import tkinter as tk
import os
import threading
from tkinter import ttk
import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience


class ProgressWindow(tk.Toplevel if tk._default_root else tk.Tk):

    def __init__(
        self,
        title: str,
        width: 300,
        height: 150,
        icon=None,
        screen_index=0,
        max_value=100,
        show_start_button=True,
        show_stop_button=True,
        show_progress=True
    ):
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

        # the function to be executed in a thread
        self.threaded_function = None
        # the parameter of the function to be executed in a thread
        self.execution_parameters = {}
        # the return value of the function to be executed
        self.execution_return_value = None

        self.content_frame = self.ContentFrame(self)
        self.control_frame = self.ControlFrame(self)

        self.content_frame.pack(ipadx=5, ipady=5, padx=5, pady=5, fill=tk.X)
        self.control_frame.pack(ipadx=5, ipady=5, padx=5, pady=5, fill=tk.X)

        gui_g.progress_window_ref = self
        self.thread = None

        self.bind('<Key>', self.on_key_press)
        self.protocol("WM_DELETE_WINDOW", self.close_window)

        # the function can be set after the window is created
        if self.threaded_function is None:
            self.deactivate()
        else:
            self.activate()

        if not show_progress:
            self.hide_progress_bar()
        if not show_start_button:
            self.hide_start_button()
        if not show_stop_button:
            self.hide_stop_button()

    class ContentFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__(container)
            pack_def_options = {'ipadx': 3, 'ipady': 3, 'padx': 5, 'pady': 5, 'fill': tk.X}
            if container.threaded_function is None:
                lbl_function_name = ttk.Label(self, text='No callable function set Yet')
            else:
                lbl_function_name = ttk.Label(self, text='Running function: ' + container.threaded_function.__name__)
            lbl_function_name.pack(**pack_def_options)
            progress_var = tk.IntVar()
            progress_bar = ttk.Progressbar(self, orient="horizontal", mode="determinate", variable=progress_var, maximum=container.max_value)
            progress_bar.pack(**pack_def_options)
            self.progress_var = progress_var
            self.progress_bar = progress_bar
            self.lbl_function_name = lbl_function_name

    class ControlFrame(ttk.Frame):

        def __init__(self, container, show_start_button=True, show_stop_button=True):
            super().__init__(container)
            pack_def_options = {'ipadx': 3, 'ipady': 3, 'fill': tk.X}
            self.button_start = None
            self.button_stop = None
            if show_start_button:
                button_start = ttk.Button(self, text="Start", command=container.start_execution)
                button_start.pack(**pack_def_options, side=tk.LEFT)
                self.button_start = button_start
            if show_stop_button:
                button_stop = ttk.Button(self, text="Stop", command=container.stop_execution, state=tk.DISABLED)
                button_stop.pack(**pack_def_options, side=tk.RIGHT)
                self.button_stop = button_stop

    def set_text(self, new_text):
        self.content_frame.lbl_function_name.config(text=new_text)

    def set_value(self, new_value):
        new_value = max(0, new_value)
        self.content_frame.progress_var.set(new_value)

    def set_max_value(self, new_max_value):
        if new_max_value:
            self.max_value = new_max_value
            self.content_frame.progress_bar.config(maximum=new_max_value)

    def set_function(self, threaded_function):
        if threaded_function is None:
            return
        self.set_text('Running function: ' + threaded_function.__name__)
        self.threaded_function = threaded_function

    def set_function_parameters(self, parameters: dict):
        if parameters is None:
            return
        self.execution_parameters = parameters

    def hide_progress_bar(self):
        self.content_frame.progress_bar.pack_forget()

    def show_progress_bar(self):
        self.content_frame.progress_bar.pack()

    def hide_start_button(self):
        self.control_frame.button_start.pack_forget()

    def show_start_button(self):
        self.control_frame.button_start.pack()

    def hide_stop_button(self):
        self.control_frame.button_stop.pack_forget()

    def show_stop_button(self):
        self.control_frame.button_stop.pack()

    def reset(self, new_value=0, new_title=None, new_text=None, new_max_value=None, new_threaded_function=None):
        if new_title is not None:
            self.title(new_title)
        if new_text is not None:
            self.set_text(new_text)
        if new_max_value is not None:
            self.set_max_value(new_max_value)
        if new_threaded_function is not None:
            self.set_function(new_threaded_function)
        self.content_frame.progress_var.set(new_value)
        self.continue_execution = True
        self.activate()

    def execute_function(self):
        gui_f.log_info(f'execution of {self.threaded_function} has started')
        if isinstance(self.execution_parameters, dict):
            # execution_parameters is a dictionary
            self.execution_return_value = self.threaded_function(**self.execution_parameters)
        elif isinstance(self.execution_parameters, list) or isinstance(self.execution_parameters, set):
            # execution_parameters is a list
            self.execution_return_value = self.threaded_function(*self.execution_parameters)
        gui_f.log_info(f'execution of {self.threaded_function} has ended')
        self.close_window()

    def start_execution(self) -> None:
        if self.threaded_function is None:
            return
        self.continue_execution = True
        threading.Thread(target=self.threaded_function).start()
        self.thread = threading.Thread(target=self.execute_function)
        self.thread.start()
        self.deactivate()

    def stop_execution(self) -> None:
        self.continue_execution = False
        self.activate()

    def get_results(self):
        return self.execution_return_value

    def activate(self) -> None:
        if self.control_frame.button_start is not None:
            self.control_frame.button_start.config(state=tk.NORMAL)
        if self.control_frame.button_stop is not None:
            self.control_frame.button_stop.config(state=tk.DISABLED)

    def deactivate(self) -> None:
        if self.control_frame.button_start is not None:
            self.control_frame.button_stop.config(state=tk.NORMAL)
        if self.control_frame.button_stop is not None:
            self.control_frame.button_start.config(state=tk.DISABLED)

    def update_and_continue(self, value=0, increment=0) -> bool:
        if increment:
            value = self.content_frame.progress_var.get() + increment
        if value > self.max_value:
            value = self.max_value
        self.content_frame.progress_var.set(value)
        return self.continue_execution

    def close_window(self, _event=None):
        self.stop_execution()
        self.quit()

    def on_key_press(self, event):
        if event.keysym == 'Escape':
            if self.continue_execution:
                self.deactivate()
            else:
                self.activate()
