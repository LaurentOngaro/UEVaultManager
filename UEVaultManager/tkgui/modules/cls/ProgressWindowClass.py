# coding=utf-8
"""
Implementation for:
- ProgressWindow: window to display the progress of a function.
"""
import queue
import threading
import tkinter as tk
from tkinter import ttk

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience


# noinspection PyProtectedMember
class ProgressWindow(tk.Toplevel):
    """
    The window to display the progress of a function.
    :param title: the title.
    :param width: the width.
    :param height: the height.
    :param icon: the icon.
    :param screen_index: the index of the screen on which the window will be displayed.
    :param max_value: the maximum value of the progress bar.
    :param show_start_button: whether to show the start button.
    :param show_stop_button: whether to show the stop button.
    :param show_progress: whether to show the progress bar.
    :param function: the function to execute.
    :param function_parameters: the parameters of the function.
    :param quit_on_close: whether to quit the application when the window is closed.
    """

    def __init__(
        self,
        title: str,
        width: int = 300,
        height: int = 150,
        icon=None,
        screen_index: int = 0,
        max_value: int = 100,
        show_start_button: bool = False,
        show_stop_button: bool = True,
        show_progress: bool = True,
        function=None,
        function_parameters: dict = None,
        quit_on_close: bool = False
    ):
        super().__init__()
        self.title(title)
        self.geometry(gui_fn.center_window_on_screen(screen_index, width, height))
        gui_fn.set_icon_and_minmax(self, icon)
        self._thread_check_delay: int = 100
        self.must_end: bool = False
        self.quit_on_close: bool = quit_on_close
        self.max_value: int = max_value
        self.continue_execution: bool = True
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
        if self.control_frame is None or not show_start_button and self.function is not None:
            self.start_execution()

    def __del__(self):
        gui_f.log_debug(f'Destruction of {self.__class__.__name__} object')
        gui_g.progress_window_ref = None

    class ContentFrame(ttk.Frame):
        """
        The frame that contains the content of the window.
        :param container: the container.
        """

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
        """
        The frame that contains the control buttons.
        :param container: the container.
        :param show_start_button: whether to show the start button.
        :param show_stop_button: whether to show the stop button.
        """

        def __init__(self, container, show_start_button=True, show_stop_button=True):
            super().__init__(container)
            pack_def_options = {'ipadx': 3, 'ipady': 3, 'fill': tk.X}
            self.pack_def_options = pack_def_options
            self.button_start = None
            self.button_stop = None
            button_start = ttk.Button(self, text="Start", command=container.start_execution)
            button_stop = ttk.Button(self, text="Stop", command=container.stop_execution, state=tk.DISABLED)
            self.button_start = button_start
            self.button_stop = button_stop
            if show_start_button:
                button_start.pack(**pack_def_options, side=tk.LEFT)
            if show_stop_button:
                button_stop.pack(**pack_def_options, side=tk.RIGHT)

    def _function_result_wrapper(self, function, *args, **kwargs) -> None:
        """
        Wrap the function call and puts the result in the queue.
        :param function: the function to execute.
        :param args: args to pass to the function.
        :param kwargs: kwargs to pass to the function.
        """
        gui_f.log_info(f'execution of {function.__name__} has started')
        result = function(*args, **kwargs)
        gui_f.log_info(f'execution of {function.__name__} has ended')
        self.result_queue.put(result)

    def _check_for_end(self, t: threading) -> None:
        """
        Check if the thread has ended, if not, schedules another check.
        :param t: the thread to check.
        """
        if t.is_alive():
            # Schedule another check in a few ms
            self.after(self._thread_check_delay, self._check_for_end, t)
        else:
            # The thread has finished; clean up
            gui_f.log_debug(f'Quitting {self.__class__.__name__}')
            self.function_return_value = self.result_queue.get()
            self.close_window(destroy_window=self.quit_on_close)  # the window is kept to allow further calls to the progress bar

    def mainloop(self, n=0):
        """
        Mainloop method
        Override created to add loggin function (for debugging)
        """
        gui_f.log_info(f'starting mainloop in {__name__}')
        self.tk.mainloop(n)
        gui_f.log_info(f'ending mainloop in {__name__}')

    def set_text(self, new_text: str) -> None:
        """
        Set the text of the label.
        :param new_text: the new text.
        """
        if self.content_frame is None or self.content_frame.lbl_function is None:
            return
        self.content_frame.lbl_function.config(text=new_text)

    def set_value(self, new_value: int) -> None:
        """
        Set the value of the progress bar.
        :param new_value: the new value.
        """
        new_value = max(0, new_value)
        if self.content_frame is None or self.content_frame.progress_bar is None:
            return
        self.content_frame.progress_bar["value"] = new_value

    def set_max_value(self, new_max_value: int) -> None:
        """
        Set the maximum value of the progress bar.
        :param new_max_value: the new maximum value.
        """
        if self.content_frame is None or self.content_frame.progress_bar is None:
            return
        self.max_value = new_max_value
        self.content_frame.progress_bar["maximum"] = new_max_value

    def set_function(self, new_function) -> None:
        """
        Set the function to execute.
        :param new_function: the new function.
        """
        if new_function is None:
            return
        self.set_text('Running function: ' + new_function.__name__)
        self.update()
        self.function = new_function

    def set_function_parameters(self, parameters: dict) -> None:
        """
        Set the parameters to pass to the function.
        :param parameters: the parameters.
        """
        self.function_params = parameters

    def hide_progress_bar(self) -> None:
        """
        Hide the progress bar.
        """
        self.content_frame.progress_bar.pack_forget()

    def show_progress_bar(self) -> None:
        """
        Show the progress bar.
        """
        self.content_frame.progress_bar.pack(self.content_frame.pack_def_options)

    def hide_start_button(self) -> None:
        """
        Hide the start button.
        """
        if self.control_frame is None or self.control_frame.button_start is None:
            return
        self.control_frame.button_start.pack_forget()

    def show_start_button(self) -> None:
        """
        Show the start button.
        """
        if self.control_frame is None or self.control_frame.button_start is None:
            return
        self.control_frame.button_start.pack(self.control_frame.pack_def_options)

    def hide_stop_button(self) -> None:
        """
        Hide the stop button.
        """
        if self.control_frame is None or self.control_frame.button_stop is None:
            return
        self.control_frame.button_stop.pack_forget()

    def show_stop_button(self) -> None:
        """
        Show the stop button.
        """
        if self.control_frame is None or self.control_frame.button_stop is None:
            return
        self.control_frame.button_stop.pack(self.control_frame.pack_def_options)

    def reset(self, new_title=None, new_value=None, new_text=None, new_max_value=None) -> None:
        """
        Reset the progress bar.
        :param new_title: the new title.
        :param new_value: the new value.
        :param new_text: the new text.
        :param new_max_value: the new maximum value.
        """
        self.must_end = False
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
                self.show_stop_button()
                self.set_max_value(new_max_value)
            else:
                self.hide_progress_bar()
                self.hide_stop_button()
        except tk.TclError:
            gui_f.log_warning('Some tkinter elements are not set. The window is probably already destroyed')
        self.continue_execution = True
        self.update()

    def start_execution(self) -> None:
        """
        Start the execution of the function.
        """
        if self.function is None:
            gui_f.log_warning('the function name to execute is not set')
            return
        self.continue_execution = True
        self.set_activation(False)
        # Run the function in a separate thread
        t = threading.Thread(target=self._function_result_wrapper, args=(self.function, self), kwargs=self.function_params)
        t.start()
        # Schedule GUI update while waiting for the thread to finish
        self.after(self._thread_check_delay, self._check_for_end, t)

    def stop_execution(self) -> None:
        """
        Stop the execution of the function.
        """
        self.continue_execution = False
        self.set_activation(True)

    def get_result(self):
        """
        Return the result of the function.
        """
        return self.function_return_value

    def set_activation(self, activate: bool) -> None:
        """
        Sets the activation state of the control buttons.
        """
        if self.control_frame is None:
            return
        start_state = tk.NORMAL if activate else tk.DISABLED
        stop_state = tk.DISABLED if activate else tk.NORMAL
        if self.control_frame.button_start is not None:
            self.control_frame.button_start.config(state=start_state)
        if self.control_frame.button_stop is not None:
            self.control_frame.button_stop.config(state=stop_state)
        self.update()

    def update_and_continue(self, value=0, increment=0, text=None) -> bool:
        """
        Update the progress bar and returns whether the execution should continue.
        :param value: the value to set.
        :param increment: the value to increment. If both value and increment are set, the value is ignored.
        :param text: the text to set.
        """
        try:
            # sometimes the window is already destroyed
            progress_bar = self.content_frame.progress_bar
            if increment:
                value = progress_bar["value"] + increment
            if value > self.max_value:
                value = self.max_value
            progress_bar["value"] = value
            if text:
                self.set_text(text)
        except tk.TclError:
            gui_f.log_warning('Some tkinter elements are not set. The window is probably already destroyed')
        self.update()
        return self.continue_execution

    def close_window(self, destroy_window=True, _event=None) -> None:
        """
        Close the window.
        :param destroy_window: whether to destroy the window or just hide it.
        :param _event: the event that triggered the close.
        """
        self.must_end = True
        if destroy_window:
            if self.quit_on_close:
                self.quit()
            else:
                self.destroy()
