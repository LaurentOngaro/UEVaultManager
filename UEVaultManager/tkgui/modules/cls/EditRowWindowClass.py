# coding=utf-8
"""
Implementation for:
- EditRowWindow: the window to edit a row.
"""
import tkinter as tk
from tkinter import ttk

from ttkbootstrap.constants import *

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience


class EditRowWindow(tk.Toplevel):
    """
    The window to edit a row.
    :param parent: the parent window.
    :param title: the title of the window.
    :param width: the width of the window.
    :param height: the height of the window.
    :param icon: the icon of the window.
    :param screen_index: the index of the screen on which the window will be displayed.
    :param editable_table: the table to edit.
    """
    must_save: bool = False

    def __init__(self, parent, title: str, width: int = 600, height: int = 800, icon=None, screen_index: int = 0, editable_table=None):
        super().__init__(parent)
        self.title(title)
        try:
            # an error can occur here AFTER a tool window has been opened and closed (ex: db "import/export")
            self.style = gui_fn.set_custom_style(gui_g.s.theme_name, gui_g.s.theme_font)
        except Exception as error:
            gui_f.log_warning(f'Error in EditCellWindowClass: {error}')
        self.geometry(gui_fn.center_window_on_screen(screen_index, width, height))
        gui_fn.set_icon_and_minmax(self, icon)
        self.resizable(True, False)

        self.editable_table = editable_table
        self.initial_values = []
        self.width: int = width
        # the photoimage is stored is the variable to avoid garbage collection
        # see: https://stackoverflow.com/questions/30210618/image-not-getting-displayed-on-tkinter-through-label-widget
        self.canvas_image = None

        self.control_frame = self.ControlFrame(self)
        self.content_frame = self.ContentFrame(self)

        self.control_frame.pack(ipadx=5, ipady=5, fill=tk.X)
        self.content_frame.pack(ipadx=5, ipady=5, padx=5, pady=5, fill=tk.X)

        self.bind('<Tab>', self._focus_next_widget)
        self.bind('<Control-Tab>', self._focus_next_widget)
        self.bind('<Shift-Tab>', self._focus_prev_widget)
        self.bind('<Key>', self.on_key_press)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        gui_g.edit_row_window_ref = self

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
        The frame containing the editable fields.
        :param container: the parent window.
        """

        def __init__(self, container):
            super().__init__(container)

    class ControlFrame(ttk.Frame):
        """
        The frame containing the buttons.
        :param container: the parent window.
        """

        def __init__(self, container):
            super().__init__(container)
            pack_def_options = {'ipadx': 2, 'ipady': 2, 'fill': tk.X, 'anchor': tk.NW}
            grid_def_options = {'ipadx': 5, 'ipady': 5, 'padx': 2, 'pady': 2, 'sticky': tk.NSEW}

            lblf_navigation = ttk.LabelFrame(self, text='Navigation')
            lblf_navigation.grid(row=0, column=0, **grid_def_options)
            btn_prev_asset = ttk.Button(lblf_navigation, text='Prev Asset', command=container.prev_asset)
            btn_prev_asset.pack(**pack_def_options, side=tk.LEFT)
            btn_next_asset = ttk.Button(lblf_navigation, text='Next Asset', command=container.next_asset)
            btn_next_asset.pack(**pack_def_options, side=tk.RIGHT)

            lbf_preview = ttk.LabelFrame(self, text='Image Preview')
            lbf_preview.grid(row=0, column=1, **grid_def_options)
            canvas_image = tk.Canvas(lbf_preview, width=gui_g.s.preview_max_width, height=gui_g.s.preview_max_height, highlightthickness=0)
            canvas_image.pack()
            canvas_image.create_rectangle((0, 0), (gui_g.s.preview_max_width, gui_g.s.preview_max_height), fill='black')

            lblf_actions = ttk.LabelFrame(self, text='Actions')
            lblf_actions.grid(row=0, column=2, **grid_def_options)
            btn_open_url = ttk.Button(lblf_actions, text="Open URL", command=container.open_asset_url)
            btn_open_url.pack(**pack_def_options, side=tk.LEFT)
            # noinspection PyArgumentList
            btn_on_close = ttk.Button(lblf_actions, text='Close', command=container.on_close, bootstyle=WARNING)
            btn_on_close.pack(**pack_def_options, side=tk.RIGHT)
            # noinspection PyArgumentList
            bnt_save = ttk.Button(lblf_actions, text='Save Changes', command=container.save_changes, bootstyle=INFO)
            bnt_save.pack(**pack_def_options, side=tk.RIGHT)

            # Configure the columns to take all the available width
            self.columnconfigure(0, weight=1)
            self.columnconfigure(1, weight=2)
            self.columnconfigure(2, weight=1)

            self.canvas_image = canvas_image

    def on_close(self, _event=None) -> None:
        """
        Event when the window is closing.
        :param _event: the event that triggered the call of this function.
        """
        current_values = self.editable_table.get_edited_row_values()
        # current_values is empty is save_button has been pressed because global variables have been cleared in save_changess()
        self.must_save = current_values and self.initial_values != current_values
        if self.must_save:
            if gui_f.box_yesno('Changes have been made in the window. Do you want to keep them ?'):
                self.save_changes()
        self.close_window()

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

    def close_window(self) -> None:
        """
        Close the window.
        """
        gui_g.edit_row_window_ref = None
        self.editable_table.reset_style()
        self.destroy()

    def save_changes(self) -> None:
        """
        Save the changes (Wrapper).
        """
        self.must_save = False
        self.editable_table.save_edit_row()

    def prev_asset(self) -> None:
        """
        Go to the previous asset (Wrapper).
        """
        row_number = self.editable_table.prev_row()
        self.editable_table.edit_row(row_number)

    def next_asset(self) -> None:
        """
        Go to the next asset (Wrapper).
        """
        row_number = self.editable_table.next_row()
        self.editable_table.edit_row(row_number)

    def open_asset_url(self) -> None:
        """
        Open the asset URL (Wrapper).
        """
        self.editable_table.open_asset_url()
