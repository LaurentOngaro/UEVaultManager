# coding=utf-8
"""
Implementation for:
- NotificationWindow class: a class that creates a semi-transparent popup window for temporary alerts or messages.
"""
import tkinter as tk
from tkinter import font

import ttkbootstrap as ttk
from ttkbootstrap import utility

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience

DEFAULT_ICON_WIN32 = "\ue154"
DEFAULT_ICON = "\u25f0"


class NW_Settings:
    """
    Settings for the class when running as main.
    """
    title = 'notification message'
    duration = 0
    screen_index = 0


class NotificationWindow(tk.Toplevel):
    """
    A semi-transparent popup window for temporary alerts or messages.
    You can click the notification to close it.
    :param message:
        The notification message.
    :param title:
        The notification title.
    :param display_icon:
        A unicode character to display on the top-left hand corner of the notification. The default symbol is OS specific. Pass an empty string to remove the symbol.
    :param screen_index: screen index.
    :param duration:
        The number of milliseconds to show the notification. If 0 (default), then you must click the notification to close it.
    :param alert:
        Indicates whether to ring the display bell when the notification is shown.
    :param iconfont (Union[str, Font]):
        The font used to render the icon. By default, this is OS specific.
        You may need to change the font to enable better character or emoji support for the icon you want to use. Windows (Segoe UI Symbol), Linux (FreeSerif), macOS (Apple Symbol)
    """

    def __init__(
        self,
        message: str,
        title: str = 'Notification',
        sub_title: str = '',
        width: int = 400,
        height: int = 100,
        display_icon: str = None,
        screen_index: int = -1,
        duration: int = 0,
        alert: bool = False,
        iconfont=None,
    ):
        if gui_g.WindowsRef.notification:
            gui_g.WindowsRef.notification.destroy()
        super().__init__()
        self.title(title)
        try:
            # an error can occur here AFTER a tool window has been opened and closed (ex: db "import/export")
            self.style = gui_fn.set_custom_style(gui_g.s.theme_name, gui_g.s.theme_font)
            # get the root window
            root = gui_g.WindowsRef.uevm_gui or self
            self.screen_index: int = screen_index if screen_index >= 0 else int(root.winfo_screen()[1])
            self.geometry(gui_fn.center_window_on_screen(self.screen_index, width, height))
        except Exception as error:
            gui_f.log_warning(f'Error in DisplayContentWindow: {error!r}')
        gui_fn.set_icon_and_minmax(self)
        self.sub_title: str = sub_title or gui_g.s.app_title
        self.display_icon: str = display_icon
        if duration == 0:
            message += '\nCLIC ON THIS WINDOW TO CLOSE IT.'
        self.message: str = message
        self.duration: int = duration
        self.alert: bool = alert
        self.iconfont = iconfont
        self.frm_control = None
        self.iconfont: font = None
        self.titlefont: font = None
        self.is_visible: bool = True
        gui_g.WindowsRef.notification = self
        self.bind("<ButtonPress>", self.hide)

    class ControlFrame(ttk.Frame):
        """
        The frame that contains the control buttons.
        :param container: container.
        """

        def __init__(self, container):
            super().__init__(container)

            # noinspection PyArgumentList
            ttk_item = ttk.Label(self, text=container.display_icon, font=container.iconfont, anchor=tk.NW, )
            ttk_item.grid(row=0, column=0, rowspan=2, sticky=tk.NSEW, padx=(5, 0))
            if container.sub_title:
                # noinspection PyArgumentList
                ttk_item = ttk.Label(self, text=container.sub_title, font=container.titlefont, anchor=tk.NW, )
                ttk_item.grid(row=0, column=1, sticky=tk.NSEW, padx=10, pady=(5, 0))
            # noinspection PyArgumentList
            ttk_item = ttk.Label(self, text=container.message, wraplength=utility.scale_size(self, 300), anchor=tk.NW, )
            ttk_item.grid(row=1, column=1, sticky=tk.NSEW, padx=10, pady=(0, 5))

            self.bind("<ButtonPress>", container.hide)

    def _init(self) -> None:
        """
        Set up the notification window.
        """
        winsys = self.tk.call('tk', 'windowingsystem')
        self.configure(relief=tk.RAISED)

        # heading font
        _font = font.nametofont('TkDefaultFont')
        self.titlefont = font.Font(family=_font['family'], size=_font['size'] + 1, weight='bold', )
        # symbol font
        self.iconfont = font.Font(size=30, weight='bold')
        if winsys == 'win32':
            self.iconfont['family'] = 'Segoe UI Symbol'
            self.display_icon = DEFAULT_ICON_WIN32 if self.display_icon is None else self.display_icon
        elif winsys == 'x11':
            self.iconfont['family'] = 'FreeSerif'
            self.display_icon = DEFAULT_ICON if self.display_icon is None else self.display_icon
        else:
            self.iconfont['family'] = 'Apple Symbols'
            self.display_icon = DEFAULT_ICON if self.display_icon is None else self.display_icon

        self.frm_control = self.ControlFrame(self)
        self.frm_control.pack(fill=ttk.BOTH, expand=ttk.YES)

        # alert notification
        if self.alert:
            self.bell()

        # specified duration to close
        if self.duration:
            self.after(self.duration, self.hide)

        # actualize geometry
        self.update_idletasks()

    def _set_geometry(self) -> None:
        """
        Set the geometry of the window.
        """
        width = self.winfo_width()
        height = self.winfo_height()
        geometry = gui_fn.center_window_on_screen(self.screen_index, width, height, set_size=False)
        self.focus_set()
        # make the window stay on top
        self.attributes('-topmost', True)
        self.geometry(geometry)

    def show(self) -> None:
        """
        Show the notification window.
        """
        self._init()
        self._set_geometry()
        self.is_visible = True

    def hide(self, *_) -> None:
        """Destroy and close the notification window."""
        try:
            alpha = float(self.attributes("-alpha"))
            if alpha <= 0.1:
                self.is_visible = False
                self.close()
            else:
                self.attributes("-alpha", alpha - 0.1)
                self.after(25, self.hide)
        except (Exception, ):
            self.close()

    def close(self) -> None:
        """ Close the window. """
        self.destroy()


if __name__ == "__main__":
    st = NW_Settings()
    main = tk.Tk()
    main.title('FAKE MAIN Window')
    main.geometry('200x100')
    window = NotificationWindow(
        message=f'This is a notification message.\nYou can either make it appear for a specified period of time, or click to close.',
        title=st.title,
        screen_index=st.screen_index,
        duration=st.duration,
    )
    window.show()
    main.mainloop()
