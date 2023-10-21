# coding=utf-8
"""
Implementation for:
- FakeUEVMGuiClass: a hidden main window for the application.
"""
import ttkbootstrap as ttk


class FakeUEVMGuiClass(ttk.Window):
    """
    This class is used to create a hidden main window for the application.
    Usefull for creating a window that is not visible to the user, but still has the ability to child windows.
    """
    is_fake = True

    def __init__(self):
        super().__init__()
        self.title('UEVMGui Hidden window')
        self.geometry('100x150')
        self.withdraw()
