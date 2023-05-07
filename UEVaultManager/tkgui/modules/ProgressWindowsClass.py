import os
import threading
import queue
import tkinter as tk
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
        show_progress=True,
        function=None,
        function_parameters: dict = None,
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

        self.function = function
        self.function_params = function_parameters
        self.function_return_value = None
        self.result_queue = queue.Queue()

        self.content_frame = self.ContentFrame(self)
        self.content_frame.pack(ipadx=5, ipady=5, padx=5, pady=5, fill=tk.X)

        if not show_start_button and not show_stop_button:
            self.control_frame = None
        else:
            self.control_frame = self.ControlFrame(self)
            self.control_frame.pack(ipadx=5, ipady=5, padx=5, pady=5, fill=tk.X)

        gui_g.progress_window_ref = self

        if not show_progress:
            self.hide_progress_bar()
        if self.control_frame and not show_start_button:
            self.control_frame.button_start.pack_forget()
        if self.control_frame and not show_stop_button:
            self.control_frame.button_stop.pack_forget()

        # Start the execution if not control frame is present
        # important because the control frame is not present when the function is set after the window is created
        if self.control_frame is None or not show_start_button:
            self.start_execution()

    class ContentFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__(container)
            pack_def_options = {'ipadx': 3, 'ipady': 3, 'padx': 5, 'pady': 5, 'fill': tk.X}
            if container.function is None:
                lbl_function = ttk.Label(self, text='No callable function set Yet')
            else:
                lbl_function = ttk.Label(self, text='Running function: ' + container.function.__name__)
            lbl_function.pack(**pack_def_options)
            progress_bar = ttk.Progressbar(self, orient="horizontal", mode="determinate", maximum=container.max_value)
            progress_bar.pack(**pack_def_options)
            self.pack_def_options = pack_def_options
            self.progress_bar = progress_bar
            self.lbl_function = lbl_function

    class ControlFrame(ttk.Frame):

        def __init__(self, container, show_start_button=True, show_stop_button=True):
            super().__init__(container)
            pack_def_options = {'ipadx': 3, 'ipady': 3, 'fill': tk.X}
            self.pack_def_options = pack_def_options
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

    def _function_result_wrapper(self, function, *args, **kwargs):
        gui_f.log_info(f'execution of {function.__name__} has started')
        result = function(*args, **kwargs)
        self.result_queue.put(result)

    # check if the function is still running, if not, quit the window
    def _check_for_end(self, t):
        if t.is_alive():
            # Schedule another check in 300 ms
            self.after(300, self._check_for_end, t)
        else:
            # The thread has finished; clean up
            gui_f.log_debug(f'Quitting {self.__class__.__name__}')
            self.function_return_value = self.result_queue.get()
            self.close_window()

    def set_text(self, new_text):
        if self.content_frame is None or self.content_frame.lbl_function is None:
            return
        self.content_frame.lbl_function.config(text=new_text)

    def set_value(self, new_value):
        new_value = max(0, new_value)
        if self.content_frame is None or self.content_frame.progress_bar is None:
            return
        self.content_frame.progress_bar["value"] = new_value

    def set_max_value(self, new_max_value):
        if self.content_frame is None or self.content_frame.progress_bar is None:
            return
        self.max_value = new_max_value
        self.content_frame.progress_bar["maximum"] = new_max_value

    def set_function(self, new_function):
        if new_function is None:
            return
        self.set_text('Running function: ' + new_function.__name__)
        self.function = new_function

    def set_function_parameters(self, parameters: dict):
        self.function_params = parameters

    def hide_progress_bar(self):
        self.content_frame.progress_bar.pack_forget()

    def show_progress_bar(self):
        self.content_frame.progress_bar.pack(self.content_frame.pack_def_options)

    def hide_start_button(self):
        if self.control_frame is None or self.control_frame.button_start is None:
            return
        self.control_frame.button_start.pack_forget()

    def show_start_button(self):
        if self.control_frame is None or self.control_frame.button_start is None:
            return
        self.control_frame.button_start.pack(self.control_frame.pack_def_options)

    def hide_stop_button(self):
        if self.control_frame is None or self.control_frame.button_stop is None:
            return
        self.control_frame.button_stop.pack_forget()

    def show_stop_button(self):
        if self.control_frame is None or self.control_frame.button_stop is None:
            return
        self.control_frame.button_stop.pack(self.control_frame.pack_def_options)

    def reset(self, new_title=None, new_value=None, new_text=None, new_max_value=None):
        try:
            # sometimes the window is already destroyed
            if new_title is not None:
                self.title(new_title)
            if new_text is not None:
                self.set_text(new_text)
            if new_value is not None:
                self.show_progress_bar()
                self.set_value(new_value)
            if new_max_value is not None:
                self.show_progress_bar()
                self.set_max_value(new_max_value)
        except tk.TclError:
            gui_f.log_warning('Some tkinter elements are not set. The window is probably already destroyed')
        self.continue_execution = True

    def start_execution(self) -> None:
        if self.function is None:
            gui_f.log_warning('the function name to execute is not set')
            return
        self.continue_execution = True
        self.deactivate()
        # Run the function in a separate thread
        t = threading.Thread(target=self._function_result_wrapper, args=(self.function, self), kwargs=self.function_params)
        t.start()
        # Schedule GUI update while waiting for the thread to finish
        self.after(100, self._check_for_end, t)

    def stop_execution(self) -> None:
        self.continue_execution = False
        self.activate()

    def get_result(self):
        return self.function_return_value

    def activate(self) -> None:
        if self.control_frame is None:
            return
        if self.control_frame.button_start is not None:
            self.control_frame.button_start.config(state=tk.NORMAL)
        if self.control_frame.button_stop is not None:
            self.control_frame.button_stop.config(state=tk.DISABLED)

    def deactivate(self) -> None:
        if self.control_frame is None:
            return
        if self.control_frame.button_start is not None:
            self.control_frame.button_stop.config(state=tk.NORMAL)
        if self.control_frame.button_stop is not None:
            self.control_frame.button_start.config(state=tk.DISABLED)

    def update_and_continue(self, value=0, increment=0) -> bool:
        try:
            # sometimes the window is already destroyed
            progress_bar = self.content_frame.progress_bar
            if increment:
                value = progress_bar["value"] + increment

            if value > self.max_value:
                value = self.max_value
            progress_bar["value"] = value
            progress_bar.update_idletasks()
        except tk.TclError:
            gui_f.log_warning('Some tkinter elements are not set. The window is probably already destroyed')
        self.update_idletasks()
        return self.continue_execution

    def close_window(self, _event=None):
        try:
            # sometimes the window is already destroyed
            self.stop_execution()
        except tk.TclError:
            gui_f.log_warning('Some tkinter elements are not set. The window is probably already destroyed')

        if tk._default_root:
            self.destroy()
        else:
            self.quit()
