"""
working file for the GUI integration in UEVaultManager

Things to be done:
- add pagination info in a new frame. See tk_table_filter_ex.py
- move quit button at right of the toolbar
- check the TODOs
- in edit_row_window, implement the prev and next buttons
- in edit_row_window, implement the zoom_in and zoom_out buttons
- Extract the classes in separate files
- split the code into several files.
- save and load for tcsv files
- save and load for json files
- migrate the code into the UEVaultManager code base
- document the new features
- update the PyPi package

Bugs to confirm:
- save to file only save the current page

Bugs to fix:
- save to file only save the current page

"""
import datetime
import time
import tkinter as tk
import webbrowser
import os
import pandas as pd
import requests
from io import BytesIO
from tkinter import filedialog as fd, messagebox, filedialog, ttk
from tkinter.messagebox import showinfo, showwarning
from urllib.parse import quote_plus
from urllib.request import urlopen
from screeninfo import get_monitors
from pandastable import Table, TableModel
from PIL import ImageTk, Image

debug_mode = False

# settings that can be store in a config file later
#
app_title = 'UEVM Gui'
app_width = 1600
app_height = 920
app_monitor = 1
csv_datetime_format = '%y-%m-%d %H:%M:%S'
app_icon_filename = '../UEVaultManager/assets/main.ico'
csv_filename = '../results/list.csv'

cache_folder = "../cache"
cache_max_time = 60 * 60 * 24 * 15  # 15 days

default_image_filename = '../UEVaultManager/assets/UEVM_200x200.png'
preview_max_width = 150
preview_max_height = 150

default_search_text = 'Search...'
default_category_for_all = 'All'

table_font_size = 10

# global variables
#
edit_cell_window_ref = None
edit_row_window_ref = None

# global functions
#
def todo_message():
    msg = 'Not implemented yet'
    showinfo(title=app_title, message=msg)


def log_info(msg):
    # will be replaced by a logger when integrated in UEVaultManager
    print(msg)


def log_debug(msg):
    if not debug_mode:
        return  # temp bypass
    # will be replaced by a logger when integrated in UEVaultManager
    print(msg)


def log_warning(msg):
    # will be replaced by a logger when integrated in UEVaultManager
    print(msg)


def log_error(msg):
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
def convert_to_datetime(value):
    try:
        return datetime.datetime.strptime(value, csv_datetime_format)
    except ValueError:
        return ''


def resize_and_show_image(image, canvas, new_height, new_width):
    image = image.resize((new_width, new_height), Image.LANCZOS)
    canvas.config(width=new_width, height=new_height, image=None)
    canvas.image = ImageTk.PhotoImage(image)
    canvas.create_image(0, 0, anchor=tk.NW, image=canvas.image)


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
        except Exception as error:
            log_warning(f'image could not be read from url {self.url}.\nError:{error}')

    def get(self):
        return self.__image_tk

    def get_resized(self, new_width, new_height):
        try:
            self.__image_pil.thumbnail((new_width, new_height))
            self.__image_tk = ImageTk.PhotoImage(self.__image_pil)
        except Exception as error:
            log_warning(f'Could notre get resized image from url {self.url}.\nError:{error}')
        return self.__image_tk


