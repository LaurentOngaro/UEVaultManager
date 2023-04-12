"""
working file for the GUI integration in UEVaultManager

Things to be done:
- fix the edit_cell window
- add columns filtering to the table. See tk_tablefilter_ex.py
- add pagination info in a new frame. See tk_tablefilter_ex.py
- check the TODOs
- in edit_row_window, implement the prev and next buttons
- split the code into several files.
- Extract the classes in separate files
- migrate the code into the UEVaultManager code base
- document the new features
- update the PyPi package
"""

import tkinter as tk
import webbrowser
import os
from io import BytesIO
from tkinter import filedialog as fd
from tkinter import ttk
from tkinter.messagebox import showinfo
from urllib.parse import quote_plus
from urllib.request import urlopen

import pandas as pd
from pandastable import Table, TableModel
from PIL import ImageTk, Image

appTitle = 'UEVM Gui'


def todo_message():
    msg = 'Not implemented yet'
    showinfo(title=appTitle, message=msg)


class WebImage:

    def __init__(self, url):
        if url is None or url == '':
            return
        self.__image_pil = None
        self.__image_tk = None
        self.url = url
        encoded_url = quote_plus(url, safe='/:&')
        try:
            my_page = urlopen(encoded_url)
            my_picture = BytesIO(my_page.read())
            self.__image_pil = Image.open(my_picture)
            self.__image_tk = ImageTk.PhotoImage(self.__image_pil)
        except Exception as e:
            print(f'image could not be read from url {self.url}.\nError:{e}')

    def get(self):
        return self.__image_tk

    def get_resized(self, new_width, new_height):
        try:
            self.__image_pil.thumbnail((new_width, new_height))
            self.__image_tk = ImageTk.PhotoImage(self.__image_pil)
        except Exception as e:
            print(f'Could notre get resized image from url {self.url}.\nError:{e}')
        return self.__image_tk


