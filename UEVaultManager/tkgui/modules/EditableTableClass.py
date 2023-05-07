import webbrowser
from tkinter import ttk

import pandas as pd
from pandastable import Table, TableModel

from UEVaultManager.tkgui.modules.EditCellWindowClass import EditCellWindow
from UEVaultManager.tkgui.modules.EditRowWindowClass import EditRowWindow
from UEVaultManager.tkgui.modules.functions import *


class EditableTable(Table):

    def __init__(self, container_frame=None, file=None, fontsize=10, **kwargs):
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
            if page < 0:
                page = 0
            elif page >= self.total_pages:
                page = self.total_pages - 1
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
        if self.current_page <= self.total_pages:
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
        if not os.path.isfile(self.file):
            log_error(f'File not found: {self.file}')
            return

        self.data = pd.read_csv(self.file, **csv_options)
        # log_debug("\nCOL TYPES AFTER LOADING CSV\n")
        # self.data.info() # direct print info

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

        # log_debug("\nCOL TYPES AFTER MANUAL CONVERSION\n")
        # self.data.info() # direct print info

        self.data_filtered = self.data

    def reload_data(self):
        self.load_data()
        self.show_page(self.current_page)

    def rebuild_data(self) -> bool:
        # we use a string comparison here to avoid to import of the module to check the real class of UEVM_cli_ref
        if gui_g.UEVM_cli_ref is None or 'UEVaultManagerCLI' not in str(type(gui_g.UEVM_cli_ref)):
            from_cli_only_message()
            return False
        else:
            gui_g.UEVM_cli_ref.list_assets(gui_g.UEVM_cli_args)
            self.load_data()
            self.show_page(self.current_page)
            return True

    def save_data(self):
        data = self.data.iloc[0:len(self.data)]
        self.updateModel(TableModel(data))  # needed to restore all the data and not only the current page
        self.model.df.to_csv(self.file, index=False, na_rep='N/A', date_format=gui_g.s.csv_datetime_format)
        self.show_page(self.current_page)
        self.must_save = False

    def search(self, category=gui_g.s.default_category_for_all, search_text=gui_g.s.default_search_text):
        if category and category != gui_g.s.default_category_for_all:
            self.data_filtered = self.data[self.data['Category'] == category]
        if search_text and search_text != gui_g.s.default_search_text:
            self.data_filtered = self.data_filtered[self.data_filtered.apply(lambda row: search_text.lower() in str(row).lower(), axis=1)]
        self.show_page(0)

    def reset_search(self):
        self.data_filtered = self.data
        self.show_page(0)

    def expand_columns(self):
        self.expandColumns(factor=gui_g.s.expand_columns_factor)

    def contract_columns(self):
        self.contractColumns(factor=gui_g.s.contract_columns_factor)

    def autofit_columns(self):
        self.autoResizeColumns()

    def zoom_in(self):
        self.zoomIn()

    def zoom_out(self):
        self.zoomOut()

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
        height = 900
        # window is displayed at mouse position
        # x = self.master.winfo_rootx()
        # y = self.master.winfo_rooty()
        edit_row_window = EditRowWindow(
            parent=self.master, title=title, width=width, height=height, icon=gui_g.s.app_icon_filename, editable_table=self
        )
        edit_row_window.grab_set()
        edit_row_window.minsize(width, height)
        # configure the grid
        edit_row_window.content_frame.columnconfigure(0, weight=0)
        edit_row_window.content_frame.columnconfigure(1, weight=1)

        self.display_record(row_selected)

    def display_record(self, row_selected=None):
        edit_row_window = gui_g.edit_row_window_ref
        if row_selected is None or edit_row_window is None:
            return
        # get and display the row data
        row_data = self.model.df.iloc[row_selected].to_dict()
        entries = {}
        image_url = ''
        for i, (key, value) in enumerate(row_data.items()):
            from tkinter import ttk
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
                inner_frame_url = tk.Frame(edit_row_window.content_frame)
                inner_frame_url.grid(row=i, column=1, sticky=tk.EW)
                entry = ttk.Entry(inner_frame_url)
                entry.insert(0, value)
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
                button = ttk.Button(inner_frame_url, text="Open URL", command=self.open_asset_url)
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
        show_asset_image(image_url=image_url, canvas_preview=edit_row_window.control_frame.canvas_preview)

        self.edit_row_entries = entries
        self.edit_row_index = row_selected
        self.edit_row_window = edit_row_window
        edit_row_window.initial_values = self.get_selected_row_values()

    def open_asset_url(self, url=None):
        if url is None:
            if self.edit_row_entries is None:
                return
            asset_url = self.edit_row_entries['Url'].get()
        else:
            asset_url = url
        log_info(f'calling open_asset_url={asset_url}')
        if asset_url is None or asset_url == '' or asset_url == 'nan':
            return
        webbrowser.open(asset_url)

    def save_record(self):
        for key, value in self.get_selected_row_values().items():
            self.model.df.at[self.edit_row_index, key] = value
        self.edit_row_entries = None
        self.edit_row_index = None
        self.redraw()
        self.must_save = True
        self.edit_row_window.close_window()

    def move_to_next_record(self):
        row_selected = self.getSelectedRow()
        if row_selected is None or row_selected == self.model.df.shape[0] - 1:
            return
        self.setSelectedRow(row_selected + 1)
        self.redraw()
        self.display_record(row_selected + 1)

    def move_to_prev_record(self):
        row_selected = self.getSelectedRow()
        if row_selected is None or row_selected == 0:
            return
        self.setSelectedRow(row_selected - 1)
        self.redraw()
        self.display_record(row_selected - 1)

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
        # x = self.master.winfo_rootx()
        # y = self.master.winfo_rooty()
        edit_cell_window = EditCellWindow(parent=self.master, title=title, width=width, height=height, editable_table=self)
        edit_cell_window.grab_set()
        edit_cell_window.minsize(width, height)

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
