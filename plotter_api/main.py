import serial
import time
import sys
import glob
import threading
import tkinter as tk
from tkinter import scrolledtext, filedialog

WINDOW_SIZE = '310x460'


class PlotterAPI(tk.Frame):
    def __init__(self, parent: tk.Tk):
        super().__init__()
        self.parent = parent
        self.filename = str()
        self.serial = serial.Serial()
        self.serial.baudrate = 9600
        self.serial_thread = None
        self.serial_thread = threading.Thread(target=self.read_from_port, daemon=True)
        self.widgets_list = list()

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
        self.widgets_list.append(
            tk.Button(self.file_frame, text="Select file", command=self.select_file).grid(row=0, column=0))
        self.stop_button = tk.Button(self.file_frame, text="STOP", command=self.stop_stream)
        self.stop_button.grid(row=0, column=1)
        self.stop_button.config(state=tk.DISABLED)

        # plotter controls
        self.controls_frame = tk.LabelFrame(self.main_frame, text="Plotter Controls", padx=5, pady=5)
        self.controls_frame.grid(row=0, column=2, rowspan=2)
        self.widgets_list += [
            tk.Button(self.controls_frame, text="Set Home").grid(row=0, column=1),
            tk.Button(self.controls_frame, text="Home").grid(row=0, column=0)
        ]
        tk.Label(self.controls_frame, text="Arrow keys to jog in x-y axis").grid(row=1, column=0, columnspan=2)

        self.parent.columnconfigure(0, weight=1)
        self.parent.rowconfigure(1, weight=1)
        self.serial_frame.rowconfigure(0, weight=1)
        self.serial_frame.columnconfigure(0, weight=1)

        self.serial_thread.start()

    def select_file(self):
        self.filename = filedialog.askopenfilename(title="Select a file",
                                                   filetypes=(("G-code files", "*.gcode"), ("All files", "*.*")))
        self.stop_button.config(state=tk.NORMAL)

    def gcode_stream(self):
        pass

    def stop_stream(self):
        self.stop_button.config(state=tk.DISABLED)

    def refresh_port_list(self, event):
        ports = get_ports_list()
        menu = self.port_menu['menu']
        menu.delete(0, 'end')
        for port in ports:
            menu.add_command(label=port, command=tk._setit(self.menu_str, port))

    def select_port(self, port):
        if self.port_var.get() == 1:
            self.port_menu.config(state=tk.DISABLED)
            if port != self.serial.port:
                self.serial.close()
                self.serial.port = port
                self.serial.open()
        else:
            self.port_menu.config(state=tk.NORMAL)

    def read_from_port(self):
        while True:
            if self.port_var.get() == 1 and self.serial.port and self.serial.in_waiting:
                packet = self.serial.readline()
                self.scroll_text.insert(tk.INSERT, packet.decode('utf'))
                self.scroll_text.see("end")
            else:
                time.sleep(0.2)


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
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result


if __name__ == '__main__':
    root = tk.Tk()
    root.geometry(WINDOW_SIZE)
    root.title("Plotter API")
    PlotterAPI(root)
    root.mainloop()
