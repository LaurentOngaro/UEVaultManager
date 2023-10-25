# coding=utf-8
"""
Implementation for:
- FakeUEVMGuiClass: hidden main window for the application.
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
        self.progress_window = None

    def mainloop(self, n=0):
        """
        Mainloop method

        Overrided to add logging function for debugging
        """
        print(f'starting mainloop in {__name__}')
        self.after(2000, self.update_progress_windows)
        # the original mainloop is not called because in a CLI session, it will block the console
        # we only update child the progress windows
        # self.tk.mainloop(n)
        print(f'ending mainloop in {__name__}')

    def update_progress_windows(self):
        """
        Update the child progress windows.
        """
        if self.progress_window:
            self.progress_window.update()
            print('UPDATE')
        self.after(2000, self.update_progress_windows)
