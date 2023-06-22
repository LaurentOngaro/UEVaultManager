# coding=utf-8
"""
Implementation for:
- EditableTable: a class that extends the pandastable.Table class, providing additional functionalities
"""
import io
import webbrowser
from enum import Enum
from tkinter import ttk

import pandas as pd
from pandas.errors import EmptyDataError
from pandastable import Table, TableModel, config

from UEVaultManager.models.csv_data import create_empty_csv_row, get_csv_field_name_list, convert_csv_row_to_sql_row, is_on_state, FieldState, \
    FieldType, is_from_type, get_typed_value
from UEVaultManager.models.UEAssetClass import UEAsset
from UEVaultManager.models.UEAssetDbHandlerClass import UEAssetDbHandler
from UEVaultManager.models.UEAssetScraperClass import UEAssetScraper
from UEVaultManager.tkgui.modules.EditCellWindowClass import EditCellWindow
from UEVaultManager.tkgui.modules.EditRowWindowClass import EditRowWindow
from UEVaultManager.tkgui.modules.ExtendedWidgetClasses import ExtendedText, ExtendedCheckButton, ExtendedEntry
from UEVaultManager.tkgui.modules.functions import *
from UEVaultManager.tkgui.modules.functions_no_deps import convert_to_bool, convert_to_int, convert_to_float, convert_to_datetime
from UEVaultManager.tkgui.modules.ProgressWindowClass import ProgressWindow
from UEVaultManager.tkgui.modules.TaggedLabelFrameClass import TaggedLabelFrame
from UEVaultManager.utils.cli import get_max_threads

test_only_mode = False  # create some limitations to speed up the dev process - Set to True for debug Only


class DataSourceType(Enum):
    """ An enum to represent the data source type """
    FILE = 1
    SQLITE = 2


