#include <Servo.h>
#include <AccelStepper.h>
#include <MultiStepper.h>

#define BUFSIZ 64
#define LINE_BUFSIZ 512

// -------------------------------------------------
// Pins
const int XButton = A0;
const int YButton = A1;
const int ServoPin = 3;
AccelStepper stepperX(4, 8, 10, 9, 11);
AccelStepper stepperY(4, 4, 6, 5, 7);

// Settings
const bool verboseMode = true; // Debugging mode

const int ZUp = 80;
const int ZDown = 20;

const int acceleration = 200;
const int wrtieSpeed = 200;
const int movementSpeed = 400;
const double stepsPerMillimeter = 51.85;

// Drawing limits
float Xmin = 0;
float Xmax = 100;
float Ymin = 0;
float Ymax = 100;
// -------------------------------------------------

bool penIsUp = true;
Servo penServo;
MultiStepper steppers;

void setup()
{
  pinMode(XButton, INPUT);
  pinMode(YButton, INPUT);
  steppers.addStepper(stepperX);
  steppers.addStepper(stepperY);
  penServo.attach(ServoPin);
  Serial.begin(9600);

  stepperX.setAcceleration(acceleration);
  stepperY.setAcceleration(acceleration);
  penDown();
  delay(1000);
  //  autohome();
}

void loop()
{
  delay(200);
  char line[LINE_BUFSIZ];
  char c;
  int lineIndex;
  bool lineIsComment;

  lineIndex = 0;
  lineIsComment = false;

  while (1)
  {
    while (Serial.available() > 0)
    {
      c = Serial.read();
      if ((c == '\n') || (c == '\r'))
      { // End of line reached
        if (lineIndex > 0)
        {
          line[lineIndex] = '\0';
          Serial.print("Received: ");
          Serial.println(line);
          processLine(line, lineIndex);
          lineIndex = 0;
        }
        lineIsComment = false;
        Serial.println("ok");
      }
      else
      {
        if (lineIsComment)
        { // Throw away all comment characters
          if (c == ')')
            lineIsComment = false; // End of comment. Resume line.
        }
        else
        {
          if (c == '/')
          { // Block delete not supported. Ignore character.
          }
          else if (c == '(')
          { // Enable comments flag
            lineIsComment = true;
          }
          else if (lineIndex >= LINE_BUFSIZ - 1)
          {
            Serial.println("ERROR - lineBuffer overflow");
          }
          else
          {
            line[lineIndex++] = toupper(c);
          }
        }
      }
    }
  }
}

void processLine(char *line, int size)
{
  char buffer[BUFSIZ];
  int currentIdx = 0;
  while (currentIdx < size)
  {
    char *index_X = NULL;
    char *index_Y = NULL;
    char *index_Other = NULL;
    switch (line[currentIdx++])
    {
    case 'G':
      int num = atoi(line + currentIdx++);
      switch (num)
      {
      case 1:
      case 2:
        float x, y;
        index_X = strchr(line + currentIdx, 'X');
        index_Y = strchr(line + currentIdx, 'Y');
        if (index_X && index_Y)
        {
          x = atof(index_X + 1);
          y = atof(index_Y + 1);
        }
        else
        {
          Serial.println("Error - Line has too few arguments");
          break;
        }
        drawLine(x, y);
        break;
      case 4:
        index_Other = strchr(line + currentIdx, 'P');
        if (!index_Other)
        {
          Serial.println("Error - Line has too few arguments");
          break;
        }
        int sleepTime = atoi(index_Other + 1);
        delay(sleepTime);
        break;
      case 28:
        autohome();
        break;
      }
      break;
    case 'M':
      buffer[0] = line[currentIdx++];
      buffer[1] = line[currentIdx++];
      buffer[2] = line[currentIdx++];
      buffer[3] = '\0';
      Serial.println(buffer);
      switch (atoi(buffer))
      {
      case 301:
        if (penIsUp)
        {
          penDown();
        }
        else
        {
          penUp();
        }
        break;
      case 300:
      {
        index_Other = strchr(line + currentIdx, 'S');
        if (!index_Other)
        {
          Serial.println("Error - Line has too few arguments");
          break;
        }
        float Spos = atof(index_Other + 1);
        if (Spos == 30)
        {
          penDown();
        }
        if (Spos == 50)
        {
          penUp();
        }
        break;
      }
      case 114:
        double x = stepperX.currentPosition() / stepsPerMillimeter;
        double y = stepperY.currentPosition() / stepsPerMillimeter;
        Serial.print("Absolute position : X = ");
        Serial.print(x);
        Serial.print("  -  Y = ");
        Serial.println(y);
        break;
      }
      break;
    }
  }
}

void drawLine(float x, float y)
{
  if (x > Xmax || x < Xmin || y > Ymax || y < Ymin)
  {
    Serial.println("Warning - destination point is out of range");
    if (x > Xmax)
    {
      x = Xmax;
    }

    if (x < Xmin)
    {
      x = Xmin;
    }

    if (y > Ymax)
    {
      y = Ymax;
    }

    if (y < Ymin)
    {
      y = Ymin;
    }
  }
  long pos[2];
  pos[0] = (long)(x * stepsPerMillimeter);
  pos[1] = (long)(y * stepsPerMillimeter);

  steppers.moveTo(pos);
  steppers.runSpeedToPosition();
  delay(10);
}

void autohome()
{
  Serial.println("Auto homing starts");
  penUp();
  // Home stepper X
  homeStepper(&stepperX, XButton);
  if (verboseMode)
  {
    Serial.println("Stepper X ends homing");
  }

  // Home stepper Y
  homeStepper(&stepperY, YButton);
  if (verboseMode)
  {
    Serial.println("Stepper Y ends homing");
  }
  Serial.println("Auto homing complete");
}

void homeStepper(AccelStepper *stepper, int button)
{
  int pos = -1;
  stepper->setMaxSpeed(300.0);
  while (!digitalRead(button))
  {
    stepper->moveTo(pos--);
    stepper->run();
    delay(5);
  }
  stepper->setCurrentPosition(0);

  pos = 1;
  stepper->setMaxSpeed(100.0);
  while (digitalRead(button))
  {
    stepper->moveTo(pos++);
    stepper->run();
    delay(5);
  }
  stepper->setMaxSpeed(movementSpeed);
  stepper->setCurrentPosition(0);
}

void penUp()
{
  penServo.write(ZUp);
  penIsUp = true;
  stepperX.setMaxSpeed(movementSpeed);
  stepperY.setMaxSpeed(movementSpeed);
  if (verboseMode)
  {
    Serial.println("Pen Up");
  }
}

void penDown()
{
  penServo.write(ZDown);
  penIsUp = false;
  stepperX.setMaxSpeed(wrtieSpeed);
  stepperY.setMaxSpeed(wrtieSpeed);
  if (verboseMode)
  {
    Serial.println("Pen down");
  }
}
