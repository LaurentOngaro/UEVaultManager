import os
import tkinter as tk
import UEVaultManager.tkgui.modules.globals as g
from tkinter import messagebox, ttk


class EditRowWindow(tk.Toplevel):

    def __init__(self, parent, title: str, geometry: str, icon: str, editable_table):
        super().__init__(parent)

        self.title(title)
        self.geometry(geometry)
        if icon != '' and os.path.isfile(icon):
            self.iconbitmap(icon)

        self.editable_table = editable_table
        self.must_save = False
        self.initial_values = []

        # the photoimage is stored is the variable to avoid garbage collection
        # see: https://stackoverflow.com/questions/30210618/image-not-getting-displayed-on-tkinter-through-label-widget
        self.image_preview = None

        # windows only (remove the minimize/maximize button)
        # self.attributes('-toolwindow', True)
        self.resizable(True, False)

        self.content_frame = self.ContentFrame(self)
        self.control_frame = self.ControlFrame(self)
        self.preview_frame = self.PreviewFrame(self)

        self.content_frame.pack(ipadx=5, ipady=5, fill=tk.X)
        self.control_frame.pack(ipadx=5, ipady=5, fill=tk.X)
        self.preview_frame.pack(fill=tk.X)

        self.bind('<Key>', self.on_key_press)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    class ContentFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__(container)
            self['padding'] = 5

    class ControlFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__(container)
            self['padding'] = 5
            pack_def_options = {'ipadx': 2, 'ipady': 2, 'fill': tk.X}
            ttk.Button(self, text='Prev Asset', command=container.prev_asset).pack(**pack_def_options, side=tk.LEFT)
            ttk.Button(self, text='Next Asset', command=container.next_asset).pack(**pack_def_options, side=tk.LEFT)
            ttk.Button(self, text='Cancel', command=container.on_close).pack(**pack_def_options, side=tk.RIGHT)
            ttk.Button(self, text='Save Changes', command=container.save_change).pack(**pack_def_options, side=tk.RIGHT)

    class PreviewFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__(container)
            self.text = 'Image preview'
            self['padding'] = 5

            self.canvas = tk.Canvas(self, width=200, height=200, bg='lightgrey')
            self.canvas.pack(anchor=tk.CENTER)
            self.canvas.create_rectangle(24, 24, 176, 176, fill='white')

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
