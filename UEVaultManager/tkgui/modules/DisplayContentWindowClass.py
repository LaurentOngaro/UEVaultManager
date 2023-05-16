# coding=utf-8
"""
Implementation for:
- DisplayContentWindow: the window to display a text content
"""
import os
import tkinter as tk
from tkinter import filedialog as fd
from tkinter import ttk

from ttkbootstrap.constants import *

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.ExtendedWidgetClasses import ExtendedText


# class DisplayContentWindow(tk.Tk if tk._default_root is None else tk.Toplevel):
class DisplayContentWindow(tk.Toplevel):
    """
    Window to display a text content
    :param title: the title of the window
    :param width: the width of the window
    :param height: the height of the window
    :param icon: the icon of the window
    :param screen_index: the index of the screen on which the window will be displayed
    :param quit_on_close: whether to quit the application when the window is closed

    """

    def __init__(self, title: str, width: int = 400, height: int = 430, icon=None, screen_index=0, quit_on_close=False):
        super().__init__()
        self.title(title)
        style = gui_f.set_custom_style(gui_g.s.theme_name, gui_g.s.theme_font)
        self.style = style
        # if tk._default_root == self :
        #     style = gui_f.set_custom_style(gui_g.s.theme_name, gui_g.s.theme_font)
        #     print(f"style SELF = {style.theme_use()}")
        # else:
        #     style = ttk.Style(tk._default_root)
        #     print(f"style ROOT = {style.theme_use()}")
        #
        # self.style = style

        geometry = gui_f.center_window_on_screen(screen_index, height, width)
        self.geometry(geometry)

        if icon is None:
            self.attributes('-toolwindow', True)
        else:
            # windows only (remove the minimize/maximize buttons and the icon)
            icon = gui_f.path_from_relative_to_absolute(icon)
            if icon != '' and os.path.isfile(icon):
                self.iconbitmap(icon)
        self.resizable(True, False)
        self.quit_on_close = quit_on_close

        self.content_frame = self.ContentFrame(self)
        self.control_frame = self.ControlFrame(self)

        self.content_frame.pack(ipadx=5, ipady=5, padx=5, pady=5, fill=tk.X)
        self.control_frame.pack(ipadx=5, ipady=5, padx=5, pady=5, fill=tk.X)

        self.bind('<Key>', self.on_key_press)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        gui_g.display_content_window_ref = self

    class ContentFrame(ttk.Frame):
        """
        The frame containing the content of the window
        :param container: the container of the frame
        """

        def __init__(self, container):
            super().__init__(container)
            pack_def_options = {'ipadx': 3, 'ipady': 3, 'padx': 5, 'pady': 5, 'fill': tk.X}

            text_content = ExtendedText(self)
            text_content.pack(**pack_def_options)
            self.text_content = text_content

    class ControlFrame(ttk.Frame):
        """
        The frame containing the control buttons of the window
        :param container: the container of the frame
        """

        def __init__(self, container):
            super().__init__(container)
            pack_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.BOTH, 'expand': False}
            lblf_def_options = {'ipadx': 1, 'ipady': 1, 'expand': True, 'fill': tk.X}
            lblf_commands = ttk.LabelFrame(self, text='Commands')
            lblf_commands.pack(**lblf_def_options)
            # noinspection PyArgumentList
            ttk.Button(lblf_commands, text='Clean content', command=container.clean).pack(**pack_def_options, side=tk.LEFT)
            # noinspection PyArgumentList
            ttk.Button(lblf_commands, text='Save To File', command=container.save_to_file).pack(**pack_def_options, side=tk.LEFT)
            # noinspection PyArgumentList
            ttk.Button(lblf_commands, text='Close', command=container.on_close, bootstyle=WARNING).pack(**pack_def_options, side=tk.RIGHT)

    def on_key_press(self, event) -> None:
        """
        Event when a key is pressed
        :param event: the event that triggered the call of this function
        """
        if event.keysym == 'Escape':
            self.on_close()

    def on_close(self, _event=None) -> None:
        """
        Event when the window is closing
        :param _event: the event that triggered the call of this function
        """
        self.close_window()

    def close_window(self) -> None:
        """
        Close the window
        """
        gui_g.display_content_window_ref = None
        if self.quit_on_close:
            self.quit()
        else:
            self.destroy()

    def display(self, content: str) -> None:
        """
        Display the content in the window
        :param content: the text to print
        """
        self.content_frame.text_content.delete('1.0', tk.END)
        self.content_frame.text_content.insert(tk.END, content)

    def clean(self) -> None:
        """
        Clean the content of the window
        """
        self.content_frame.text_content.delete('1.0', tk.END)

    def save_to_file(self) -> str:
        """
        Save the content displayed to a file
        """
        initial_dir = os.path.dirname(gui_g.s.csv_filename)
        filename = fd.asksaveasfilename(
            title='Choose a file to save data to', initialdir=initial_dir, filetypes=gui_g.s.data_filetypes, initialfile='UEVM_output.txt'
        )
        if filename:
            with open(filename, 'w') as f:
                f.write(self.content_frame.text_content.get('1.0', tk.END))
            gui_f.box_message(f'Content Saved to {filename}')
        return filename
