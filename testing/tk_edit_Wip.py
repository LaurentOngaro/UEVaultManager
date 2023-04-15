"""
working file for the GUI integration in UEVaultManager

Things to be done:
- add columns filtering to the table. See tk_table_pagination_toggle_ex.py
- add pagination info in a new frame. See tk_table_filter_ex.py
- check the TODOs
- in edit_row_window, implement the prev and next buttons
- save and load for tcsv files
- save and load for json files
- split the code into several files.
- Extract the classes in separate files
- migrate the code into the UEVaultManager code base
- document the new features
- update the PyPi package

Bugs to confirm:
- save to file only save the current page

Bugs to fix:
- save to file only save the current page

"""
import datetime
import tkinter as tk
import webbrowser
import os
from io import BytesIO
from tkinter import filedialog as fd, messagebox, filedialog
from tkinter import ttk
from tkinter.messagebox import showinfo, showwarning
from urllib.parse import quote_plus
from urllib.request import urlopen

import pandas as pd
from pandastable import Table, TableModel
from PIL import ImageTk, Image

appTitle = 'UEVM Gui'
csv_datetime_format = '%y-%m-%d %H:%M:%S'


def todo_message():
    msg = 'Not implemented yet'
    showinfo(title=appTitle, message=msg)


def log(msg):
    # will be replaced by a logger when integrated in UEVaultManager
    print(msg)


def convert_to_bool(x):
    try:
        if str(x).lower() in ('1', '1.0', 'true', 'yes', 'y', 't'):
            return True
        else:
            return False
    except ValueError:
        return False


# convert x to a datetime using the format in csv_datetime_format
def convert_to_datetime(x):
    try:
        return datetime.datetime.strptime(x, csv_datetime_format)
    except ValueError:
        return ''


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
            log(f'image could not be read from url {self.url}.\nError:{e}')

    def get(self):
        return self.__image_tk

    def get_resized(self, new_width, new_height):
        try:
            self.__image_pil.thumbnail((new_width, new_height))
            self.__image_tk = ImageTk.PhotoImage(self.__image_pil)
        except Exception as e:
            log(f'Could notre get resized image from url {self.url}.\nError:{e}')
        return self.__image_tk


