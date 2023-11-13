# coding=utf-8
"""
Implementation for:
- IPW_Settings: settings for the class when running as main.
- ImagePreviewWindow: window to display an image.
"""
import tkinter as tk
from tkinter import ttk

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience


class IPW_Settings:
    """
    Settings for the class when running as main.
    """
    title = 'Display an image'
    url = 'https://cdn1.epicgames.com/ue/product/Thumbnail/FurryS1FantasyWarrior_thumb-284x284-1c25e20033317ac22a5b8f3ecf658d7c.png'
    width = 400
    height = 400


class ImagePreviewWindow(tk.Toplevel):
    """
    Window to display a text content.
    :param title: title of the window.
    :param width: width of the window.
    :param height: height of the window.
    :param icon: icon of the window.
    :param screen_index: index of the screen on which the window will be displayed.
    :param url: url of the image to display.
    """

    def __init__(self, title: str = 'Image preview', width: int = 400, height: int = 400, icon=None, screen_index: int = 0, url: str = '', ):
        if not url:
            return

        super().__init__()
        self.title(title)
        try:
            # an error can occur here AFTER a tool window has been opened and closed (ex: db "import/export")
            self.style = gui_fn.set_custom_style(gui_g.s.theme_name, gui_g.s.theme_font)
        except Exception as error:
            gui_f.log_warning(f'Error in ImagePreviewWindow: {error!r}')
        self.url: str = url
        self.width: int = width
        self.height: int = height
        self.geometry(gui_fn.center_window_on_screen(screen_index, width, height))
        gui_fn.set_icon_and_minmax(self, icon)
        self.resizable(False, False)
        self.frm_content = self.ContentFrame(self)
        self.frm_content.pack(ipadx=5, ipady=5, padx=5, pady=5, fill=tk.X)
        self.protocol('WM_DELETE_WINDOW', self.close_window)
        self.bind("<Button-1>", self.close_window)
        gui_g.WindowsRef.image_preview = self
        # gui_f.make_modal(self)  # could cause issue if done in the init of the class. better to be done by the caller

    class ContentFrame(ttk.Frame):
        """
        The frame containing the content of the window.
        :param container: container of the frame.
        """

        def __init__(self, container):
            super().__init__(container)
            self.canvas = tk.Canvas(container, width=container.width, height=container.height, background='grey', borderwidth=1)
            self.canvas.place(relx=0.5, rely=0.5, anchor='center')
            self.canvas.bind("<Button-1>", container.close_window)

    def on_close(self, _event=None) -> None:
        """
        Event when the window is closing.
        :param _event: event that triggered the call of this function.
        """
        self.close_window()

    def close_window(self) -> None:
        """
        Close the window.
        """
        self.destroy()
        gui_g.WindowsRef.image_preview = None

    def display(self, url: str = '') -> bool:
        """
        Display the image in the window.
        :return: True if the image was displayed, False otherwise.
        """
        if not url:
            url = self.url
        if not url:
            return False
        self.focus_set()
        # send the window to the front
        self.attributes('-topmost', True)
        return gui_f.show_asset_image(url, self.frm_content.canvas, x=int(self.width / 2), y=int(self.height / 2))


if __name__ == '__main__':
    st = IPW_Settings()
    main = tk.Tk()
    main.title('FAKE MAIN Window')
    main.geometry('200x100')
    ImagePreviewWindow(title=st.title, url=st.url, width=st.width, height=st.height).display()
    main.mainloop()
