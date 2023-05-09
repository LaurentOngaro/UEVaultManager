import tkinter as tk
import os
from tkinter import ttk

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience


class EditCellWindow(tk.Toplevel):

    def __init__(self, parent, title: str, width=600, height=400, icon=None, screen_index=0, editable_table=None):
        super().__init__(parent)
        self.title(title)
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

        def __init__(self, container):
            super().__init__(container)

    class ControlFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__(container)
            pack_def_options = {'ipadx': 3, 'ipady': 3, 'fill': tk.X}
            ttk.Button(self, text='Cancel', command=container.on_close).pack(**pack_def_options, side=tk.RIGHT)
            ttk.Button(self, text='Save Changes', command=container.save_change).pack(**pack_def_options, side=tk.RIGHT)

    def on_close(self, _event=None):
        current_values = self.editable_table.get_edit_cell_values()
        # current_values is empty if save_button has been pressed because global variables have been cleared in save_changes()
        self.must_save = current_values and self.initial_values != current_values
        if self.must_save:
            if gui_f.box_yesno('Changes have been made in the window. Do you want to keep them ?'):
                self.save_change()
        self.close_window()

    def close_window(self, _event=None):
        gui_g.edit_cell_window_ref = None
        self.destroy()

    def save_change(self):
        self.must_save = False
        self.editable_table.save_edit_cell_value()

    def on_key_press(self, event):
        if event.keysym == 'Escape':
            self.on_close()
        elif event.keysym == 'Return':
            self.save_change()