class EditableTable(Table):

    def __init__(self, container_frame=None, file=None, **kwargs):
        self.container_frame = container_frame
        self.file = file

        self.rows_per_page = 32
        self.current_page = 0
        self.total_pages = 0
        self.pagination_enabled = True

        self.data = None
        # Initialize filtered DataFrame
        self.data_filtered = None

        self.must_save = False
        self.edit_row_window = None
        self.edit_row_entries = None
        self.edit_row_index = None

        self.edit_cell_window = None
        self.edit_cell_row_index = None
        self.edit_cell_col_index = None
        self.edit_cell_entry = None

        self.load_data()
        Table.__init__(self, container_frame, dataframe=self.data, **kwargs, showtoolbar=True, showstatusbar=True)
        # self.bind('<Double-Button-1>', self.edit_row)
        self.bind('<Double-Button-1>', self.edit_cell)

    def show_page(self, page=None):
        if page is None:
            page = self.current_page
        if self.pagination_enabled:
            # Calculate start and end rows for current page
            self.current_page = page
            start = page * self.rows_per_page
            end = start + self.rows_per_page
            # Update table with data for current page
            self.model.df = self.data.iloc[start:end]
        else:
            # Update table with all data
            self.model.df = self.data_filtered
            self.current_page = 0
        # self.updateModel(TableModel(data))
        self.redraw()

    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.show_page(self.current_page + 1)

    def prev_page(self):
        if self.current_page > 0:
            self.show_page(self.current_page - 1)

    def first_page(self):
        self.show_page(0)

    def last_page(self):
        self.show_page(self.total_pages - 1)

    def toggle_pagination(self):
        # Toggle pagination on/off and update table
        self.pagination_enabled = not self.pagination_enabled
        # Update table with data for current page or all data if pagination is disabled
        self.show_page()

    def load_data(self):
        csv_options = {
            'dtype': {
                'Asset_id': str,  #
                'App name': str,  #
            },
            'converters': {
                'Review': float,  #
                'Price': float,  #
                'Old Price': float,  #
                'On Sale': convert_to_bool,  #
                'Purchased': convert_to_bool,  #
                'Must Buy': convert_to_bool,  #
                'Date Added': convert_to_datetime,  #
            },
            'on_bad_lines': 'warn',
            'encoding': "utf-8",
        }
        self.data = pd.read_csv(self.file, **csv_options)
        self.total_pages = (len(self.data) - 1) // self.rows_per_page + 1

        # note "date added" does not use the same format as the other date columns
        date_to_convert = ['Creation Date', 'Update Date']
        for col in date_to_convert:
            try:
                self.data[col] = pd.to_datetime(self.data[col], format='ISO8601')
            except ValueError as error:
                log(f'Could not convert column "{col}" to datetime. Error: {error}')

        self.data_filtered = self.data

    def reload_data(self):
        self.load_data()
        self.show_page(self.current_page)

    def save_data(self):
        data = self.data.iloc[0:-1]
        self.updateModel(TableModel(data))  # needed to ,restore all the data and not only the current page
        self.model.df.to_csv(self.file, index=False, na_rep='N/A', date_format=csv_datetime_format)
        self.show_page(self.current_page)
        self.must_save = False

    def zoom_in(self):
        todo_message()

    def zoom_out(self):
        todo_message()

    def edit_row(self):
        row_selected = self.getSelectedRow()
        if row_selected is None:
            return

        title = 'Edit current row values'
        width = 900
        height = 980  # 780
        # window is displayed at mouse position
        x = self.master.winfo_rootx()
        y = self.master.winfo_rooty()

        edit_row_window = EditRowWindow(
            self.master, title=title, geometry=f'{width}x{height}+{x}+{y}', icon='../UEVaultManager/assets/main.ico', editable_table=self
        )
        edit_row_window.grab_set()
        edit_row_window.minsize(width, height)
        # configure the grid
        edit_row_window.row_frame.columnconfigure(0, weight=0)
        edit_row_window.row_frame.columnconfigure(1, weight=1)

        # get and display the row data
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

        self.edit_row_entries = entries
        self.edit_row_index = row_selected
        self.edit_row_window = edit_row_window

    def save_row(self):
        if self.edit_row_entries is None or self.edit_row_index is None:
            return

        for key, entry in self.edit_row_entries.items():
            try:
                # get value for an entry tk widget
                value = entry.get()
            except TypeError:
                # get value for a text tk widget
                value = entry.get('1.0', 'end')
            self.model.df.at[self.edit_row_index, key] = value

        self.edit_row_entries = None
        self.edit_row_index = None
        self.redraw()
        self.must_save = True
        self.edit_row_window.close_window()

    def edit_cell(self, event):
        row_index = self.get_row_clicked(event)
        col_index = self.get_col_clicked(event)
        if row_index is None or col_index is None:
            return

        title = 'Edit current cell values'
        width = 300
        height = 80
        # window is displayed at mouse position
        x = self.master.winfo_rootx()
        y = self.master.winfo_rooty()

        edit_cell_window = EditCellWindow(
            self.master, title=title, geometry=f'{width}x{height}+{x}+{y}', icon='../UEVaultManager/assets/main.ico', editable_table=self
        )
        edit_cell_window.grab_set()
        edit_cell_window.minsize(width, height)

        # get and display the cell data
        col_name = self.model.df.columns[col_index]
        cell_value = self.model.df.iat[row_index, col_index]
        ttk.Label(edit_cell_window.row_frame, text=col_name).pack(side=tk.LEFT)
        entry = ttk.Entry(edit_cell_window.row_frame)
        entry.insert(0, cell_value)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.edit_cell_entry = entry
        self.edit_cell_row_index = row_index
        self.edit_cell_col_index = col_index
        self.edit_cell_window = edit_cell_window

    def save_cell(self):
        if self.edit_cell_row_index is None or self.edit_cell_col_index is None or self.edit_cell_entry is None:
            return

        try:
            # get value for an entry tk widget
            value = self.edit_cell_entry.get()
        except TypeError:
            # get value for a text tk widget
            value = self.edit_cell_entry.get('1.0', 'end')
        self.model.df.iat[self.edit_cell_row_index, self.edit_cell_col_index] = value

        self.edit_cell_entry = None
        self.edit_cell_row_index = None
        self.edit_cell_col_index = None
        self.redraw()
        self.must_save = True
        self.edit_cell_window.close_window()


