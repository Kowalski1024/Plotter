from serial import Serial, SerialException
import time
import sys
import glob
import threading
import tkinter as tk
from tkinter import scrolledtext, filedialog

WINDOW_SIZE = '384x460'


class PlotterAPI:
    def __init__(self, parent: tk.Tk):
        self.parent = parent
        self.serial = Serial()
        self.serial.baudrate = 9600
        self.serial_thread = None
        self.serial_thread = threading.Thread(target=self.read_from_port, daemon=True)
        self.widgets_list = list()
        self.stop_button_clicked = False
        self.semaphore = threading.BoundedSemaphore(1)

        self.main_frame = tk.LabelFrame(self.parent, padx=5, pady=5)
        self.main_frame.grid(row=0, column=0, sticky=tk.E + tk.W, padx=5, pady=5)

        # serial output frame
        self.serial_frame = tk.LabelFrame(self.parent, text="Serial Output", padx=5, pady=5)
        self.serial_frame.grid(row=1, column=0, sticky=tk.E + tk.W + tk.N + tk.S, padx=10, pady=10)
        self.scroll_text = scrolledtext.ScrolledText(self.serial_frame, width=40, height=10)
        self.scroll_text.bind("<Key>", lambda a: "break")
        self.scroll_text.grid(row=0, column=0, sticky=tk.E + tk.W + tk.N + tk.S)

        # port menu frame
        self.port_frame = tk.LabelFrame(self.main_frame, text="Serial Port", padx=5, pady=5)
        self.port_frame.grid(row=0, column=0)

        ports = get_ports_list()
        self.menu_str = tk.StringVar()
        self.menu_str.set("None")
        self.port_menu = tk.OptionMenu(self.port_frame, self.menu_str, *ports)
        self.port_menu.bind('<Button-1>', self.refresh_port_list)
        self.port_menu.grid(row=0, column=0, sticky=tk.W + tk.E)

        self.port_var = tk.IntVar()
        tk.Checkbutton(self.port_frame, variable=self.port_var,
                       command=lambda: self.select_port(self.menu_str.get())).grid(row=0, column=1)

        # G-code transfer
        self.file_frame = tk.LabelFrame(self.main_frame, text="G-code Stream", padx=5, pady=5)
        self.file_frame.grid(row=1, column=0)
        widget_1 = tk.Button(self.file_frame, text="Select file", command=self.select_file)
        widget_1.grid(row=0, column=0)
        self.stop_button = tk.Button(self.file_frame, text="STOP", command=self.stop_stream)
        self.stop_button.grid(row=0, column=1)
        self.stop_button.config(state=tk.DISABLED)

        # plotter controls
        self.controls_frame = tk.LabelFrame(self.main_frame, text="Plotter Controls", padx=5, pady=5)
        self.controls_frame.grid(row=0, column=2, rowspan=2)
        widget_2 = tk.Button(self.controls_frame, text="Current Position", command=self.print_curr_position)
        widget_2.grid(row=0, column=0)
        widget_3 = tk.Button(self.controls_frame, text="Home", command=self.auto_home)
        widget_3.grid(row=0, column=1)
        widget_4 = tk.Button(self.controls_frame, text="Pen", command=self.change_pen_position)
        widget_4.grid(row=0, column=2)
        self.widgets_list += [widget_1, widget_2, widget_3, widget_4]
        # tk.Label(self.controls_frame, text="Arrow keys to jog in x-y axis").grid(row=1, column=0, columnspan=3)

        self.parent.columnconfigure(0, weight=1)
        self.parent.rowconfigure(1, weight=1)
        self.serial_frame.rowconfigure(0, weight=1)
        self.serial_frame.columnconfigure(0, weight=1)

        self.controls_state()
        self.serial_thread.start()

    def select_file(self):
        filename = filedialog.askopenfilename(title="Select a file",
                                              filetypes=(("G-code files", "*.gcode"), ("All files", "*.*")))
        self.stop_button.config(state=tk.NORMAL)
        threading.Thread(target=self.file_stream, args=(filename,)).start()

    def file_stream(self, filename):
        file = open(filename, 'r')
        lines = file.readlines()
        for line in lines:
            if self.stop_button_clicked:
                break
            self.write_to_port(line, semaphore=True)

    def stop_stream(self):
        self.stop_button.config(state=tk.DISABLED)
        self.stop_button_clicked = True

    def refresh_port_list(self, event):
        ports = get_ports_list()
        menu = self.port_menu['menu']
        menu.delete(0, 'end')
        for port in ports:
            menu.add_command(label=port, command=tk._setit(self.menu_str, port))

    def select_port(self, port):
        if port == 'None':
            self.port_var.set(0)
        elif self.port_var.get() == 1:
            self.port_menu.config(state=tk.DISABLED)
            self.serial.port = port
            self.serial.open()
        else:
            self.port_menu.config(state=tk.NORMAL)
            self.serial.close()
        self.controls_state()

    def read_from_port(self):
        while True:
            if self.port_var.get() and self.serial.isOpen() and self.serial.in_waiting:
                packet = self.serial.readline().decode('utf')
                self.scroll_text.insert(tk.INSERT, packet)
                self.scroll_text.see("end")
                if packet.startswith('ok'):
                    self.semaphore.release()
            else:
                time.sleep(0.2)

    def write_to_port(self, line: str, semaphore=False):
        if semaphore:
            self.semaphore.acquire()
        if line.endswith('\n'):
            self.serial.write(line.encode())
        else:
            self.serial.write((line + '\n').encode())

    def change_pen_position(self):
        self.write_to_port('M301\n', semaphore=True)

    def auto_home(self):
        self.write_to_port('G28', semaphore=True)

    def print_curr_position(self):
        self.write_to_port('M114', semaphore=True)

    def controls_state(self):
        if self.widgets_list:
            for widget in self.widgets_list:
                if self.port_var.get():
                    widget.config(state=tk.NORMAL)
                else:
                    widget.config(state=tk.DISABLED)


def get_ports_list() -> list:
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    # add available ports to list
    for port in ports:
        try:
            s = Serial(port)
            s.close()
            result.append(port)
        except (OSError, SerialException):
            pass
    return result


if __name__ == '__main__':
    root = tk.Tk()
    root.geometry(WINDOW_SIZE)
    root.title("Plotter API")
    PlotterAPI(root)
    root.mainloop()