class EditableTable(Table):

    def __init__(self, container_frame=None, file=None, fontsize=10, **kwargs):
        self.container_frame = container_frame
        self.file = file

        self.rows_per_page = 35
        self.current_page = 0
        self.total_pages = 0
        self.pagination_enabled = True

        self.data = None
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
        Table.__init__(self, container_frame, dataframe=self.data, showtoolbar=True, showstatusbar=True, **kwargs)
        self.fontsize = fontsize
        self.setFont()

        # self.bind('<Double-Button-1>', self.edit_row)
        self.bind('<Double-Button-1>', self.edit_value)

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

    def load_data(self):
        csv_options = {
            'converters': {
                'Asset_id': str,  #
                'App name': str,  #
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
        log_debug("\nCOL TYPES AFTER LOADING CSV\n")
        log_debug(self.data.info())

        self.total_pages = (len(self.data) - 1) // self.rows_per_page + 1

        for col in self.data.columns:
            try:
                self.data[col] = self.data[col].astype(str)
            except ValueError as error:
                log_error(f'Could not convert column "{col}" to string. Error: {error}')

        col_to_datetime = ['Creation Date', 'Update Date']
        # note "date added" does not use the same format as the other date columns
        for col in col_to_datetime:
            try:
                self.data[col] = pd.to_datetime(self.data[col], format='ISO8601')
            except ValueError as error:
                log_error(f'Could not convert column "{col}" to datetime. Error: {error}')

        col_as_float = ['Review', 'Price', 'Old Price']
        for col in col_as_float:
            try:
                self.data[col] = self.data[col].astype(float)
            except ValueError as error:
                log_error(f'Could not convert column "{col}" to float. Error: {error}')

        col_as_category = ['Category']
        for col in col_as_category:
            try:
                self.data[col] = self.data[col].astype("category")
            except ValueError as error:
                log_error(f'Could not convert column "{col}" to category. Error: {error}')

        log_debug("\nCOL TYPES AFTER MANUAL CONVERSION\n")
        log_debug(self.data.info())

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

    def search(self, category=default_category_for_all, search_text=default_search_text):
        if category and category != default_category_for_all:
            self.data_filtered = self.data[self.data['Category'] == category]
        if search_text and search_text != default_search_text:
            self.data_filtered = self.data_filtered[self.data_filtered.apply(lambda row: search_text.lower() in str(row).lower(), axis=1)]
        self.show_page(0)

    def reset_search(self):
        self.data_filtered = self.data
        self.show_page(0)

    def expand_cols(self):
        todo_message()

    def shrink_cols(self):
        todo_message()

    def get_selected_row_values(self):
        if self.edit_row_entries is None or self.edit_row_index is None:
            return {}
        entries_values = {}
        for key, entry in self.edit_row_entries.items():
            try:
                # get value for an entry tk widget
                value = entry.get()
            except TypeError:
                # get value for a text tk widget
                value = entry.get('1.0', 'end')
            entries_values[key] = value
        return entries_values

    def edit_record(self):
        row_selected = self.getSelectedRow()
        if row_selected is None:
            return

        title = 'Edit current row values'
        width = 900
        height = 980  # 780
        # window is displayed at mouse position
        x = self.master.winfo_rootx()
        y = self.master.winfo_rooty()

        edit_row_window = EditRowWindow(self.master, title=title, geometry=f'{width}x{height}+{x}+{y}', icon=app_icon_filename, editable_table=self)
        edit_row_window.grab_set()
        edit_row_window.minsize(width, height)
        # configure the grid
        edit_row_window.content_frame.columnconfigure(0, weight=0)
        edit_row_window.content_frame.columnconfigure(1, weight=1)

        global edit_row_window_ref
        edit_row_window_ref = edit_row_window

        # get and display the row data
        row_data = self.model.df.iloc[row_selected].to_dict()
        entries = {}
        image_url = ''
        for i, (key, value) in enumerate(row_data.items()):
            ttk.Label(edit_row_window.content_frame, text=key).grid(row=i, column=0, sticky=tk.W)
            lower_key = key.lower()
            if lower_key == 'image':
                image_url = value

            if lower_key == 'asset_id':
                # asset_id is readonly
                entry = ttk.Entry(edit_row_window.content_frame)
                entry.insert(0, value)
                entry.grid(row=i, column=1, sticky=tk.EW)
            elif lower_key == 'url':
                # we add a button to open the url in an inner frame
                asset_url = value
                inner_frame_url = tk.Frame(edit_row_window.content_frame)
                inner_frame_url.grid(row=i, column=1, sticky=tk.EW)
                entry = ttk.Entry(inner_frame_url)
                entry.insert(0, value)
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
                button = ttk.Button(inner_frame_url, text="Open URL", command=lambda: webbrowser.open(asset_url))
                button.pack(side=tk.RIGHT)
            elif lower_key in ('description', 'comment'):
                # description and comment fields are text
                entry = tk.Text(edit_row_window.content_frame, height=3)
                entry.insert('1.0', value)
                entry.grid(row=i, column=1, sticky=tk.EW)
            else:
                # other field is just a usual entry
                entry = ttk.Entry(edit_row_window.content_frame)
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
        edit_row_window.initial_values = self.get_selected_row_values()

    def save_record(self):
        for key, value in self.get_selected_row_values().items():
            self.model.df.at[self.edit_row_index, key] = value
        self.edit_row_entries = None
        self.edit_row_index = None
        self.redraw()
        self.must_save = True
        self.edit_row_window.close_window()

    def get_selected_cell_values(self):
        if self.edit_cell_entry is None:
            return None
        return self.edit_cell_entry.get()

    def edit_value(self, event):
        row_index = self.get_row_clicked(event)
        col_index = self.get_col_clicked(event)
        if row_index is None or col_index is None:
            return None
        cell_value = self.model.df.iat[row_index, col_index]

        title = 'Edit current cell values'
        width = 300
        height = 80
        # window is displayed at mouse position
        x = self.master.winfo_rootx()
        y = self.master.winfo_rooty()

        edit_cell_window = EditCellWindow(self.master, title=title, geometry=f'{width}x{height}+{x}+{y}', icon=app_icon_filename, editable_table=self)
        edit_cell_window.grab_set()
        edit_cell_window.minsize(width, height)
        global edit_cell_window_ref
        edit_cell_window_ref = edit_cell_window

        # get and display the cell data
        col_name = self.model.df.columns[col_index]
        ttk.Label(edit_cell_window.content_frame, text=col_name).pack(side=tk.LEFT)
        entry = ttk.Entry(edit_cell_window.content_frame)
        entry.insert(0, cell_value)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry.focus_set()

        self.edit_cell_entry = entry
        self.edit_cell_row_index = row_index
        self.edit_cell_col_index = col_index
        self.edit_cell_window = edit_cell_window
        edit_cell_window.initial_values = self.get_selected_cell_values()

    def save_value(self):
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

        self.title(title)
        self.geometry(geometry)
        if icon != '':
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
            default_pack_options = {'ipadx': 3, 'ipady': 3, 'fill': tk.X}
            ttk.Button(self, text='Prev Asset', command=container.prev_asset).pack(**default_pack_options, side=tk.LEFT)
            ttk.Button(self, text='Next Asset', command=container.next_asset).pack(**default_pack_options, side=tk.LEFT)
            ttk.Button(self, text='Cancel', command=container.on_close).pack(**default_pack_options, side=tk.RIGHT)
            ttk.Button(self, text='Save Changes', command=container.save_change).pack(**default_pack_options, side=tk.RIGHT)

    class PreviewFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__(container)
            self.text = 'Image preview'
            self['padding'] = 5

            self.canvas = tk.Canvas(self, width=200, height=200, bg='lightgrey')
            self.canvas.pack(anchor=tk.CENTER)
            self.canvas.create_rectangle(24, 24, 176, 176, fill='white')

    def on_close(self, event=None):
        current_values = self.editable_table.get_selected_row_values()
        # current_values is empty is save_button has been pressed because global variables have been cleared in save_changes()
        self.must_save = current_values and self.initial_values != current_values
        if self.must_save:
            if messagebox.askokcancel('Close the window', 'Changes have been made. Do you want to save them ?'):
                self.save_change()
        self.close_window()

    def close_window(self, event=None):
        global edit_row_window_ref
        edit_row_window_ref = None
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

        self.editable_table = editable_table
        self.must_save = False
        self.initial_values = []

        # windows only (remove the minimize/maximize button)
        self.attributes('-toolwindow', True)
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
            self['padding'] = 5

    class ControlFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__(container)
            self['padding'] = 5
            default_pack_options = {'ipadx': 3, 'ipady': 3, 'fill': tk.X}
            ttk.Button(self, text='Cancel', command=container.on_close).pack(**default_pack_options, side=tk.RIGHT)
            ttk.Button(self, text='Save Changes', command=container.save_change).pack(**default_pack_options, side=tk.RIGHT)

    def on_close(self, event=None):
        current_values = self.editable_table.get_selected_cell_values()
        # current_values is empty is save_button has been pressed because global variables have been cleared in save_changes()
        self.must_save = current_values and self.initial_values != current_values
        if self.must_save:
            if messagebox.askokcancel('Close the window', 'Changes have been made. Do you want to save them ?'):
                self.save_change()
        self.close_window()

    def close_window(self, event=None):
        global edit_cell_window_ref
        edit_cell_window_ref = None
        self.destroy()

    def save_change(self):
        self.must_save = False
        self.editable_table.save_value()

    def on_key_press(self, event):
        if event.keysym == 'Escape':
            self.on_close()
        elif event.keysym == 'Return':
            self.save_change()


class AppWindow(tk.Tk):

    def __init__(self, title: str, width: int, height: int, icon: str, file: str, screen_index=0):
        super().__init__()

        self.title(title)

        monitors = get_monitors()
        if screen_index > len(monitors):
            log_warning(f'The screen #{screen_index} is not available. Using 0 as screen index.')
            screen_index = 0

        log_info(f'The app is displayed is the center of the screen #{screen_index}.')

        # Position the window in the center of the screen
        target_screen = monitors[screen_index]
        screen_width = target_screen.width
        screen_height = target_screen.height
        x = target_screen.x + (screen_width-width) // 2
        y = target_screen.y + (screen_height-height) // 2
        geometry: str = f'{width}x{height}+{x}+{y}'
        self.geometry(geometry)

        if icon != '':
            self.iconbitmap(icon)

        self.resizable(True, False)
        self.editable_table = None

        # Create frames
        table_frame = self.TableFrame(self)
        self.editable_table = EditableTable(container_frame=table_frame, file=file, fontsize=table_font_size)

        self.editable_table.show()
        self.editable_table.show_page(0)
        self.table_frame = table_frame
        toolbar_frame = self.ToolbarFrame(self)
        self.toolbar_frame = toolbar_frame
        control_frame = self.ControlFrame(self)
        self.control_frame = control_frame

        # Pack the frames with the appropriate side option
        toolbar_frame.pack(fill=tk.X, side=tk.TOP, anchor=tk.NW, ipadx=5, ipady=5)
        table_frame.pack(fill=tk.BOTH, side=tk.LEFT, anchor=tk.NW, ipadx=5, ipady=5, expand=True)
        control_frame.pack(fill=tk.BOTH, side=tk.RIGHT, anchor=tk.NW, ipadx=5, ipady=5)

        self.bind('<Key>', self.on_key_press)
        # Bind the table to the mouse motion event
        self.editable_table.bind('<Motion>', self.mouse_over_cell)
        # Bind the table to the mouse leave event
        self.editable_table.bind('<Leave>', self.show_default_image)
        self.protocol("WM_DELETE_WINDOW", self.on_close())

    class ToolbarFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__()
            default_pack_options = {'ipadx': 2, 'ipady': 2, 'fill': tk.BOTH, 'expand': False}
            lblf_def_options = {'ipadx': 1, 'ipady': 1, 'padx': 2, 'pady': 1, 'fill': tk.BOTH, 'expand': False}

            lblf_pagination = ttk.LabelFrame(self, text='Pagination')
            lblf_pagination.pack(**lblf_def_options, side=tk.LEFT)
            btn_toggle_pagination = ttk.Button(lblf_pagination, text='Toggle Pagination', command=container.toggle_pagination)
            btn_toggle_pagination.pack(**default_pack_options, side=tk.LEFT)
            btn_first_page = ttk.Button(lblf_pagination, text='First Page', command=container.editable_table.first_page)
            btn_first_page.pack(**default_pack_options, side=tk.LEFT)
            btn_prev_page = ttk.Button(lblf_pagination, text='Prev Page', command=container.editable_table.prev_page)
            btn_prev_page.pack(**default_pack_options, side=tk.LEFT)
            btn_next_page = ttk.Button(lblf_pagination, text='Next Page', command=container.editable_table.next_page)
            btn_next_page.pack(**default_pack_options, side=tk.LEFT)
            btn_last_page = ttk.Button(lblf_pagination, text='Last Page', command=container.editable_table.last_page)
            btn_last_page.pack(**default_pack_options, side=tk.LEFT)
            btn_toggle_controls = ttk.Button(self, text="Hide Controls", command=container.toggle_filter_controls)
            btn_toggle_controls.pack(side=tk.RIGHT)

            # store the buttons that need to be disabled when the pagination is disabled
            self.btn_first_page = btn_first_page
            self.btn_prev_page = btn_prev_page
            self.btn_next_page = btn_next_page
            self.btn_last_page = btn_last_page
            self.btn_toggle_controls = btn_toggle_controls

    class TableFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__(container)

    class ControlFrame(ttk.Frame):
        # delete the temporary text in filter value entry
        def reset_entry_search(self, _event=None):
            self.entry_search.delete(0, 'end')
            self.entry_search.insert(0, default_search_text)

        def del_entry_search(self, _event=None):
            self.entry_search.delete(0, 'end')

        def __init__(self, container):
            super().__init__()

            default_pack_options = {'ipadx': 2, 'ipady': 2, 'fill': tk.BOTH, 'expand': False}
            default_grid_options = {'ipadx': 2, 'ipady': 2, 'sticky': tk.NW}
            lblf_def_options = {'ipadx': 1, 'ipady': 1, 'padx': 2, 'pady': 1, 'fill': tk.BOTH, 'expand': False}

            lblf_display = ttk.LabelFrame(self, text='Display')
            lblf_display.pack(**lblf_def_options)
            btn_zoom_in = ttk.Button(lblf_display, text='Expand Cols', command=container.editable_table.expand_cols)
            btn_zoom_in.pack(**default_pack_options, side=tk.LEFT)
            btn_zoom_out = ttk.Button(lblf_display, text='Shrink Cols', command=container.editable_table.shrink_cols)
            btn_zoom_out.pack(**default_pack_options, side=tk.LEFT)

            lblf_content = ttk.LabelFrame(self, text='Content')
            lblf_content.pack(**lblf_def_options)
            btn_edit_row = ttk.Button(lblf_content, text='Edit Row', command=container.editable_table.edit_record)
            btn_edit_row.pack(**default_pack_options, side=tk.LEFT)
            btn_reload_data = ttk.Button(lblf_content, text='Reload Content', command=container.editable_table.reload_data)
            btn_reload_data.pack(**default_pack_options, side=tk.LEFT)

            # Add controls for searching
            lbf_filter_cat = ttk.LabelFrame(self, text="Search and Filter")
            lbf_filter_cat.pack(fill=tk.X, anchor=tk.NW, ipadx=5, ipady=5)
            categories = list(container.editable_table.data['Category'].cat.categories)
            var_category = tk.StringVar(value=categories[0])
            categories.insert(0, default_category_for_all)
            opt_category = ttk.Combobox(lbf_filter_cat, textvariable=var_category, values=categories)
            opt_category.grid(row=0, column=0, **default_grid_options)
            var_search = tk.StringVar(value=default_search_text)
            entry_search = ttk.Entry(lbf_filter_cat, textvariable=var_search)
            entry_search.grid(row=0, column=1, **default_grid_options)
            entry_search.bind("<FocusIn>", self.del_entry_search)

            btn_filter_by_text = ttk.Button(lbf_filter_cat, text='Search', command=container.search)
            btn_filter_by_text.grid(row=1, column=0, **default_grid_options)
            btn_reset_search = ttk.Button(lbf_filter_cat, text='Reset', command=container.reset_search)
            btn_reset_search.grid(row=1, column=1, **default_grid_options)

            lblf_files = ttk.LabelFrame(self, text='Files')
            lblf_files.pack(**lblf_def_options)
            btn_save_change = ttk.Button(lblf_files, text='Save to File', command=container.save_change)
            btn_save_change.pack(**default_pack_options, side=tk.LEFT)
            btn_export_button = ttk.Button(lblf_files, text='Export Selection', command=container.export_selection)
            btn_export_button.pack(**default_pack_options, side=tk.LEFT)
            btn_select_file = ttk.Button(lblf_files, text='Load a file', command=container.select_file)
            btn_select_file.pack(**default_pack_options, side=tk.LEFT)

            # Create a Canvas to preview the asset image
            lbf_preview = ttk.LabelFrame(self, text="Image Preview")
            lbf_preview.pack(**lblf_def_options, anchor=tk.SW)
            canvas_preview = tk.Canvas(lbf_preview, width=preview_max_width, height=preview_max_height, highlightthickness=0)
            canvas_preview.pack()
            canvas_preview.create_rectangle((0, 0), (preview_max_width, preview_max_height), fill='black')

            lblf_bottom = ttk.Frame(self)
            lblf_bottom.pack(**lblf_def_options)
            ttk.Sizegrip(lblf_bottom).pack(side=tk.RIGHT)
            btn_on_close = ttk.Button(lblf_bottom, text='Quit', command=container.on_close)
            btn_on_close.pack(**default_pack_options, side=tk.RIGHT)

            # store the controls that need to be accessible outside the class
            self.entry_search = entry_search
            self.var_category = var_category
            self.var_search = var_search
            self.canvas_preview = canvas_preview

    def on_close(self):
        if self.editable_table.must_save:
            if messagebox.askokcancel('Exit the application', 'Changes have been made. Do you want to save them in the source file ?'):
                self.save_change()
        self.quit()

    def save_change(self):
        self.editable_table.save_data()

    def on_key_press(self, event):
        global edit_cell_window_ref, edit_row_window_ref
        if event.keysym == 'Escape':
            if edit_cell_window_ref:
                edit_cell_window_ref.destroy()
                edit_cell_window_ref = None
            elif edit_row_window_ref:
                edit_row_window_ref.destroy()
                edit_row_window_ref = None
            else:
                self.on_close()
        elif event.keysym == 'Return':
            self.editable_table.edit_record()

    def select_file(self):
        filetypes = (('csv file', '*.csv'), ('tcsv file', '*.tcsv'), ('json file', '*.json'), ('text file', '*.txt'))

        filename = fd.askopenfilename(title='Choose a file to open', initialdir='./', filetypes=filetypes)

        showinfo(title=app_title, message=f'The file {filename} as been read')
        self.editable_table.file = filename
        self.editable_table.load_data()
        self.editable_table.show_page(0)

    def search(self):
        search_text = self.control_frame.var_search.get()
        category = self.control_frame.var_category.get()
        if search_text == default_search_text and category == default_category_for_all:
            return
        self.toggle_pagination(forced_value=False)
        self.editable_table.search(search_text=search_text, category=category)
        self.control_frame.reset_entry_search()

    def reset_search(self):
        self.control_frame.var_search.set(default_search_text)
        self.control_frame.var_category.set(default_category_for_all)
        self.editable_table.reset_search()

    def toggle_pagination(self, forced_value=None):
        if forced_value is not None:
            self.editable_table.pagination_enabled = forced_value
        else:
            self.editable_table.pagination_enabled = not self.editable_table.pagination_enabled
        self.editable_table.show_page()

        if not self.editable_table.pagination_enabled:
            # Disable prev/next buttons when pagination is disabled
            self.toolbar_frame.btn_first_page.config(state=tk.DISABLED)
            self.toolbar_frame.btn_prev_page.config(state=tk.DISABLED)
            self.toolbar_frame.btn_next_page.config(state=tk.DISABLED)
            self.toolbar_frame.btn_last_page.config(state=tk.DISABLED)
        else:
            # Enable prev/next buttons when pagination is enabled
            self.toolbar_frame.btn_first_page.config(state=tk.NORMAL)
            self.toolbar_frame.btn_prev_page.config(state=tk.NORMAL)
            self.toolbar_frame.btn_next_page.config(state=tk.NORMAL)
            self.toolbar_frame.btn_last_page.config(state=tk.NORMAL)

    def toggle_filter_controls(self):
        # Toggle visibility of filter controls frame
        if self.control_frame.winfo_ismapped():
            self.control_frame.pack_forget()
            self.toolbar_frame.btn_toggle_controls.config(text="Show Control")
        else:
            self.control_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
            self.toolbar_frame.btn_toggle_controls.config(text="Hide Control")

    def export_selection(self):
        # Get selected row indices
        selected_row_indices = self.editable_table.multiplerowlist

        if selected_row_indices:
            # Get selected rows from filtered DataFrame
            selected_rows = self.editable_table.data_filtered.iloc[selected_row_indices]

            # Open file dialog to select file to save exported rows
            file_name = filedialog.asksaveasfilename(
                defaultextension=".csv",
                initialfile="export.csv",
                initialdir=os.path.dirname(self.editable_table.file),
                filetypes=[("CSV files", "*.csv")]
            )

            if file_name:
                # Export selected rows to the specified CSV file
                selected_rows.to_csv(file_name, index=False)
                showinfo(title=app_title, message=f'Selected rows exported to "{file_name}"')
            else:
                showwarning(title=app_title, message='No file has been selected')
        else:
            showwarning(title=app_title, message='Select at least one row first')

    # noinspection DuplicatedCode
    def mouse_over_cell(self, event):
        # Get the row and column index of the cell under the mouse pointer
        row, col = self.editable_table.get_row_clicked(event), self.editable_table.get_col_clicked(event)
        if row is None or col is None:
            return
        # Check if the mouse is over the "img_url" column
        if self.editable_table.model.df.columns[col] == 'Image':
            # Get the image URL
            img_url = self.editable_table.model.getValueAt(row, col)

            # Show the image
            self.show_asset_image(img_url)
        else:
            # Show the default
            self.show_default_image()

    def show_asset_image(self, img_url):
        try:
            # noinspection DuplicatedCode
            if not os.path.isdir(cache_folder):
                os.mkdir(cache_folder)

            image_filename = os.path.join(cache_folder, os.path.basename(img_url))

            # Check if the image is already cached
            if os.path.isfile(image_filename) and (time.time() - os.path.getmtime(image_filename)) < cache_max_time:
                # Load the image from the cache folder
                image = Image.open(image_filename)
            else:
                response = requests.get(img_url)
                image = Image.open(BytesIO(response.content))

                with open(image_filename, "wb") as f:
                    f.write(response.content)

            # Calculate new dimensions while maintaining the aspect ratio
            width_ratio = preview_max_width / float(image.width)
            height_ratio = preview_max_height / float(image.height)
            ratio = min(width_ratio, height_ratio, 1)
            new_width = min(int(image.width * ratio), preview_max_width)
            new_height = min(int(image.height * ratio), preview_max_height)
            log_debug(f'Image size: {image.width}x{image.height} -> {new_width}x{new_height} ratio: {ratio}')
            # noinspection PyTypeChecker
            resize_and_show_image(image, self.control_frame.canvas_preview, new_height, new_width)

        except Exception as error:
            log_error(f"Error showing image: {error}")

    def show_default_image(self, _event=None):
        try:
            # Load the default image
            if os.path.isfile(default_image_filename):
                def_image = Image.open(default_image_filename)
                # noinspection PyTypeChecker
                resize_and_show_image(def_image, self.control_frame.canvas_preview, preview_max_width, preview_max_height)
        except Exception as error:
            log_warning(f"Error showing default image {default_image_filename} cwd:{os.getcwd()}: {error}")


if __name__ == '__main__':
    main = AppWindow(title=app_title, width=app_width, height=app_height, icon=app_icon_filename, file=csv_filename)
    main.mainloop()
