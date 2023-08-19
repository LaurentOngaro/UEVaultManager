# coding=utf-8
"""
Implementation for:
- DisplayContentWindow: the window to display a text content.
"""
import os
import tkinter as tk
from tkinter import filedialog as fd
from tkinter import ttk

from ttkbootstrap.constants import *

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.cls.ExtendedWidgetClasses import ExtendedText


# class DisplayContentWindow(tk.Tk if tk._default_root is None else tk.Toplevel):
class DisplayContentWindow(tk.Toplevel):
    """
    Window to display a text content.
    :param title: the title of the window.
    :param width: the width of the window.
    :param height: the height of the window.
    :param icon: the icon of the window.
    :param screen_index: the index of the screen on which the window will be displayed.
    :param quit_on_close: whether to quit the application when the window is closed.
    """
    keep_existing: bool = False  # whether to keep the existing content when adding a new one

    def __init__(self, title: str, width: int = 600, height: int = 430, icon=None, screen_index: int = 0, quit_on_close: bool = False):
        super().__init__()
        self.title(title)
        self.style = gui_fn.set_custom_style(gui_g.s.theme_name, gui_g.s.theme_font)
        self.geometry(gui_fn.center_window_on_screen(screen_index, width, height))
        gui_fn.set_icon_and_minmax(self, icon)
        self.resizable(True, False)
        self.quit_on_close = quit_on_close
        self.content_frame = self.ContentFrame(self)
        self.control_frame = self.ControlFrame(self)

        self.content_frame.pack(ipadx=5, ipady=5, padx=5, pady=5, fill=tk.X)
        self.control_frame.pack(ipadx=5, ipady=5, padx=5, pady=5, fill=tk.X)

        self.bind('<Tab>', self._focus_next_widget)
        self.bind('<Control-Tab>', self._focus_next_widget)
        self.bind('<Shift-Tab>', self._focus_prev_widget)
        self.bind('<Key>', self.on_key_press)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        gui_g.display_content_window_ref = self

    @staticmethod
    def _focus_next_widget(event):
        event.widget.tk_focusNext().focus()
        return 'break'

    @staticmethod
    def _focus_prev_widget(event):
        event.widget.tk_focusPrev().focus()
        return 'break'

    class ContentFrame(ttk.Frame):
        """
        The frame containing the content of the window.
        :param container: the container of the frame.
        """

        def __init__(self, container):
            super().__init__(container)
            pack_def_options = {'ipadx': 3, 'ipady': 3}

            text_content = ExtendedText(self)
            scrollbar = ttk.Scrollbar(self)
            scrollbar.config(command=text_content.yview)
            text_content.config(yscrollcommand=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y, **pack_def_options)
            text_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, **pack_def_options)

            self.text_content = text_content

    class ControlFrame(ttk.Frame):
        """
        The frame containing the control buttons of the window.
        :param container: the container of the frame.
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
            ttk.Button(lblf_commands, text='Save To File', command=container.save_changes).pack(**pack_def_options, side=tk.LEFT)
            # noinspection PyArgumentList
            ttk.Button(lblf_commands, text='Close', command=container.on_close, bootstyle=WARNING).pack(**pack_def_options, side=tk.RIGHT)

    # noinspection DuplicatedCode
    def on_key_press(self, event):
        """
                Event when a key is pressed.
                :param event: the event that triggered the call of this function.
                """
        control_pressed = event.state == 4 or event.state & 0x00004 != 0
        if event.keysym == 'Escape':
            self.on_close()
        elif control_pressed and (event.keysym == 's' or event.keysym == 'S'):
            self.save_changes()
        return 'break'

    def on_close(self, _event=None) -> None:
        """
        Event when the window is closing.
        :param _event: the event that triggered the call of this function.
        """
        self.close_window()

    def close_window(self) -> None:
        """
        Close the window.
        """
        gui_g.display_content_window_ref = None
        if self.quit_on_close:
            self.quit()
        else:
            self.destroy()

    def display(self, content='', keep_mode=True) -> None:
        """
        Display the content in the window. By default, i.e. keep_mode==True, each new call adds the content to the existing content with a new line.
        :param content: the text to print.
        :param keep_mode: whether to keep the existing content when a new one is added.
        """
        if self.keep_existing:
            content += '\n'
            self.content_frame.text_content.insert(tk.END, content)
        else:
            self.content_frame.text_content.delete('1.0', tk.END)
            self.content_frame.text_content.insert(tk.END, content)
        # set the mode at the end to allow using display() to be used to change the mode for the next call
        self.keep_existing = keep_mode

    def clean(self) -> None:
        """
        Clean the content of the window.
        """
        self.content_frame.text_content.delete('1.0', tk.END)

    def save_changes(self) -> str:
        """
        Save the content displayed to a file.
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