class EditableTable(Table):

    def __init__(self, container_frame=None, file=None, **kwargs):
        self.file = file
        self.rows_per_page = 35
        self.current_page = 0
        self.total_pages = 0
        self.data = None
        self.edit_row_window = None
        self.edited_entries = None
        self.edited_row_index = None
        self.edit_cell_window = None

        self.load_data()
        Table.__init__(self, container_frame, dataframe=self.data, **kwargs)
        # self.bind('<Double-Button-1>', self.edit_row)
        self.bind('<Double-Button-1>', self.edit_cell)

    def show_page(self, page):
        start = page * self.rows_per_page
        end = start + self.rows_per_page
        data = self.data.iloc[start:end]
        self.updateModel(TableModel(data))
        self.redraw()
        self.current_page = page

    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.show_page(self.current_page + 1)

    def prev_page(self):
        if self.current_page > 0:
            self.show_page(self.current_page - 1)

    def load_data(self):
        self.data = pd.read_csv(self.file)
        self.total_pages = (len(self.data) - 1) // self.rows_per_page + 1

    def reload_data(self):
        self.load_data()
        self.show_page(self.current_page)

    def save_data(self):
        self.model.df.to_csv(self.file, index=False)

    def edit_row(self):
        row_selected = self.getSelectedRow()
        if row_selected is None:
            return
        width = 900
        height = 980  # 780

        # window is displayed at mouse position
        x = self.master.winfo_rootx()
        y = self.master.winfo_rooty()

        edit_row_window = EditRowWindow(
            self.master,
            title='Edit current row values',
            geometry=f'{width}x{height}+{x}+{y}',
            icon='../UEVaultManager/assets/main.ico',
            editable_table=self
        )
        edit_row_window.grab_set()
        edit_row_window.minsize(width, height)
        # configure the grid
        edit_row_window.row_frame.columnconfigure(0, weight=0)
        edit_row_window.row_frame.columnconfigure(1, weight=1)

        row_data = self.model.df.iloc[row_selected].to_dict()
        entries = {}
        image_url = ''
        for i, (key, value) in enumerate(row_data.items()):
            ttk.Label(edit_row_window.row_frame, text=key).grid(row=i, column=0, sticky=tk.W)
            lower_key = key.lower()
            if lower_key == 'image':
                image_url = value

            if lower_key == 'asset_id':
                # asset_id is readonly
                entry = ttk.Entry(edit_row_window.row_frame)
                entry.insert(0, value)
                entry.grid(row=i, column=1, sticky=tk.EW)
            elif lower_key == 'url':
                # we add a button to open the url in an inner frame
                asset_url = value
                inner_frame_url = tk.Frame(edit_row_window.row_frame)
                inner_frame_url.grid(row=i, column=1, sticky=tk.EW)
                entry = ttk.Entry(inner_frame_url)
                entry.insert(0, value)
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
                button = ttk.Button(inner_frame_url, text="Open URL", command=lambda: webbrowser.open(asset_url))
                button.pack(side=tk.RIGHT)
            elif lower_key in ('description', 'comment'):
                # description and comment fields are text
                entry = tk.Text(edit_row_window.row_frame, height=3)
                entry.insert('1.0', value)
                entry.grid(row=i, column=1, sticky=tk.EW)
            else:
                # other field is just a usual entry
                entry = ttk.Entry(edit_row_window.row_frame)
                entry.insert(0, value)
                entry.grid(row=i, column=1, sticky=tk.EW)

            entries[key] = entry

        # image preview
        image_preview = WebImage(image_url).get_resized(150, 150)
        if image_preview is None:
            # use default image
            current_working_directory = os.path.dirname(os.getcwd())
            image_path = os.path.join(current_working_directory, 'UEVaultManager/assets/UEVM_200x200.png')
            image_path = os.path.normpath(image_path)
            image_preview = tk.PhotoImage(file=image_path)
        edit_row_window.image_preview = image_preview  # keep a reference to the image to avoid garbage collection

        edit_row_window.preview_frame.canvas.create_image(100, 100, anchor="center", image=image_preview)

        self.edited_entries = entries
        self.edited_row_index = row_selected
        self.edit_row_window = edit_row_window

    def save_row(self):
        if self.edited_entries is None or self.edited_row_index is None:
            return

        entries = self.edited_entries
        row_index = self.edited_row_index
        print(f'row_index={row_index}')
        for key, entry in entries.items():
            # print(f'row_index={row_index} key={key} value={value}')
            try:
                # get value for an entry tk widget
                value = entry.get()
            except TypeError:
                # get value for a text tk widget
                value = entry.get('1.0', 'end')
            self.model.df.at[row_index, key] = value

        self.edited_entries = None
        self.edited_row_index = None
        self.redraw()
        self.edit_row_window.close_window()

    def edit_cell(self, event):
        row_clicked = self.get_row_clicked(event)
        col_clicked = self.get_col_clicked(event)
        if row_clicked is None or col_clicked is None:
            return
        col_name = self.model.df.columns[col_clicked]
        cell_value = self.model.df.iat[row_clicked, col_clicked]

        self.edit_cell_window = EditCellWindow(title='Edit current cell value', geometry='300x80', icon='')

        ttk.Label(self.edit_cell_window, text=col_name).grid(row=0, column=0)
        entry = ttk.Entry(self.edit_cell_window)
        entry.insert(0, cell_value)
        entry.grid(row=0, column=1, sticky=tk.W)

    def save_cell(self, row_index, col_index, entry):
        self.model.df.iat[row_index, col_index] = entry.get()
        self.redraw()
        self.edit_cell_window.destroy()


class EditRowWindow(tk.Toplevel):

    def __init__(self, parent, title: str, geometry: str, icon: str, editable_table):
        super().__init__(parent)
        # self = super().Toplevel()

        self.title(title)
        self.geometry(geometry)
        if icon != '':
            self.iconbitmap(icon)

        # the photoimage is stored here to avoid garbage collection
        # see: https://stackoverflow.com/questions/30210618/image-not-getting-displayed-on-tkinter-through-label-widget
        self.image_preview = None

        # windows only (remove the minimize/maximize button)
        # self.attributes('-toolwindow', True)
        self.resizable(True, False)
        # create the data frame
        self.row_frame = self.RowFrame(self, editable_table)
        self.row_frame['padding'] = 5
        # create the preview frame
        self.preview_frame = self.PreviewFrame(self)
        self.preview_frame['padding'] = 5
        # create the button frame
        self.button_frame = self.ButtonFrame(self)
        self.button_frame['padding'] = 5

        self.bind('<Key>', self.on_key_press)

    class RowFrame(ttk.Frame):

        def __init__(self, container, editable_table):
            super().__init__(container)
            self.editable_table = editable_table
            self.pack(ipadx=5, ipady=5, fill=tk.X)

    class PreviewFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__(container)
            self.text = 'Image preview'
            self.pack(fill=tk.X)

            self.canvas = tk.Canvas(self, width=200, height=200, bg='lightgrey')
            self.canvas.pack(anchor=tk.CENTER)
            self.canvas.create_rectangle(24, 24, 176, 176, fill='white')

    class ButtonFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__(container)
            self.button_def_options = {'ipadx': 3, 'ipady': 3, 'fill': tk.X}
            self.pack(ipadx=5, ipady=5, fill=tk.X)

            ttk.Button(self, text='Prev Asset', command=container.prev_asset).pack(**self.button_def_options, side=tk.LEFT)
            ttk.Button(self, text='Next Asset', command=container.next_asset).pack(**self.button_def_options, side=tk.LEFT)
            ttk.Button(self, text='Cancel', command=container.close_window).pack(**self.button_def_options, side=tk.RIGHT)
            ttk.Button(self, text='Save Changes', command=container.save_change).pack(**self.button_def_options, side=tk.RIGHT)

    def close_window(self):
        self.destroy()

    def save_change(self):
        self.row_frame.editable_table.save_row()

    def on_key_press(self, event):
        if event.keysym == 'Escape':
            self.close_window()
        elif event.keysym == 'Return':
            self.save_change()

    def prev_asset(self):
        # TODO
        todo_message()

    def next_asset(self):
        # TODO
        todo_message()


