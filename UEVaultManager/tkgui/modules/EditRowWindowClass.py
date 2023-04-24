import os
import tkinter as tk
import UEVaultManager.tkgui.modules.globals as g
from tkinter import messagebox, ttk
from UEVaultManager.tkgui.modules.functions import center_window_on_screen, path_from_relative_to_absolute
from UEVaultManager.tkgui.modules.settings import *


class EditRowWindow(tk.Toplevel):

    def __init__(self, parent: ttk.Frame, title: str, width=600, height=800, icon='', screen_index=0, editable_table=None):
        super().__init__(parent)
        self.title(title)
        geometry = center_window_on_screen(screen_index, height, width)
        self.geometry(geometry)
        icon = path_from_relative_to_absolute(icon)
        if icon != '' and os.path.isfile(icon):
            self.iconbitmap(icon)

        self.editable_table = editable_table
        self.must_save = False
        self.initial_values = []
        self.width = width

        # the photoimage is stored is the variable to avoid garbage collection
        # see: https://stackoverflow.com/questions/30210618/image-not-getting-displayed-on-tkinter-through-label-widget
        self.image_preview = None

        self.resizable(True, False)

        self.content_frame = self.ContentFrame(self)
        self.control_frame = self.ControlFrame(self)

        self.content_frame.pack(ipadx=5, ipady=5, fill=tk.X)
        self.control_frame.pack(ipadx=5, ipady=5, fill=tk.X)

        self.bind('<Key>', self.on_key_press)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    class ContentFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__(container)

    class ControlFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__(container)
            pack_def_options = {'ipadx': 2, 'ipady': 2, 'fill': tk.X}
            grid_def_options = {'ipadx': 5, 'ipady': 5, 'padx': 2, 'pady': 2, 'sticky': tk.NSEW}

            lblf_navigation = ttk.LabelFrame(self, text='Navigation')
            lblf_navigation.grid(row=0, column=0, **grid_def_options)
            btn_prev = ttk.Button(lblf_navigation, text='Prev Asset', command=container.prev_asset)
            btn_prev.pack(**pack_def_options, side=tk.LEFT)
            btn_next = ttk.Button(lblf_navigation, text='Next Asset', command=container.next_asset)
            btn_next.pack(**pack_def_options, side=tk.RIGHT)

            lbf_preview = ttk.LabelFrame(self, text="Image Preview")
            lbf_preview.grid(row=0, column=1, **grid_def_options)
            canvas_preview = tk.Canvas(lbf_preview, width=preview_max_width, height=preview_max_height, highlightthickness=0)
            canvas_preview.pack()
            canvas_preview.create_rectangle((0, 0), (preview_max_width, preview_max_height), fill='black')

            lblf_actions = ttk.LabelFrame(self, text='Actions')
            lblf_actions.grid(row=0, column=2, **grid_def_options)
            btn_open_url = ttk.Button(lblf_actions, text="Open URL", command=container.open_asset_url)
            btn_open_url.pack(**pack_def_options, side=tk.LEFT)
            bnt_save = ttk.Button(lblf_actions, text='Save Changes', command=container.save_change)
            bnt_save.pack(**pack_def_options, side=tk.LEFT)
            btn_on_close = ttk.Button(lblf_actions, text='Cancel', command=container.on_close)
            btn_on_close.pack(**pack_def_options, side=tk.RIGHT)

            # Configure the columns to take all the available width
            self.columnconfigure(0, weight=1)
            self.columnconfigure(1, weight=2)
            self.columnconfigure(2, weight=1)

            self.canvas_preview = canvas_preview

    def on_close(self, _event=None):
        current_values = self.editable_table.get_selected_row_values()
        # current_values is empty is save_button has been pressed because global variables have been cleared in save_changes()
        self.must_save = current_values and self.initial_values != current_values
        if self.must_save:
            if messagebox.askokcancel('Close the window', 'Changes have been made. Do you want to save them ?'):
                self.save_change()
        self.close_window()

    def close_window(self, _event=None):
        g.edit_row_window_ref = None
        self.destroy()

    def save_change(self):
        self.must_save = False
        self.editable_table.save_record()

    def on_key_press(self, event):
        if event.keysym == 'Escape':
            self.on_close()
        elif event.keysym == 'Return':
            self.save_change()

    def prev_asset(self):
        self.editable_table.move_to_prev_record()

    def next_asset(self):
        self.editable_table.move_to_next_record()

    def open_asset_url(self):
        self.editable_table.open_asset_url()
