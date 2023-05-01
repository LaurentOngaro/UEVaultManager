import tkinter as tk
import os
import threading
from tkinter import ttk
import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience


class ProgressWindow(tk.Toplevel):

    def __init__(self, title: str, width: 300, height: 150, icon=None, screen_index=0, callable_function=None, max_value=100):
        if callable_function is None:
            return
        super().__init__()
        self.title(title)
        geometry = gui_f.center_window_on_screen(screen_index, height, width)
        self.geometry(geometry)

        if icon is None:
            self.attributes('-toolwindow', True)
        else:
            # windows only (remove the minimize/maximize buttons and the icon)
            icon = gui_f.path_from_relative_to_absolute(icon)
            if icon != '' and os.path.isfile(icon):
                self.iconbitmap(icon)

        self.max_value = max_value
        self.continue_execution = True
        self.called_function = callable_function

        self.content_frame = self.ContentFrame(self)
        self.control_frame = self.ControlFrame(self)

        self.content_frame.pack(ipadx=5, ipady=5, padx=5, pady=5, fill=tk.X)
        self.control_frame.pack(ipadx=5, ipady=5, padx=5, pady=5, fill=tk.X)

        self.bind('<Key>', self.on_key_press)
        self.protocol("WM_DELETE_WINDOW", self.close_window)

        self.activate()
        gui_g.progress_window_ref = self

    class ContentFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__(container)
            pack_def_options = {'ipadx': 3, 'ipady': 3, 'padx': 5, 'pady': 5, 'fill': tk.X}
            function_name_label = ttk.Label(self, text='Running function: ' + container.called_function.__name__)
            function_name_label.pack(**pack_def_options)
            progress_var = tk.IntVar()
            progress_bar = ttk.Progressbar(self, orient="horizontal", mode="determinate", variable=progress_var, maximum=container.max_value)
            progress_bar.pack(**pack_def_options)
            self.progress_var = progress_var
            self.progress_bar = progress_bar

    class ControlFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__(container)
            pack_def_options = {'ipadx': 3, 'ipady': 3, 'fill': tk.X}
            start_button = ttk.Button(self, text="Start", command=container.start_execution)
            start_button.pack(**pack_def_options, side=tk.LEFT)
            stop_button = ttk.Button(self, text="Stop", command=container.stop_execution, state=tk.DISABLED)
            stop_button.pack(**pack_def_options, side=tk.RIGHT)
            self.stop_button = stop_button
            self.start_button = start_button

    def start_execution(self) -> None:
        self.continue_execution = True
        threading.Thread(target=self.called_function).start()
        self.deactivate()

    def stop_execution(self) -> None:
        self.continue_execution = False
        self.activate()

    def activate(self) -> None:
        self.control_frame.start_button.config(state=tk.NORMAL)
        self.control_frame.stop_button.config(state=tk.DISABLED)

    def deactivate(self) -> None:
        self.control_frame.stop_button.config(state=tk.NORMAL)
        self.control_frame.start_button.config(state=tk.DISABLED)

    def update_and_check(self, value) -> bool:
        self.content_frame.progress_var.set(value)
        return self.continue_execution

    def close_window(self, _event=None):
        gui_g.edit_cell_window_ref = None
        self.destroy()

    def on_key_press(self, event):
        if event.keysym == 'Return':
            if self.continue_execution:
                self.deactivate()
            else:
                self.activate()
