# coding=utf-8
"""
Implementation for:
- UEVMGuiHiddenRoot: a hidden root window for the application.
"""
import ttkbootstrap as ttk


class UEVMGuiHiddenRoot(ttk.Window):
    """
    This class is used to create a hidden root window for the application.
    Usefull for creating a window that is not visible to the user, but still has the ability to child windows.
    """
    def __init__(self):
        super().__init__()
        self.title('UEVMGui Hidden window')
        self.geometry('100x150')
        self.withdraw()
