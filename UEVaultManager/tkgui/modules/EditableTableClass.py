import webbrowser
from tkinter import ttk

import pandas as pd
from pandastable import Table, TableModel

from UEVaultManager.tkgui.modules.EditCellWindowClass import EditCellWindow
from UEVaultManager.tkgui.modules.EditRowWindowClass import EditRowWindow
from UEVaultManager.tkgui.modules.ExtendedWidgetClasses import ExtendedText
from UEVaultManager.tkgui.modules.functions import *
from UEVaultManager.tkgui.modules.TaggedLabelFrameClass import TaggedLabelFrame


class EditableTable(Table):
    """
    EditableTable is a custom class that extends the pandastable.Table class, providing additional functionality
    such as loading data from CSV files, searching, filtering, pagination, and editing cell values.
    :param container_frame: The parent frame for the table.
    :param file: The path to the CSV file containing the table data.
    :param fontsize: The font size for the table.
    :param show_toolbar: Whether to show the toolbar.
    :param show_statusbar: Whether to show the status bar.
    :param kwargs: Additional arguments to pass to the pandastable.Table class.
    """

    def __init__(self, container_frame=None, file=None, fontsize=10, show_toolbar=False, show_statusbar=False, **kwargs):
        self._last_selected_row = -1
        self._last_selected_col = -1

        self.file = file
        self.must_save = False

        self.pagination_enabled = True
        self.rows_per_page = 35
        self.current_page = 0
        self.total_pages = 0

        self.data = None
        self.data_filtered = None

        self.edit_row_window = None
        self.edit_row_entries = None
        self.edit_row_index = None

        self.edit_cell_window = None
        self.edit_cell_row_index = None
        self.edit_cell_col_index = None
        self.edit_cell_entry = None

        self.load_data()
        Table.__init__(self, container_frame, dataframe=self.data, showtoolbar=show_toolbar, showstatusbar=show_statusbar, **kwargs)
        self.fontsize = fontsize
        self.setFont()

        self.bind('<Double-Button-1>', self.create_edit_cell_window)

    def _generate_cell_selection_changed_event(self) -> None:
        """
        Creates the event bindings for the table.
        """
        selected_row = self.currentrow
        selected_col = self.currentcol

        if (selected_row != self._last_selected_row) or (selected_col != self._last_selected_col):
            self._last_selected_row = selected_row
            self._last_selected_col = selected_col
            self.event_generate('<<CellSelectionChanged>>')

    def handle_left_click(self, event) -> None:
        """
        Handles left-click events on the table.
        :param event: The event that triggered the function call.
        """
        super().handle_left_click(event)
        self._generate_cell_selection_changed_event()

    def handle_right_click(self, event) -> None:
        """
        Handles right-click events on the table.
        :param event: The event that triggered the function call.
        """
        super().handle_right_click(event)
        self._generate_cell_selection_changed_event()

    def show_page(self, page=None) -> None:
        """
        Displays the specified page of the table data.
        :param page: The page number to display (zero-based index).
        """
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
            try:
                # Update table with data for current page
                self.model.df = self.data.iloc[start:end]
            except AttributeError:
                self.redraw()
                return
        else:
            # Update table with all data
            self.model.df = self.data_filtered
            self.current_page = 0
        # self.updateModel(TableModel(data))
        self.redraw()

    def next_page(self) -> None:
        """
        Navigates to the next page of the table data.
        """
        if self.current_page <= self.total_pages:
            self.show_page(self.current_page + 1)

    def prev_page(self) -> None:
        """
        Navigates to the previous page of the table data.
        """
        if self.current_page > 0:
            self.show_page(self.current_page - 1)

    def first_page(self) -> None:
        """
        Navigates to the first page of the table data.
        """
        self.show_page(0)

    def last_page(self) -> None:
        """
        Navigates to the last page of the table data.
        """
        self.show_page(self.total_pages - 1)

    def load_data(self) -> None:
        """
        Loads data from the specified CSV file into the table.
        """
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
            log_warning(f'File not found: {self.file}')
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

    def reload_data(self) -> None:
        """
        Reloads data from the CSV file and refreshes the table display.
        """
        self.load_data()
        self.show_page(self.current_page)

    def rebuild_data(self) -> bool:
        """
         Rebuilds the data in the table based on the current filtering and sorting options.
         :return: True if the data was successfully rebuilt, False otherwise.
         """

        # we use a string comparison here to avoid to import of the module to check the real class of UEVM_cli_ref
        if gui_g.UEVM_cli_ref is None or 'UEVaultManagerCLI' not in str(type(gui_g.UEVM_cli_ref)):
            from_cli_only_message()
            return False
        else:
            gui_g.UEVM_cli_ref.list_assets(gui_g.UEVM_cli_args)
            self.load_data()
            self.show_page(self.current_page)
            return True

    def save_data(self) -> None:
        """
        Saves the current table data to the CSV file.
        """

        data = self.data.iloc[0:len(self.data)]
        self.updateModel(TableModel(data))  # needed to restore all the data and not only the current page
        self.model.df.to_csv(self.file, index=False, na_rep='N/A', date_format=gui_g.s.csv_datetime_format)
        self.show_page(self.current_page)
        self.must_save = False

    def search(self, filter_dict=None, global_search=None) -> None:
        """
        Searches the table data based on the provided filter dictionary.
        :param filter_dict: A dictionary containing the column names as keys and filter values as the values.
        :param global_search: The text to search for in the table data.
        """
        if filter_dict is None:
            filter_dict = {}
        log_info(f'Filtering data with: {filter_dict} and global search: {global_search}')
        self.data_filtered = self.data

        for key, value in filter_dict.items():
            if key == 'Category' and value == gui_g.s.default_category_for_all:
                continue
            # if isinstance(value, str) and value != '':
            #     self.data_filtered = self.data_filtered[self.data_filtered[key].apply(lambda x: str(value).lower() in str(x).lower())]
            # elif isinstance(value, bool) and value:
            #     self.data_filtered = self.data_filtered[self.data_filtered[key]]
            # elif isinstance(value, bool) and not value:
            #     self.data_filtered = self.data_filtered[not self.data_filtered[key]]
            # else:
            #     self.data_filtered = self.data_filtered[self.data_filtered[key].apply(lambda x: value == x)]
            self.data_filtered = self.data_filtered[self.data_filtered[key].apply(lambda x: str(value).lower() in str(x).lower())]

        if global_search and global_search != gui_g.s.default_global_search:
            self.data_filtered = self.data_filtered[self.data_filtered.apply(lambda row: global_search.lower() in str(row).lower(), axis=1)]
        self.show_page(0)

    def reset_search(self) -> None:
        """
        Resets the table data filtering and sorting, displaying all rows.
        """
        self.data_filtered = self.data
        self.show_page(0)

    def expand_columns(self) -> None:
        """
        Expands the width of all columns in the table.
        """
        self.expandColumns(factor=gui_g.s.expand_columns_factor)

    def contract_columns(self) -> None:
        """
        Contracts the width of all columns in the table.
        """
        self.contractColumns(factor=gui_g.s.contract_columns_factor)

    def autofit_columns(self) -> None:
        """
        Automatically resizes the columns to fit their content.
        """
        self.autoResizeColumns()

    def zoom_in(self) -> None:
        """
        Increases the font size of the table.
        """
        self.zoomIn()

    def zoom_out(self) -> None:
        """
        Decreases the font size of the table.
        """
        self.zoomOut()

    def get_selected_row_values(self) -> dict:
        """
        Returns the values of the selected row in the table.
        :return: A dictionary containing the column names and their corresponding values for the selected row.
        """
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

    def create_edit_record_window(self) -> None:
        """
        Creates the edit row window for the selected row in the table.
        """
        row_selected = self.getSelectedRow()
        if row_selected is None:
            return

        title = 'Edit current row values'
        width = 900
        height = 980
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

        self.edit_record(row_selected)

    def edit_record(self, row_selected: int = None) -> None:
        """
        Edits the values of the specified row in the table.
        :param row_selected: The index of the row to edit.
        """
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
                entry = ExtendedText(edit_row_window.content_frame, height=3)
                entry.insert('1.0', value)
                entry.grid(row=i, column=1, sticky=tk.EW)
            else:
                # other field is just a usual entry
                entry = ttk.Entry(edit_row_window.content_frame)
                entry.insert(0, value)
                entry.grid(row=i, column=1, sticky=tk.EW)

            entries[key] = entry

        # image preview
        show_asset_image(image_url=image_url, canvas_image=edit_row_window.control_frame.canvas_image)

        self.edit_row_entries = entries
        self.edit_row_index = row_selected
        self.edit_row_window = edit_row_window
        edit_row_window.initial_values = self.get_selected_row_values()

    def save_edit_row_record(self) -> None:
        """
        Saves the edited row values to the table data.
        """
        for key, value in self.get_selected_row_values().items():
            self.model.df.at[self.edit_row_index, key] = value
        self.edit_row_entries = None
        self.edit_row_index = None
        self.redraw()
        self.must_save = True
        self.edit_row_window.close_window()

    def move_to_prev_record(self) -> None:
        """
        Navigates to the previous row in the table and opens the edit row window.
        """
        row_selected = self.getSelectedRow()
        if row_selected is None or row_selected == 0:
            return
        self.setSelectedRow(row_selected - 1)
        self.redraw()
        self._generate_cell_selection_changed_event()
        self.edit_record(row_selected - 1)

    def move_to_next_record(self) -> None:
        """
        Navigates to the next row in the table and opens the edit row window.
        """
        row_selected = self.getSelectedRow()
        if row_selected is None or row_selected == self.model.df.shape[0] - 1:
            return
        self.setSelectedRow(row_selected + 1)
        self.redraw()
        self._generate_cell_selection_changed_event()
        self.edit_record(row_selected + 1)

    def create_edit_cell_window(self, event) -> None:
        """
        Creates the edit cell window for the selected cell in the table.
        :param event: The event that triggered the creation of the edit cell window.
        """
        row_index = self.get_row_clicked(event)
        col_index = self.get_col_clicked(event)
        if row_index is None or col_index is None:
            return None
        cell_value = self.model.df.iat[row_index, col_index]

        title = 'Edit current cell values'
        width = 300
        height = 90
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
        edit_cell_window.initial_values = self.get_edit_cell_values()

    def get_edit_cell_values(self) -> str:
        """
        Returns the values of the selected cell in the table.
        :return: The value of the selected cell.
        """
        if self.edit_cell_entry is None:
            return ''
        return self.edit_cell_entry.get()

    def save_edit_cell_value(self) -> None:
        """
        Saves the edited cell value to the table data.
        """
        widget = self.edit_cell_entry
        if widget is None or self.edit_cell_row_index is None or self.edit_cell_col_index is None or self.edit_cell_entry is None:
            return
        # widget_class = widget.winfo_class().lower()
        entry = self.edit_cell_entry
        try:
            try:
                # get value for an entry tk widget
                value = entry.get()
            except TypeError:
                # get value for a text tk widget
                value = entry.get('1.0', 'end')
            self.model.df.iat[self.edit_cell_row_index, self.edit_cell_col_index] = value
            self.must_save = True
            self.edit_cell_entry = None
            self.edit_cell_row_index = None
            self.edit_cell_col_index = None
        except TypeError:
            log_warning(f'Failed to get content of {widget}')
        self.redraw()
        self.edit_cell_window.close_window()

    def quit_edit_content(self, quick_edit_frame: TaggedLabelFrame = None, row: int = None) -> None:
        """
        Quick edit the content some cells of the selected row.
        :param quick_edit_frame: The frame to display the cell content preview in.
        :param row: The row index of the selected cell.
        """
        if row is None or row >= len(self.model.df) or quick_edit_frame is None:
            return
        # url
        col = self.model.df.columns.get_loc('Url')
        value = self.model.getValueAt(row, col)
        quick_edit_frame.set_child_values(tag='url', content=value, row=row, col=col)
        # stars
        col = self.model.df.columns.get_loc('Stars')
        value = self.model.getValueAt(row, col)
        quick_edit_frame.set_child_values(tag='stars', content=value, row=row, col=col)
        # comment
        col = self.model.df.columns.get_loc('Comment')
        value = self.model.getValueAt(row, col)
        quick_edit_frame.set_child_values(tag='comment', content=value, row=row, col=col)
        # test_result
        col = self.model.df.columns.get_loc('Test result')
        value = self.model.getValueAt(row, col)
        quick_edit_frame.set_child_values(tag='test_result', content=value, row=row, col=col)
        # alternative
        col = self.model.df.columns.get_loc('Alternative')
        value = self.model.getValueAt(row, col)
        quick_edit_frame.set_child_values(tag='alternative', content=value, row=row, col=col)
        # Installed folder
        col = self.model.df.columns.get_loc('Installed Folder')
        value = self.model.getValueAt(row, col)
        quick_edit_frame.set_child_values(tag='folder', content=value, row=row, col=col)

    @staticmethod
    def quick_edit(quick_edit_frame: TaggedLabelFrame = None) -> None:
        """
        Resets the cell content preview.
        :param quick_edit_frame: The frame to reset the cell content preview in.
        """
        quick_edit_frame.set_default_content('asset_url')
        quick_edit_frame.set_default_content('asset_comment')
        quick_edit_frame.set_default_content('asset_test_result')
        quick_edit_frame.set_default_content('asset_alternative')
        quick_edit_frame.set_default_content('asset_folder')

    def quick_edit_save_value(self, value: str, row: int = None, col: int = None) -> None:
        """
        Saves the cell content preview.
        :param value: The value to save.
        :param row: The row index of the cell.
        :param col: The column index of the cell.
        """
        if row is None or row >= len(self.model.df) or col is None:
            return
        try:
            self.model.df.iat[row, col] = value
            self.redraw()
            self.must_save = True
            log_info(f'Save preview value {value} at row={row} col={col}')
        except IndexError:
            log_warning(f'Failed to save preview value {value} at row={row} col={col}')

    def get_image_url(self, row: int = None) -> str:
        """
        Returns the image URL of the selected row.
        :param row: The row index of the selected cell.
        :return: The image URL of the selected row.
        """
        if row is None:
            return ''
        try:
            return self.model.getValueAt(row, col=self.model.df.columns.get_loc('Image'))
        except IndexError:
            return ''

    def open_asset_url(self, url: str = None):
        """
        Opens the asset URL in a web browser.
        :param url: The URL to open.
        """
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

    def reset_style(self) -> None:
        """
        Resets the table style. Usefull when style of the main ttk window has changed.
        """
        self.data.style.clear()
        self.redraw()
