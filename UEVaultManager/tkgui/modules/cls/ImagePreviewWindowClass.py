# coding=utf-8
"""
Implementation for:
- IPW_Settings: settings for the class when running as main.
- ImagePreviewWindow: window to display an image.
"""
import tkinter as tk
from tkinter import filedialog as fd
from tkinter import ttk

from ttkbootstrap import WARNING

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
    show_buttons = True


class ImagePreviewWindow(tk.Toplevel):
    """
    Window to display a text content.
    :param title: title of the window.
    :param width: width of the window.
    :param height: height of the window.
    :param icon: icon of the window.
    :param screen_index: index of the screen on which the window will be displayed.
    :param url: url of the image to display.
    :param show_buttons: if True, show the buttons to save the image and close the window.
    """

    def __init__(
        self,
        title: str = 'Image preview',
        width: int = 400,
        height: int = 400,
        icon=None,
        screen_index: int = -1,
        url: str = '',
        show_buttons: bool = False
    ):
        super().__init__()
        self.title(title)
        try:
            # an error can occur here AFTER a tool window has been opened and closed (ex: db "import/export")
            self.style = gui_fn.set_custom_style(gui_g.s.theme_name, gui_g.s.theme_font)
            # get the root window
            root = gui_g.WindowsRef.uevm_gui or self
            self.screen_index = screen_index if screen_index >= 0 else int(root.winfo_screen()[1])
            self.geometry(gui_fn.center_window_on_screen(self.screen_index, width, height))
        except Exception as error:
            gui_f.log_warning(f'Error in ImagePreviewWindow: {error!r}')
        self.width: int = width
        self.height: int = height
        gui_fn.set_icon_and_minmax(self, icon)
        self.resizable(False, False)
        self.url: str = url
        self.show_buttons = show_buttons
        if self.show_buttons:
            self.frm_control = self.ControlFrame(self)
            self.frm_control.pack(ipadx=5, ipady=5, padx=5, pady=5, fill=tk.X)
        else:
            self.bind("<Button-1>", self.on_close)
        self.bind('<Key>', self.on_key_press)
        self.frm_content = self.ContentFrame(self)
        self.frm_content.pack(ipadx=5, ipady=5, padx=5, pady=5, fill=tk.BOTH, expand=True)

        self.protocol('WM_DELETE_WINDOW', self.on_close)
        gui_g.WindowsRef.image_preview = self
        # gui_f.make_modal(self)  # could cause issue if done in the init of the class. better to be done by the caller

    class ContentFrame(ttk.Frame):
        """
        The frame containing the content of the window.
        :param container: container of the frame.
        """

        def __init__(self, container):
            super().__init__(container)
            self.canvas = tk.Canvas(self, width=container.width, height=container.height, background='grey', borderwidth=1, border=1)
            if container.show_buttons:
                self.canvas.pack(ipadx=5, ipady=5, padx=5, pady=5, fill=tk.BOTH, expand=True)
            else:
                self.canvas.place(relx=0.5, rely=0.5, anchor='center')
                self.canvas.bind("<Button-1>", container.on_close)

    class ControlFrame(ttk.Frame):
        """
        The frame containing the control buttons of the window.
        :param container: container of the frame.
        """

        def __init__(self, container):
            super().__init__(container)
            pack_def_options = {'ipadx': 0, 'ipady': 0, 'padx': 2, 'pady': 2, 'fill': tk.BOTH, 'expand': False}
            lblf_def_options = {'ipadx': 1, 'ipady': 1, 'expand': True, 'fill': tk.X}
            lblf_commands = ttk.LabelFrame(self, borderwidth=1)
            lblf_commands.pack(**lblf_def_options)
            ttk.Button(lblf_commands, text='Save To File', command=container.save_image).pack(**pack_def_options, side=tk.LEFT)
            # noinspection PyArgumentList
            # (bootstyle is not recognized by PyCharm)
            ttk.Button(lblf_commands, text='Close', command=container.close_window, bootstyle=WARNING).pack(**pack_def_options, side=tk.RIGHT)

    def on_close(self, _event=None) -> None:
        """
        Event when the window is closing.
        :param _event: event that triggered the call of this function.
        """
        self.close_window()

    def on_key_press(self, event):
        """
        Event when a key is pressed.
        :param event: event that triggered the call of this function.
        """
        if event.keysym == 'Escape':
            self.on_close()
        return 'break'

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

    def save_image(self) -> str:
        """
        Save the image to a file.
        :return: the filename of the saved image.
        """
        initial_dir = gui_g.s.last_opened_folder
        filename = fd.asksaveasfilename(
            title='Choose a PNG file to save the image to', initialdir=initial_dir, filetypes=gui_g.s.data_filetypes_all + gui_g.s.data_filetypes_png
        )
        if filename:
            # noinspection PyUnresolvedReferences
            if gui_f.save_image_to_png(self.frm_content.canvas.image, filename):
                gui_f.box_message(f'Image Saved to {filename}')
                return filename
            else:
                gui_f.box_message(f'Error saving image to {filename}')
        return ''


if __name__ == '__main__':
    st = IPW_Settings()
    main = tk.Tk()
    main.title('FAKE MAIN Window')
    main.geometry('200x100')
    ipw = ImagePreviewWindow(title=st.title, url=st.url, width=st.width, height=st.height, show_buttons=st.show_buttons)
    ipw.display()
    main.mainloop()