class EditCellWindow(tk.Tk):
    # TODO
    def __init__(self, title: str, geometry: str, icon: str):
        super().__init__()

        self.title(title)
        self.geometry(geometry)
        if icon != '':
            self.iconbitmap(icon)

        # windows only (remove the minimize/maximize button)
        self.attributes('-toolwindow', True)
        self.resizable(True, False)

        ttk.Button(self, text='Save Changes', command=todo_message).pack(ipadx=20, ipady=3, fill=tk.X, side=tk.LEFT)
        ttk.Button(self, text='Cancel', command=todo_message).pack(ipadx=20, ipady=3, fill=tk.X, side=tk.RIGHT)


class AppWindow(tk.Tk):

    def __init__(self, title: str, geometry: str, icon: str, file: str):
        super().__init__()

        self.title(title)
        self.geometry(geometry)
        if icon != '':
            self.iconbitmap(icon)

        self.resizable(True, False)
        # windows only (remove the minimize/maximize button)
        # self.attributes('-toolwindow', True)

        # create the data frame
        self.table_frame = self.TableFrame(self)
        self.table_frame['padding'] = 5

        # create and display the data object
        self.table_frame.editable_table = EditableTable(self.table_frame, file=file)
        self.table_frame.editable_table.show()
        self.table_frame.editable_table.show_page(0)

        # create the button frame
        self.button_frame = self.ButtonFrame(self)

        self.bind('<Key>', self.on_key_press)

    class TableFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__(container)
            self.editable_table = None
            self.pack(ipadx=5, ipady=5, fill=tk.BOTH, expand=True)

    class ButtonFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__(container)

            self.button_def_options = {'ipadx': 3, 'ipady': 3, 'fill': tk.BOTH, 'expand': False}
            self.pack(padx=5, pady=5, ipadx=5, ipady=5, fill=tk.X)
            editable = container.table_frame.editable_table

            ttk.Button(container, text='Prev Page', command=editable.prev_page).pack(**self.button_def_options, side=tk.LEFT)
            ttk.Button(container, text='Next Page', command=editable.next_page).pack(**self.button_def_options, side=tk.LEFT)
            ttk.Button(container, text='Edit Row', command=editable.edit_row).pack(**self.button_def_options, side=tk.LEFT)
            ttk.Button(container, text='Reload Content', command=editable.reload_data).pack(**self.button_def_options, side=tk.LEFT)
            ttk.Button(container, text='Save Changes', command=container.save_changes).pack(**self.button_def_options, side=tk.LEFT)
            ttk.Button(container, text='Load a file', command=container.select_file).pack(**self.button_def_options, side=tk.LEFT)
            ttk.Button(container, text='Quit', command=container.close_window).pack(**self.button_def_options, side=tk.RIGHT)

    def close_window(self):
        self.quit()

    def save_changes(self):
        self.table_frame.editable_table.save_data()

    def on_key_press(self, event):
        if event.keysym == 'Escape':
            self.close_window()
        elif event.keysym == 'Return':
            self.table_frame.editable_table.edit_row()

    def select_file(self):
        filetypes = (('csv file', '*.csv'), ('tcsv file', '*.tcsv'), ('json file', '*.json'), ('text file', '*.txt'))

        filename = fd.askopenfilename(title='Choose a file to open', initialdir='./', filetypes=filetypes)

        showinfo(title=appTitle, message=f'The file {filename} as been read')
        self.table_frame.editable_table.file = filename
        self.table_frame.editable_table.load_data()


if __name__ == '__main__':
    main = AppWindow(title=appTitle, geometry='1200x890', icon='../UEVaultManager/assets/main.ico', file='../results/list.csv')
    main.mainloop()