class EditRowWindow(tk.Toplevel):

    def __init__(self, parent, title: str, geometry: str, icon: str, editable_table):
        super().__init__(parent)
        # self = super().Toplevel()

        self.title(title)
        self.geometry(geometry)
        if icon != '':
            self.iconbitmap(icon)

        # the photoimage is stored is the variable to avoid garbage collection
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
            button_def_options = {'ipadx': 3, 'ipady': 3, 'fill': tk.X}
            self.pack(ipadx=5, ipady=5, fill=tk.X)

            ttk.Button(self, text='Prev Asset', command=container.prev_asset).pack(**button_def_options, side=tk.LEFT)
            ttk.Button(self, text='Next Asset', command=container.next_asset).pack(**button_def_options, side=tk.LEFT)
            ttk.Button(self, text='Cancel', command=container.close_window).pack(**button_def_options, side=tk.RIGHT)
            ttk.Button(self, text='Save Changes', command=container.save_change).pack(**button_def_options, side=tk.RIGHT)

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


class EditCellWindow(tk.Toplevel):

    def __init__(self, parent, title: str, geometry: str, icon: str, editable_table):
        super().__init__(parent)

        self.title(title)
        self.geometry(geometry)
        if icon != '':
            self.iconbitmap(icon)

        # windows only (remove the minimize/maximize button)
        self.attributes('-toolwindow', True)
        self.resizable(True, False)

        # create the data frame
        self.row_frame = self.RowFrame(self, editable_table)
        self.row_frame['padding'] = 5

        # create the button frame
        self.button_frame = self.ButtonFrame(self)
        self.button_frame['padding'] = 5

    class RowFrame(ttk.Frame):

        def __init__(self, container, editable_table):
            super().__init__(container)
            self.editable_table = editable_table
            self.pack(ipadx=5, ipady=5, fill=tk.X)

    class ButtonFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__(container)
            button_def_options = {'ipadx': 3, 'ipady': 3, 'fill': tk.X}
            self.pack(ipadx=5, ipady=5, fill=tk.X)
            ttk.Button(self, text='Cancel', command=container.close_window).pack(**button_def_options, side=tk.RIGHT)
            ttk.Button(self, text='Save Changes', command=container.save_change).pack(**button_def_options, side=tk.RIGHT)

    def close_window(self):
        self.destroy()

    def save_change(self):
        self.row_frame.editable_table.save_cell()

    def on_key_press(self, event):
        if event.keysym == 'Escape':
            self.close_window()
        elif event.keysym == 'Return':
            self.save_change()


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
        self.protocol("WM_DELETE_WINDOW", self.on_close())

    class TableFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__(container)
            self.editable_table = None
            self.pack(ipadx=5, ipady=5, fill=tk.BOTH, expand=True)

    class ButtonFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__(container)

            button_def_options = {'ipadx': 3, 'ipady': 3, 'fill': tk.BOTH, 'expand': False}
            self.pack(padx=5, pady=5, ipadx=5, ipady=5, fill=tk.X)
            editable = container.table_frame.editable_table

            btn_zoom_in = ttk.Button(container, text='Zoom In', command=editable.zoom_in)
            btn_zoom_in.pack(**button_def_options, side=tk.LEFT)
            btn_zoom_out = ttk.Button(container, text='Zoom Out', command=editable.zoom_out)
            btn_zoom_out.pack(**button_def_options, side=tk.LEFT)
            btn_toggle_pagination = ttk.Button(container, text='Toggle Pagination', command=container.toggle_pagination)
            btn_toggle_pagination.pack(**button_def_options, side=tk.LEFT)
            btn_first_page = ttk.Button(container, text='First Page', command=editable.first_page)
            btn_first_page.pack(**button_def_options, side=tk.LEFT)
            btn_prev_page = ttk.Button(container, text='Prev Page', command=editable.prev_page)
            btn_prev_page.pack(**button_def_options, side=tk.LEFT)
            btn_next_page = ttk.Button(container, text='Next Page', command=editable.next_page)
            btn_next_page.pack(**button_def_options, side=tk.LEFT)
            btn_last_page = ttk.Button(container, text='Last Page', command=editable.last_page)
            btn_last_page.pack(**button_def_options, side=tk.LEFT)
            btn_edit_row = ttk.Button(container, text='Edit Row', command=editable.edit_row)
            btn_edit_row.pack(**button_def_options, side=tk.LEFT)
            btn_reload_data = ttk.Button(container, text='Reload Content', command=editable.reload_data)
            btn_reload_data.pack(**button_def_options, side=tk.LEFT)
            btn_save_changes = ttk.Button(container, text='Save to File', command=container.save_changes)
            btn_save_changes.pack(**button_def_options, side=tk.LEFT)
            btn_export_button = tk.Button(container, text='Export Selection', command=container.export_selection)
            btn_export_button.pack(side=tk.LEFT)
            btn_select_file = ttk.Button(container, text='Load a file', command=container.select_file)
            btn_select_file.pack(**button_def_options, side=tk.LEFT)
            # add a sizegrip
            ttk.Sizegrip(container).pack(side=tk.RIGHT)
            btn_on_close = ttk.Button(container, text='Quit', command=container.on_close)
            btn_on_close.pack(**button_def_options, side=tk.RIGHT)

            # store the buttons that need to be disabled when the pagination is disabled
            self.btn_first_page = btn_first_page
            self.btn_prev_page = btn_prev_page
            self.btn_next_page = btn_next_page
            self.btn_last_page = btn_last_page

    def on_close(self):
        if self.table_frame.editable_table.must_save:
            if messagebox.askokcancel(
                "Quitter l'application", "Des modifications on été effectuées. Voulez-vous les enregistrer dans le fichier source ?"
            ):
                self.save_changes()
        self.quit()

    def save_changes(self):
        self.table_frame.editable_table.save_data()

    def on_key_press(self, event):
        if event.keysym == 'Escape':
            self.on_close()
        elif event.keysym == 'Return':
            self.table_frame.editable_table.edit_row()

    def select_file(self):
        filetypes = (('csv file', '*.csv'), ('tcsv file', '*.tcsv'), ('json file', '*.json'), ('text file', '*.txt'))

        filename = fd.askopenfilename(title='Choose a file to open', initialdir='./', filetypes=filetypes)

        showinfo(title=appTitle, message=f'The file {filename} as been read')
        self.table_frame.editable_table.file = filename
        self.table_frame.editable_table.load_data()
        self.table_frame.editable_table.show_page(0)

    def toggle_pagination(self):
        self.table_frame.editable_table.toggle_pagination()
        if not self.table_frame.editable_table.pagination_enabled:
            # Disable prev/next buttons when pagination is disabled
            self.button_frame.btn_first_page.config(state=tk.DISABLED)
            self.button_frame.btn_prev_page.config(state=tk.DISABLED)
            self.button_frame.btn_next_page.config(state=tk.DISABLED)
            self.button_frame.btn_last_page.config(state=tk.DISABLED)
        else:
            # Enable prev/next buttons when pagination is enabled
            self.button_frame.btn_first_page.config(state=tk.NORMAL)
            self.button_frame.btn_prev_page.config(state=tk.NORMAL)
            self.button_frame.btn_next_page.config(state=tk.NORMAL)
            self.button_frame.btn_last_page.config(state=tk.NORMAL)

    def export_selection(self):
        # Get selected row indices
        selected_row_indices = self.table_frame.editable_table.multiplerowlist

        if selected_row_indices:
            # Get selected rows from filtered DataFrame
            selected_rows = self.table_frame.editable_table.data_filtered.iloc[selected_row_indices]

            # Open file dialog to select file to save exported rows
            file_name = filedialog.asksaveasfilename(
                defaultextension=".csv",
                initialfile="export.csv",
                initialdir=os.path.dirname(self.table_frame.editable_table.file),
                filetypes=[("CSV files", "*.csv")]
            )

            if file_name:
                # Export selected rows to the specified CSV file
                selected_rows.to_csv(file_name, index=False)
                showinfo(title=appTitle, message=f'Selected rows exported to "{file_name}"')
            else:
                showwarning(title=appTitle, message='No file has been selected')
        else:
            showwarning(title=appTitle, message='Select at least one row first')


if __name__ == '__main__':
    main = AppWindow(title=appTitle, geometry='1200x890', icon='../UEVaultManager/assets/main.ico', file='../results/list.csv')
    main.mainloop()