class EditableTable(Table):
    """
    A class that extends the pandastable.Table class, providing additional functionalities
    such as loading data from CSV files, searching, filtering, pagination, and editing cell values.
    :param container_frame: The parent frame for the table.
    :param data_source_type: The type of data source (DataSourceType.FILE or DataSourceType.SQLITE).
    :param data_source: The path to the source that contains the table data
    :param rows_per_page: The number of rows to show per page.
    :param show_toolbar: Whether to show the toolbar.
    :param show_statusbar: Whether to show the status bar.
    :param kwargs: Additional arguments to pass to the pandastable.Table class.
    """

    def __init__(
        self,
        container_frame=None,
        data_source_type=DataSourceType.FILE,
        data_source=None,
        rows_per_page=36,
        show_toolbar=False,
        show_statusbar=False,
        **kwargs
    ):
        self._last_selected_row = -1
        self._last_selected_col = -1
        self._changed_rows = []

        self.data_source_type = data_source_type
        self.data_source = data_source

        self.must_save = False
        self.must_rebuild = False
        self.container_frame = container_frame
        self.show_toolbar = show_toolbar
        self.show_statusbar = show_statusbar

        self.pagination_enabled = True
        self.rows_per_page = rows_per_page
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
        self.edit_cell_widget = None

        self.quick_edit_frame = None

        if self.data_source_type == DataSourceType.SQLITE:
            self.db_handler = UEAssetDbHandler(database_name=self.data_source, reset_database=False)
        else:
            self.db_handler = None
        self.load_data()
        Table.__init__(self, container_frame, dataframe=self.data, showtoolbar=show_toolbar, showstatusbar=show_statusbar, **kwargs)
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

    def gradient_color_cells(self, col_names=None, cmap='sunset', alpha=1) -> None:
        """
        Creates a gradient color for the cells os specified columns. The gradient depends on the cell value between min and max values for that column.
        :param col_names: The names of the columns to create a gradient color for.
        :param cmap: name of the colormap to use
        :param alpha: alpha value for the color
        """
        # import pylab as plt
        # cmaps = sorted(m for m in plt.cm.datad if not m.endswith("_r"))
        # print(cmaps)
        # possible cmaps:
        # 'Accent', 'Blues', 'BrBG', 'BuGn', 'BuPu', 'CMRmap', 'Dark2', 'GnBu', 'Greens', 'Greys', 'OrRd', 'Oranges', 'PRGn', 'Paired', 'Pastel1',
        #  'Pastel2', 'PiYG', 'PuBu', 'PuBuGn', 'PuOr', 'PuRd', 'Purples', 'RdBu', 'RdGy', 'RdPu', 'RdYlBu', 'RdYlGn', 'Reds', 'Set1', 'Set2', 'Set3',
        #  'Spectral', 'Wistia', 'YlGn', 'YlGnBu', 'YlOrBr', 'YlOrRd', 'afmhot', 'autumn', 'binary', 'bone', 'brg', 'bwr', 'cool', 'coolwarm', 'copper',
        #  'cubehelix', 'flag', 'gist_earth', 'gist_gray', 'gist_heat', 'gist_ncar', 'gist_rainbow', 'gist_stern', 'gist_yarg', 'gnuplot', 'gnuplot2',
        #  'gray', 'hot', 'hsv', 'jet', 'nipy_spectral', 'ocean', 'pink', 'prism', 'rainbow', 'seismic', 'spring', 'summer', 'tab10', 'tab20', 'tab20b',
        #  'tab20c', 'terrain', 'winter'

        if col_names is None:
            return
        df = self.data_filtered if self.data_filtered is not None else self.model.df
        for col_name in col_names:
            try:
                x = df[col_name]
            except KeyError:
                log_debug(f'gradient_color_cells: Column {col_name} not found in the table data.')
                continue
            clrs = self.values_to_colors(x, cmap, alpha)
            clrs = pd.Series(clrs, index=df.index)
            rc = self.rowcolors
            rc[col_name] = clrs

    def color_cells_if(self, col_names=None, color='green', value_to_check='True') -> None:
        """
        Set the cell color for the specified columns and the cell with a given value.
        :param col_names: The names of the columns to create a gradient color for.
        :param color: The color to set the cell to.
        :param value_to_check: The value to check for.
        """

        if col_names is None:
            return
        df = self.data_filtered if self.data_filtered is not None else self.model.df
        for col_name in col_names:
            try:
                mask = df[col_name] == value_to_check
            except KeyError:
                log_debug(f'color_cells_if: Column {col_name} not found in the table data.')
                continue
            self.setColorByMask(col=col_name, mask=mask, clr=color)

    def color_cells_if_not(self, col_names=None, color='grey', value_to_check='False') -> None:
        """
        Set the cell color for the specified columns and the cell with NOT a given value.
        :param col_names: The names of the columns to create a gradient color for.
        :param color: The color to set the cell to.
        :param value_to_check: The value to check for.
        """
        if col_names is None:
            return
        df = self.data_filtered if self.data_filtered is not None else self.model.df
        for col_name in col_names:
            try:
                mask = df[col_name] != value_to_check
            except KeyError:
                log_debug(f'color_cells_if_not: Column {col_name} not found in the table data.')
                continue
            self.setColorByMask(col=col_name, mask=mask, clr=color)

    def color_rows_if(self, col_names=None, color='#55555', value_to_check='True') -> None:
        """
        Set the row color for the specified columns and the rows with a given value.
        :param col_names: The names of the columns to check for the value.
        :param color: The color to set the row to.
        :param value_to_check: The value to check for.
        """
        if col_names is None:
            return
        df = self.data_filtered if self.data_filtered is not None else self.model.df

        for col_name in col_names:
            row_indices = []
            if col_name not in df.columns:
                continue
            try:
                mask = df[col_name]
            except KeyError:
                log_debug(f'color_rows_if: Column {col_name} not found in the table data.')
                continue
            for i in range(min(self.rows_per_page, len(mask))):
                try:
                    if str(mask[i]) == value_to_check:
                        row_indices.append(i)
                except KeyError:
                    log_debug(f'KeyError for row {i} in color_rows_if')
            if len(row_indices) > 0:  # Check if there are any row indices
                try:
                    self.setRowColors(rows=row_indices, clr=color, cols='all')
                except KeyError:
                    log_debug(f'KeyError for row in color_rows_if')
            return

    def set_preferences(self, default_pref=None) -> None:
        """
        Initializes the table preferences.
        :param default_pref: The default preferences to apply to the table.
        """
        # remove the warning: "A value is trying to be set on a copy of a slice from a DataFrame"
        # when sorting the table with pagination enabled
        # see: https://stackoverflow.com/questions/20625582/how-to-deal-with-settingwithcopywarning-in-pandas
        pd.options.mode.chained_assignment = None

        if default_pref is not None:
            config.apply_options(default_pref, self)

    def colorRows(self):
        """
        Color individual cells in column(s). Requires that the rowcolors
        dataframe has been set. This needs to be updated if the index is reset
        Override this method to check indexes when rebuildind data from en empty table
        """
        df = self.model.df
        rc = self.rowcolors
        rows = self.visiblerows
        offset = rows[0]
        idx = df.index[rows]

        for col in self.visiblecols:
            colname = df.columns[col]
            if colname in list(rc.columns):
                try:
                    colors = rc[colname].loc[idx]
                except KeyError:
                    colors = None
                if colors is not None:
                    for row in rows:
                        clr = colors.iloc[row - offset]
                        if not pd.isnull(clr):
                            self.drawRect(row, col, color=clr, tag='colorrect', delete=0)

    def set_colors(self) -> None:
        """
        Initializes the colors of some cells depending on their values.
        """
        if not gui_g.s.use_colors_for_data:
            self.redraw()
            return
        log_debug('set_colors')
        self.gradient_color_cells(col_names=['Review'], cmap='Set3', alpha=1)
        self.color_cells_if(col_names=['Owned', 'Discounted'], color='lightgreen', value_to_check='True')
        self.color_cells_if(col_names=['Grab result'], color='lightblue', value_to_check='NO_ERROR')
        self.color_cells_if_not(col_names=['Status'], color='#555555', value_to_check='ACTIVE')
        self.color_rows_if(col_names=['Status'], color='#555555', value_to_check='SUNSET')
        self.color_rows_if(col_names=['Obsolete'], color='#777777', value_to_check='True')
        self.redraw()

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
            self.total_pages = min(self.total_pages, len(self.data))
            if page < 0:
                page = 0
            elif page >= self.total_pages:
                page = self.total_pages - 1
            # Calculate start and end rows for current page
            self.current_page = page
            start = page * self.rows_per_page
            end = start + self.rows_per_page
            start = min(start, len(self.data))
            end = min(end, len(self.data))
            try:
                # Update table with data for current page
                self.model.df = self.data.iloc[start:end]
            except AttributeError:
                # self.redraw()
                log_debug('AttributeError in show_page')
                self.set_colors()
                return
        else:
            # Update table with all data
            self.model.df = self.data_filtered
            self.current_page = 0
        # self.redraw()
        self.set_colors()

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
        # by default the following values will be considered as 'NaN'
        # '#N/A', '#N/A N/A', '#NA', '-1.#IND', '-1.#QNAN', '-NaN', '-nan', '1.#IND', '1.#QNAN', '<NA>', 'N/A', 'NA', 'NULL', 'NaN', 'None', 'n/a', 'nan', 'null'
        # see https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html
        csv_options = {'on_bad_lines': 'warn', 'encoding': 'utf-8', 'keep_default_na': True}
        if self.data_source is None or not os.path.isfile(self.data_source):
            log_warning(f'File to read data from is not defined or not found: {self.data_source}')
            return
        self.must_rebuild = False
        if self.data_source_type == DataSourceType.FILE:
            try:
                self.data = pd.read_csv(self.data_source, **csv_options)
            except EmptyDataError:
                # will create an empty row with the correct columns
                str_data = get_csv_field_name_list(exclude_sql_only=True, return_as_string=True)  # column names
                str_data += '\n'
                str_data += create_empty_csv_row(return_as_string=True)  # dummy row
                self.data = pd.read_csv(io.StringIO(str_data), **csv_options)
                self.must_rebuild = True
            # fill all 'NaN' like values with 'None', to be similar to the database
            self.data.fillna('None', inplace=True)
        elif self.data_source_type == DataSourceType.SQLITE:
            try:
                data, column_names = self.db_handler.get_assets_data_for_csv()
                if len(data) <= 0 or data[0][0] is None:
                    # create an empty row (in the database) with the correct columns
                    self.db_handler.create_empty_row(return_as_string=False, empty_cell=gui_g.s.empty_cell)  # dummy row
                    data, column_names = self.db_handler.get_assets_data_for_csv()
                    self.must_rebuild = True
                self.data = pd.DataFrame(data, columns=column_names)
            except EmptyDataError:
                log_error(f'Unable to read data from database: {self.data_source}')
                return
        else:
            log_error(f'Unknown data source type: {self.data_source_type}')
            return

        self.init_data_format()  # could take some time with lots of rows

        # log_debug("\nCOL TYPES AFTER LOADING CSV\n")
        # self.data.info()  # direct print info

        self.total_pages = (len(self.data) - 1) // self.rows_per_page + 1
        self.data_filtered = self.data

    def save_data(self, source_type=None) -> None:
        """
        Saves the current table data to the CSV file.
        """
        if source_type is None:
            source_type = self.data_source_type
        data = self.data.iloc[0:len(self.data)]
        self.updateModel(TableModel(data))  # needed to restore all the data and not only the current page
        # noinspection GrazieInspection
        if source_type == DataSourceType.FILE:
            self.model.df.to_csv(self.data_source, index=False, na_rep='None', date_format=gui_g.s.csv_datetime_format)
        else:
            for row in self._changed_rows:
                # get the row data
                row_data = self.data.iloc[row]
                # convert the series to a dictionary
                row_data = row_data.to_dict()
                # convert the key names to the database column names
                asset_data = convert_csv_row_to_sql_row(row_data)
                ue_asset = UEAsset()
                ue_asset.init_from_dict(asset_data)
                # update the row in the database
                self.db_handler.save_ue_asset(ue_asset)
                log_info(f'UE_asset ({ue_asset.data["asset_id"]}) for row #{row} has been saved to the database')

        self.show_page(self.current_page)
        self.clear_rows_to_save()
        self.must_save = False
        box_message(f'Changed data has been saved to {self.data_source}')

    def init_data_format(self) -> None:
        """
        Initializes the data format for the table.
        """
        converters = {
            'Category': ('category',),
            'Grab result': ('category',),
            'Discounted': (convert_to_bool, bool),
            'Is new': (convert_to_bool, bool),
            'Free': (convert_to_bool, bool),
            'Can purchase': (convert_to_bool, bool),
            'Owned': (convert_to_bool, bool),
            'Obsolete': (convert_to_bool, bool),
            'Review': (convert_to_float, float),
            'Price': (convert_to_float, float),
            'Old price': (convert_to_float, float),
            'Discount price': (convert_to_float, float),
            'Discount percentage': (convert_to_float, float),
            'Stars': (convert_to_int, int),
            'Review count': (convert_to_int, int),
            'Creation date': (lambda x: convert_to_datetime(x, date_format='%Y-%m-%dT%H:%M:%S.%fZ'), pd.to_datetime),
            'Update date': (lambda x: convert_to_datetime(x, date_format=gui_g.s.csv_datetime_format), pd.to_datetime),
            'Date added': (lambda x: convert_to_datetime(x, date_format=gui_g.s.csv_datetime_format), pd.to_datetime),
        }

        for col in self.data.columns:
            if col in converters:
                converter, *args = converters[col]
                try:
                    self.data[col] = self.data[col].apply(converter, *args) if callable(converter) else self.data[col].astype(converter)
                except (KeyError, ValueError) as error:
                    log_warning(f'Could not convert column "{col}" using {converter}. Error: {error}')
            else:
                try:
                    self.data[col] = self.data[col].astype(str)
                except (KeyError, ValueError) as error:
                    log_error(f'Could not convert column "{col}" to string. Error: {error}')

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
        if self.data_source_type == DataSourceType.FILE:
            # we use a string comparison here to avoid to import of the module to check the real class of UEVM_cli_ref
            if gui_g.UEVM_cli_ref is None or 'UEVaultManagerCLI' not in str(type(gui_g.UEVM_cli_ref)):
                from_cli_only_message()
                return False
            else:
                gui_g.UEVM_cli_ref.list_assets(gui_g.UEVM_cli_args)
                self.current_page = 0
                self.load_data()
                self.show_page(0)
                return True
        elif self.data_source_type == DataSourceType.SQLITE:
            # we create the progress window here to avoid lots of imports in UEAssetScraper class
            progress_window = ProgressWindow('Rebuilding Data from database')
            progress_window.deactivate()
            max_threads = get_max_threads()
            owned_assets_only = False
            ue_asset_per_page = 100  # a bigger value will be refused by UE API
            if test_only_mode:
                start_row = 15000
                stop_row = 15000 + ue_asset_per_page
            else:
                start_row = 0
                stop_row = 0
            if gui_g.UEVM_cli_args and gui_g.UEVM_cli_args.get('force_refresh', False):
                load_from_files = False
            else:
                load_from_files = gui_g.UEVM_cli_args.get('offline', True)
            scraper = UEAssetScraper(
                start=start_row,
                stop=stop_row,
                assets_per_page=ue_asset_per_page,
                max_threads=max_threads,
                store_in_db=True,
                store_in_files=True,
                store_ids=False,  # useless for now
                load_from_files=load_from_files,
                clean_database=not test_only_mode,
                engine_version_for_obsolete_assets=None,  # None will allow get this value from its context
                egs=None if gui_g.UEVM_cli_ref is None else gui_g.UEVM_cli_ref.core.egs,
                progress_window=progress_window
            )
            scraper.gather_all_assets_urls(empty_list_before=True, owned_assets_only=owned_assets_only)
            if not progress_window.continue_execution:
                progress_window.close_window()
                return False
            scraper.save(owned_assets_only=owned_assets_only)
            progress_window.close_window()
            self.current_page = 0
            self.load_data()
            self.show_page(0)
            return True
        else:
            return False

    def apply_filters(self, filter_dict=None, global_search=None) -> None:
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
            if key == 'Grab result' and value == gui_g.s.default_category_for_all:
                continue
            try:
                # if data are corrupted, we can have a ValueError here
                self.data_filtered = self.data_filtered[self.data_filtered[key].apply(lambda x: str(value).lower() in str(x).lower())]
            except (KeyError, ValueError) as error:
                log_debug(f'Could not filter column "{key}" with value "{value}". Error: {error}')
        if global_search and global_search != gui_g.s.default_global_search:
            self.data_filtered = self.data_filtered[self.data_filtered.apply(lambda row: global_search.lower() in str(row).lower(), axis=1)]
        self.show_page(0)

    def reset_filters(self) -> None:
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
        # Note:
        # autoResizeColumns() will not resize table with more than 30 columns
        # same limit without settings the limit in adjustColumnWidths()
        # self.autoResizeColumns()
        self.adjustColumnWidths(limit=len(self.data.columns))
        self.redraw()

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

    def add_to_rows_to_save(self, row_index: int) -> None:
        """
        Adds the specified row to the list of rows to save.
        :param row_index: The index of the row to save.
        """
        if row_index < 0 or row_index > len(self.data) or row_index in self._changed_rows:
            return
        self._changed_rows.append(row_index)

    def clear_rows_to_save(self) -> None:
        """
        Clears the list of rows to save.
        """
        self._changed_rows = []

    def get_edited_row_values(self) -> dict:
        """
        Returns the values of the selected row in the table.
        :return: A dictionary containing the column names and their corresponding values for the selected row.
        """
        if self.edit_row_entries is None or self.edit_row_index is None:
            return {}
        entries_values = {}
        for key, entry in self.edit_row_entries.items():
            try:
                value = entry.get()
            except AttributeError:
                value = entry.get_content()  # for extendedWidgets
            except TypeError:
                value = entry.get('1.0', tk.END)
            entries_values[key] = value
        return entries_values

    def create_edit_record_window(self) -> None:
        """
        Creates the edit row window for the selected row in the table.
        """
        row_selected = self.getSelectedRow()
        if row_selected is None:
            return

        title = 'Edit current row'
        width = 900
        height = 1000
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
            if self.data_source_type == DataSourceType.FILE and is_on_state(key, [FieldState.SQL_ONLY, FieldState.ASSET_ONLY]):
                continue
            if self.data_source_type == DataSourceType.SQLITE and is_on_state(key, [FieldState.CSV_ONLY, FieldState.ASSET_ONLY]):
                continue
            label = key.replace('_', ' ').title()
            ttk.Label(edit_row_window.content_frame, text=label).grid(row=i, column=0, sticky=tk.W)
            lower_key = key.lower()

            if lower_key == 'image':
                image_url = value

            if lower_key == 'url':
                # we add a button to open the url in an inner frame
                inner_frame_url = tk.Frame(edit_row_window.content_frame)
                inner_frame_url.grid(row=i, column=1, sticky=tk.EW)
                entry = ttk.Entry(inner_frame_url)
                entry.insert(0, value)
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
                button = ttk.Button(inner_frame_url, text="Open URL", command=self.open_asset_url)
                button.pack(side=tk.RIGHT)
            elif is_from_type(key, [FieldType.TEXT]):
                entry = ExtendedText(edit_row_window.content_frame, height=3)
                entry.set_content(value)
                entry.grid(row=i, column=1, sticky=tk.EW)
            elif is_from_type(key, [FieldType.BOOL]):
                entry = ExtendedCheckButton(edit_row_window.content_frame, label='', images_folder=gui_g.s.assets_folder)
                entry.set_content(value)
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
        edit_row_window.initial_values = self.get_edited_row_values()

    def save_edit_row_record(self) -> None:
        """
        Saves the edited row values to the table data.
        """
        for key, value in self.get_edited_row_values().items():
            # if is_from_type(key, [FieldType.BOOL]):
            #    value = convert_to_bool(value)
            value = get_typed_value(csv_field=key, value=value)
            self.model.df.at[self.edit_row_index, key] = value
        row = self.edit_row_index
        self.edit_row_entries = None
        self.edit_row_index = None
        self.redraw()
        self.must_save = True
        self.edit_row_window.close_window()
        self.add_to_rows_to_save(row)
        self.update_quick_edit(row=row)

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
        height = 110
        # window is displayed at mouse position
        # x = self.master.winfo_rootx()
        # y = self.master.winfo_rooty()
        edit_cell_window = EditCellWindow(parent=self.master, title=title, width=width, height=height, editable_table=self)
        edit_cell_window.grab_set()
        edit_cell_window.minsize(width, height)

        # get and display the cell data
        col_name = self.model.df.columns[col_index]
        ttk.Label(edit_cell_window.content_frame, text=col_name).pack(side=tk.LEFT)
        if is_from_type(col_name, [FieldType.TEXT]):
            widget = ExtendedText(edit_cell_window.content_frame, tag=col_name, height=3)
            widget.set_content(cell_value)
            widget.focus_set()
        elif is_from_type(col_name, [FieldType.BOOL]):
            widget = ExtendedCheckButton(edit_cell_window.content_frame, tag=col_name, label='', images_folder=gui_g.s.assets_folder)
            widget.set_content(cell_value)
        else:
            # other field is just a ExtendedEntry
            widget = ExtendedEntry(edit_cell_window.content_frame, tag=col_name)
            widget.insert(0, cell_value)
            widget.focus_set()

        widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.edit_cell_widget = widget
        self.edit_cell_row_index = row_index
        self.edit_cell_col_index = col_index
        self.edit_cell_window = edit_cell_window
        edit_cell_window.initial_values = self.get_edit_cell_values()

    def get_edit_cell_values(self) -> str:
        """
        Returns the values of the selected cell in the table.
        :return: The value of the selected cell.
        """
        if self.edit_cell_widget is None:
            return ''
        tag = self.edit_cell_widget.tag
        value = self.edit_cell_widget.get_content()
        typed_value = get_typed_value(csv_field=tag, value=value)
        return typed_value

    def save_edit_cell_value(self) -> None:
        """
        Saves the edited cell value to the table data.
        """
        widget = self.edit_cell_widget
        if widget is None or self.edit_cell_row_index is None or self.edit_cell_col_index is None or self.edit_cell_widget is None:
            return
        row = self.edit_cell_row_index
        try:
            tag = self.edit_cell_widget.tag
            value = self.edit_cell_widget.get_content()
            typed_value = get_typed_value(csv_field=tag, value=value)
            self.model.df.iat[self.edit_cell_row_index, self.edit_cell_col_index] = typed_value
            self.must_save = True
            self.edit_cell_widget = None
            self.edit_cell_row_index = None
            self.edit_cell_col_index = None
        except TypeError:
            log_warning(f'Failed to get content of {widget}')
        self.redraw()
        self.edit_cell_window.close_window()
        self.add_to_rows_to_save(row)
        self.update_quick_edit(row=row)

    def update_quick_edit(self, quick_edit_frame: TaggedLabelFrame = None, row: int = None) -> None:
        """
        Quick edit the content some cells of the selected row.
        :param quick_edit_frame: The frame to display the cell content preview in.
        :param row: The row index of the selected cell.
        """
        if quick_edit_frame is None:
            quick_edit_frame = self.quick_edit_frame
        else:
            self.quick_edit_frame = quick_edit_frame

        if row is None or row >= len(self.model.df) or quick_edit_frame is None:
            return

        column_names = ['Url', 'Comment', 'Stars', 'Test result', 'Must buy', 'Alternative', 'Installed folder', 'Origin']
        for col_name in column_names:
            col = self.model.df.columns.get_loc(col_name)
            value = self.model.getValueAt(row=row, col=col)
            typed_value = get_typed_value(csv_field=col_name, value=value)
            quick_edit_frame.set_child_values(tag=col_name, content=typed_value, row=row, col=col)

    @staticmethod
    def quick_edit(quick_edit_frame: TaggedLabelFrame = None) -> None:
        """
        Resets the cell content preview.
        :param quick_edit_frame: The frame to reset the cell content preview in.
        """
        quick_edit_frame.set_default_content('Url')
        quick_edit_frame.set_default_content('Comments')
        quick_edit_frame.set_default_content('Stars')
        quick_edit_frame.set_default_content('Test result')
        quick_edit_frame.set_default_content('Must buy')
        quick_edit_frame.set_default_content('Installed folder')
        quick_edit_frame.set_default_content('Origin')
        quick_edit_frame.set_default_content('Alternative')

    def quick_edit_save_value(self, value: str, row: int = None, col: int = None, tag=None) -> None:
        """
        Saves the cell content preview.
        :param value: The value to save.
        :param row: The row index of the cell.
        :param col: The column index of the cell.
        :param tag: The tag associated to the control where the value come from
        """
        old_value = self.model.df.iat[row, col]

        typed_old_value = get_typed_value(sql_field=tag, value=old_value)
        typed_value = get_typed_value(sql_field=tag, value=value)

        if row is None or row >= len(self.model.df) or col is None or typed_old_value == typed_value:
            return
        try:
            self.model.df.iat[row, col] = typed_value
            self.redraw()
            self.must_save = True
            log_debug(f'Save preview value {typed_value} at row={row} col={col}')
            self.add_to_rows_to_save(row)
        except IndexError:
            log_warning(f'Failed to save preview value {typed_value} at row={row} col={col}')

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
        except (IndexError, KeyError):
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
        if asset_url is None or asset_url == '' or asset_url == gui_g.s.empty_cell:
            log_info('asset URL is empty for this asset')
            return
        webbrowser.open(asset_url)

    def reset_style(self) -> None:
        """
        Resets the table style. Usefull when style of the main ttk window has changed.
        """
        self.data.style.clear()
        self.redraw()
