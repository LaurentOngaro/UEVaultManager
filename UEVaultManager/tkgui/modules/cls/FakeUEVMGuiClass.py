# coding=utf-8
"""
Implementation for:
- FakeUEVMGuiClass: hidden main window for the application.
"""
import time

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
        self.progress_window = None
        self.update_delay: int = 1000
        self.editable_table = None

    def mainloop(self, n=0, call_tk_mainloop: bool = True):
        """
        Mainloop method
        :param n: threshold.
        :param call_tk_mainloop: if True, call the original mainloop method.

        Overrided to add logging function for debugging
        """
        if call_tk_mainloop or self.progress_window is None:
            self.after(self.update_delay, self.update_progress)
            print(f'starting mainloop in {__name__}')
            # the original mainloop could not be called sometime in a CLI session because it will block the console
            self.tk.mainloop(n)
        else:
            print(f'starting update progress loop in {__name__}')
            while self.progress_window.continue_execution:
                time.sleep(self.update_delay / 2)
                self.update_idletasks()
                time.sleep(self.update_delay / 2)
                self.update_progress()
        print(f'ending mainloop or update progress loop in {__name__}')

    def update_progress(self):
        """
        Update the child progress windows.
        """
        self.update_idletasks()
        if self.progress_window:
            self.progress_window.update()
            # print('UPDATE')
        self.after(self.update_delay, self.update_progress)
