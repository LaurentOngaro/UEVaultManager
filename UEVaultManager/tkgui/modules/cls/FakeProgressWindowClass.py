# coding=utf-8
"""
implementation for:
- FakeProgressWindow: fake ProgressWindow object to use when no ProgressWindow object is provided and provide the same interface.
"""


# noinspection PyMethodMayBeStatic,PyUnusedLocal
class FakeProgressWindow:
    """
    A fake ProgressWindow object to use when no ProgressWindow object is provided and provide the same interface
    Usefull to avoid importing the ProgressWindow class and all its dependencies (all the tkinter stuff).
    """
    _thread_check_delay: int = -1
    is_fake = True
    is_closing: bool = False
    quit_on_close: bool = False
    max_value: int = -1
    continue_execution: bool = True
    function = None
    function_params = None
    function_return_value = None
    result_queue = None
    frm_content = None
    frm_control = None

    def _function_result_wrapper(self, function, *args, **kwargs) -> None:
        """ FAKE METHOD"""
        pass

    def get_text(self) -> str:
        """ FAKE METHOD"""
        return ''

    def set_text(self, new_text: str) -> None:
        """ FAKE METHOD"""
        pass

    def set_value(self, new_value: int) -> None:
        """ FAKE METHOD"""
        pass

    def set_max_value(self, new_max_value: int) -> None:
        """ FAKE METHOD"""
        pass

    def set_function(self, new_function) -> None:
        """ FAKE METHOD"""
        pass

    def set_function_parameters(self, parameters: dict) -> None:
        """ FAKE METHOD"""
        pass

    def hide_progress_bar(self) -> None:
        """ FAKE METHOD"""
        pass

    def show_progress_bar(self) -> None:
        """ FAKE METHOD"""
        pass

    def hide_btn_start(self) -> None:
        """ FAKE METHOD"""
        pass

    def show_btn_start(self) -> None:
        """ FAKE METHOD"""
        pass

    def hide_btn_stop(self) -> None:
        """ FAKE METHOD"""
        pass

    def show_btn_stop(self) -> None:
        """ FAKE METHOD"""
        pass

    def reset(self, new_title=None, new_value=None, new_text=None, new_max_value=None) -> None:
        """ FAKE METHOD"""
        pass

    def start_execution(self) -> None:
        """ FAKE METHOD"""
        pass

    def stop_execution(self) -> None:
        """ FAKE METHOD"""
        pass

    def get_result(self):
        """ FAKE METHOD"""
        return None

    def set_activation(self, activate: bool) -> None:
        """ FAKE METHOD"""
        pass

    def update_and_continue(self, value=0, increment=0, text=None) -> bool:
        """ FAKE METHOD"""
        return True

    def close_window(self, destroy_window=True, _event=None) -> None:
        """ FAKE METHOD"""
        pass

    def update(self) -> None:
        """ FAKE METHOD"""
        pass
