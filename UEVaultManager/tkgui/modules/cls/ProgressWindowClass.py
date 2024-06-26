# coding=utf-8
"""
Implementation for:
- PW_Settings: settings for the class when running as main.
- ProgressWindow: window to display the progress of a function.
"""
import queue
import threading
import tkinter as tk
from tkinter import ttk

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience


# noinspection PyPep8Naming
class PW_Settings:
    """
    Settings for the class when running as main.
    """
    title = 'This is a progress window'
    show_btn_start: bool = True,
    show_btn_stop: bool = True,
    show_progress: bool = True,
    max_value: int = 100


# noinspection PyProtectedMember
class ProgressWindow(tk.Toplevel):
    """
    The window to display the progress of a function.
    :param parent: parent window.
    :param title: title.
    :param width: width.
    :param height: height.
    :param icon: icon.
    :param screen_index: index of the screen on which the window will be displayed.
    :param max_value: maximum value of the progress bar.
    :param show_btn_start: whether to show the start button.
    :param show_btn_stop: whether to show the stop button.
    :param show_progress: whether to show the progress bar.
    :param function: function to execute.
    :param function_parameters: parameters of the function.
    :param quit_on_close: whether to quit the application when the window is closed.
    """
    is_fake = False

    def __init__(
        self,
        title: str,
        parent=None,
        width: int = 300,
        height: int = 150,
        icon=None,
        screen_index: int = -1,
        max_value: int = 100,
        show_btn_start: bool = False,
        show_btn_stop: bool = True,
        show_progress: bool = True,
        function=None,
        function_parameters: dict = None,
        quit_on_close: bool = False
    ):
        super().__init__(parent)
        self.title(title)
        # get the root window
        root = gui_g.WindowsRef.uevm_gui or self
        self.screen_index: int = screen_index if screen_index >= 0 else int(root.winfo_screen()[1])
        self.geometry(gui_fn.center_window_on_screen(self.screen_index, width, height))
        gui_fn.set_icon_and_minmax(self, icon)
        self._thread_check_delay: int = 100
        self.is_closing: bool = False
        self.quit_on_close: bool = quit_on_close
        self.max_value: int = max_value
        self._continue_execution: bool = True
        self.function = function
        self.function_params = function_parameters
        self.function_return_value = None
        self.result_queue = queue.Queue()
        self.pack_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 3, 'pady': 3, 'fill': tk.X}

        self.frm_content = self.ContentFrame(self)
        self.frm_content.pack(**self.pack_def_options)

        self.frm_control = self.ControlFrame(self)
        if show_btn_start or show_btn_stop:
            self.frm_control.pack(**self.pack_def_options)
        if not show_progress:
            self.hide_progress_bar()
        if not show_btn_start:
            self.hide_btn_start()
        if not show_btn_stop:
            self.hide_btn_stop()

        gui_g.WindowsRef.progress = self
        gui_f.make_modal(self, wait_for_close=False)

        # Start the execution if not control frame is present
        # important because the control frame is not present when the function is set after the window is created
        if not show_btn_start and self.function is not None:
            self.start_execution()

    def mainloop(self, n=0):
        """
        Mainloop method
        :param n: threshold.

        Overrided to add logging function for debugging
        """
        gui_f.log_info(f'starting mainloop in {__name__}')
        self.focus_force()
        self.grab_set()
        self.tk.mainloop(n)
        gui_f.log_info(f'ending mainloop in {__name__}')

    def __del__(self):
        gui_f.log_debug(f'Destruction of {self.__class__.__name__} object')
        gui_g.WindowsRef.progress = None

    class ContentFrame(ttk.Frame):
        """
        The frame that contains the content of the window.
        :param container: container.
        """

        def __init__(self, container):
            super().__init__(container)
            if container.function is None:
                lbl_text = ttk.Label(self, text='Operation has started...')
            else:
                lbl_text = ttk.Label(self, text='Running function: ' + container.function.__name__)
            lbl_text.pack(**container.pack_def_options)
            progress_bar = ttk.Progressbar(self, orient="horizontal", mode="determinate", maximum=container.max_value)
            progress_bar.pack(**container.pack_def_options)
            self.progress_bar = progress_bar
            self.lbl_text = lbl_text

    class ControlFrame(ttk.Frame):
        """
        The frame that contains the control buttons.
        :param container: container.
        :param show_btn_start: whether to show the start button.
        :param show_btn_stop: whether to show the stop button.
        """

        def __init__(self, container, show_btn_start=True, show_btn_stop=True):
            super().__init__(container)
            self.btn_start = None
            self.btn_stop = None
            btn_start = ttk.Button(self, text="Start", command=container.start_execution)
            btn_stop = ttk.Button(self, text="Stop", command=container.stop_execution, state=tk.DISABLED)
            self.btn_start = btn_start
            self.btn_stop = btn_stop
            if show_btn_start:
                btn_start.pack(**container.pack_def_options, side=tk.LEFT)
            if show_btn_stop:
                btn_stop.pack(**container.pack_def_options, side=tk.RIGHT)

    def _function_result_wrapper(self, function, *args, **kwargs) -> None:
        """
        Wrap the function call and puts the result in the queue.
        :param function: function to execute.
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
        :param t: thread to check.
        """
        if t.is_alive():
            # Schedule another check in a few ms
            self.after(self._thread_check_delay, self._check_for_end, t)
        else:
            # The thread has finished; clean up
            gui_f.log_debug(f'Quitting {self.__class__.__name__}')
            self.function_return_value = self.result_queue.get()
            self.close_window(destroy_window=self.quit_on_close)  # the window is kept to allow further calls to the progress bar

    def get_text(self) -> str:
        """
        Get the text of the label.
        :return: text.
        """
        return self.frm_content.lbl_text.cget('text')

    def set_text(self, new_text: str) -> None:
        """
        Set the text of the label.
        :param new_text: new text.
        """
        self.frm_content.lbl_text.config(text=new_text)
        self.update()

    def set_value(self, new_value: int) -> None:
        """
        Set the value of the progress bar.
        :param new_value: new value.
        """
        new_value = max(0, new_value)
        self.frm_content.progress_bar['value'] = new_value
        self.update()

    def set_max_value(self, new_max_value: int) -> None:
        """
        Set the maximum value of the progress bar.
        :param new_max_value: new maximum value.
        """
        self.max_value = new_max_value
        self.frm_content.progress_bar['maximum'] = new_max_value
        self.update()

    def set_function(self, new_function) -> None:
        """
        Set the function to execute.
        :param new_function: new function.
        """
        if new_function is None:
            return
        self.set_text('Running function: ' + new_function.__name__)
        self.update()
        self.function = new_function

    def set_function_parameters(self, parameters: dict) -> None:
        """
        Set the parameters to pass to the function.
        :param parameters: parameters.
        """
        self.function_params = parameters

    def hide_progress_bar(self) -> None:
        """
        Hide the progress bar.
        """
        self.frm_content.progress_bar.pack_forget()
        self.update()

    def show_progress_bar(self) -> None:
        """
        Show the progress bar.
        """
        self.frm_control.pack(**self.pack_def_options)
        self.frm_content.progress_bar.pack(**self.pack_def_options)
        self.update()

    def hide_btn_start(self) -> None:
        """
        Hide the start button.
        """
        try:
            self.frm_control.btn_start.pack_forget()
            self.update()
        except tk.TclError as error:
            gui_f.log_debug(f'Some tkinter elements are not set. The window is probably already destroyed. {error!r}')

    def show_btn_start(self) -> None:
        """
        Show the start button.
        """
        try:
            self.frm_control.pack(**self.pack_def_options)
            self.frm_control.btn_start.pack(**self.pack_def_options, side=tk.LEFT)
            self.update()
        except tk.TclError as error:
            gui_f.log_debug(f'Some tkinter elements are not set. The window is probably already destroyed. {error!r}')

    def hide_btn_stop(self) -> None:
        """
        Hide the stop button.
        """
        try:
            self.frm_control.btn_stop.pack_forget()
            self.update()
        except tk.TclError as error:
            gui_f.log_debug(f'Some tkinter elements are not set. The window is probably already destroyed. {error!r}')

    def show_btn_stop(self) -> None:
        """
        Show the stop button.
        """
        try:
            self.frm_control.pack(**self.pack_def_options)
            self.frm_control.btn_stop.pack(**self.pack_def_options, side=tk.RIGHT)
        except tk.TclError as error:
            gui_f.log_debug(f'Some tkinter elements are not set. The window is probably already destroyed. {error!r}')

    def reset(self, new_title=None, new_value=None, new_text=None, new_max_value=None, keep_execution_state: bool = False) -> None:
        """
        Reset the progress bar.
        :param new_title: new title.
        :param new_value: new value.
        :param new_text: new text.
        :param new_max_value: new maximum value.
        :param keep_execution_state: whether to keep the execution state (continue or not).
        """
        self.is_closing = False
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
                self.show_btn_stop()
                self.set_max_value(new_max_value)
            else:
                self.hide_progress_bar()
                self.hide_btn_stop()
            self.frm_control.btn_stop.config(text='Stop')
        except tk.TclError as error:
            gui_f.log_debug(f'Some tkinter elements are not set. The window is probably already destroyed. {error!r}')
        if not keep_execution_state:
            self.continue_execution = True
        self.update()

    @property
    def continue_execution(self) -> bool:
        """ Returns whether the execution should continue. """
        return self._continue_execution

    @continue_execution.setter
    def continue_execution(self, value: bool) -> None:
        """ Set whether the execution should continue. """
        self._continue_execution = value

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
        if self.frm_control.btn_stop is not None:
            self.frm_control.btn_stop.config(text='Canceling...', width=15)
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
        start_state = tk.NORMAL if activate else tk.DISABLED
        stop_state = tk.DISABLED if activate else tk.NORMAL
        if self.frm_control.btn_start is not None:
            self.frm_control.btn_start.config(state=start_state)
        if self.frm_control.btn_stop is not None:
            self.frm_control.btn_stop.config(state=stop_state)
        self.update()

    def update_and_continue(self, value=0, increment=0, text=None, max_value: int = -1) -> bool:
        """
        Update the progress bar and returns whether the execution should continue.
        :param value: value to set.
        :param increment: value to increment. If both value and increment are set, the value is ignored.
        :param text: text to set.
        :param max_value: maximum value to set. Use -1 to keep the existing.
        """
        try:
            # sometimes the window is already destroyed
            progress_bar = self.frm_content.progress_bar
            if max_value > 0:
                self.max_value = max_value
                progress_bar['maximum'] = max_value  # no call to set_max_value to avoid the update
            if increment:
                value = progress_bar['value'] + increment
            if value > self.max_value:
                value = self.max_value
            progress_bar['value'] = value
            if text:
                self.set_text(text)
        except tk.TclError as error:
            gui_f.log_debug(f'Some tkinter elements are not set. The window is probably already destroyed. {error!r}')
        self.update()
        return self._continue_execution

    def close_window(self, destroy_window=True, _event=None) -> None:
        """
        Close the window.
        :param destroy_window: whether to destroy the window or just hide it.
        :param _event: event that triggered the close.
        """
        self.is_closing = True
        # self.continue_execution = True
        if destroy_window:
            if self.quit_on_close:
                self.quit()
            else:
                self.destroy()


if __name__ == '__main__':
    st = PW_Settings()
    main = tk.Tk()
    main.title('FAKE MAIN Window')
    main.geometry('200x100')
    ProgressWindow(title=st.title, show_progress=st.show_progress, show_btn_start=st.show_btn_start, show_btn_stop=st.show_btn_stop)
    main.mainloop()
