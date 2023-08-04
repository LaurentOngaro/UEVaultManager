# coding=utf-8
"""
Implementation for:
- EditCellWindow: the window to edit a cell.
"""
import tkinter as tk
from tkinter import ttk

from ttkbootstrap.constants import *

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience


class EditCellWindow(tk.Toplevel):
    """
    The window to edit a cell.
    :param parent: the parent window.
    :param title: the title of the window.
    :param width: the width of the window.
    :param height: the height of the window.
    :param icon: the icon of the window.
    :param screen_index: the index of the screen on which the window will be displayed.
    :param editable_table: the table to edit.
    """

    def __init__(self, parent, title: str, width: int = 600, height: int = 400, icon=None, screen_index=0, editable_table=None):
        super().__init__(parent)
        self.title(title)
        style = gui_fn.set_custom_style(gui_g.s.theme_name, gui_g.s.theme_font)
        self.style = style
        geometry = gui_fn.center_window_on_screen(screen_index, width, height)
        self.geometry(geometry)
        gui_fn.set_icon_and_minmax(self, icon)
        self.resizable(True, False)

        self.editable_table = editable_table
        self.must_save = False
        self.initial_values = []

        self.content_frame = self.ContentFrame(self)
        self.control_frame = self.ControlFrame(self)

        self.content_frame.pack(ipadx=5, ipady=5, padx=5, pady=5, fill=tk.X)
        self.control_frame.pack(ipadx=5, ipady=5, padx=5, pady=5, fill=tk.X)

        self.bind('<Key>', self.on_key_press)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        gui_g.edit_cell_window_ref = self

    class ContentFrame(ttk.Frame):
        """
        The frame containing the content of the window.
        :param container: the container of the frame.
        """

        def __init__(self, container):
            super().__init__(container)

    class ControlFrame(ttk.Frame):
        """
        The frame containing the control buttons of the window.
        :param container: the container of the frame.
        """

        def __init__(self, container):
            super().__init__(container)
            grid_def_options = {'ipadx': 5, 'ipady': 5, 'padx': 2, 'pady': 2, 'sticky': tk.NSEW}
            # (bootstyle is not recognized by PyCharm)
            ttk.Label(self, text='Respect the initial format when changing a value').grid(row=0, column=0, columnspan=2, **grid_def_options)
            # noinspection PyArgumentList
            ttk.Button(self, text='Save Changes', command=container.save_change, bootstyle=INFO).grid(row=1, column=0, **grid_def_options)
            # noinspection PyArgumentList
            ttk.Button(self, text='Close', command=container.on_close, bootstyle=WARNING).grid(row=1, column=1, **grid_def_options)
            self.columnconfigure('all', weight=1)
            self.rowconfigure('all', weight=1)

    def set_size(self, width: int, height: int) -> None:
        """
        Set the size (aka geometry) the window.
        :param width: the width.
        :param height: the height
        
        Note: The window is centered on the screen.
        """
        geometry = gui_fn.center_window_on_screen(0, width, height)
        self.geometry(geometry)

    def on_key_press(self, event) -> None:
        """
        Event when a key is pressed.
        :param event: the event that triggered the call of this function.
        """
        if event.keysym == 'Escape':
            self.on_close()
        elif event.keysym == 'Return':
            self.save_change()

    def on_close(self, _event=None) -> None:
        """
        Event when the window is closing.
        :param _event: the event that triggered the call of this function.
        """
        current_values = self.editable_table.get_edit_cell_values()
        # current_values is empty if save_button has been pressed because global variables have been cleared in save_changes()
        self.must_save = current_values and self.initial_values != current_values
        if self.must_save:
            if gui_f.box_yesno('Changes have been made in the window. Do you want to keep them ?'):
                self.save_change()
        self.close_window()

    def close_window(self) -> None:
        """
        Close the window.
        """
        gui_g.edit_cell_window_ref = None
        self.editable_table.reset_style()
        self.destroy()

    def save_change(self) -> None:
        """
        Save the changes made in the window  (Wrapper).
        """
        self.must_save = False
        self.editable_table.save_edit_cell_value()
