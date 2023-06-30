# coding=utf-8
"""
implementation for:
- FakeProgressWindow: a fake ProgressWindow object to use when no ProgressWindow object is provided and provide the same interface
"""


class FakeProgressWindow:
    """
    A fake ProgressWindow object to use when no ProgressWindow object is provided and provide the same interface
    Usefull to avoid importing the ProgressWindow class and all its dependencies (all the tkinter stuff)
    """

    def __init__(self, title='Dummy'):
        self.title = title
        self.text = ''
        self.value = 0
        self.max_value = 0
        self.quit_on_close = False
        self.continue_execution = True

    def reset(self, new_title=None, new_value=None, new_text=None, new_max_value=None) -> None:
        """ FAKE METHOD"""
        self.title = new_title
        self.text = new_text
        self.value = new_value
        self.max_value = new_max_value

    def update_and_continue(self, value=0, increment=0, text=None) -> bool:
        """ FAKE METHOD"""
        if value:
            self.value = value
        else:
            self.value += increment
        self.text = text
        return True

    def close_window(self, destroy_window=True, _event=None) -> None:
        """ FAKE METHOD"""
        self.quit_on_close = destroy_window
