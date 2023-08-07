# coding=utf-8
"""
Implementation for:
- EditableTable: a class that extends the pandastable.Table class, providing additional functionalities.
"""
import io
import webbrowser
from tkinter import ttk

import pandas as pd
from pandas.errors import EmptyDataError
from pandastable import Table, TableModel, config

from UEVaultManager.models.csv_sql_fields import create_empty_csv_row, get_csv_field_name_list, convert_csv_row_to_sql_row, is_on_state, \
    CSVFieldState, \
    CSVFieldType, is_from_type, get_typed_value, get_converters, get_csv_field_name
from UEVaultManager.models.UEAssetClass import UEAsset
from UEVaultManager.models.UEAssetDbHandlerClass import UEAssetDbHandler
from UEVaultManager.models.UEAssetScraperClass import UEAssetScraper
from UEVaultManager.tkgui.modules.cls.EditCellWindowClass import EditCellWindow
from UEVaultManager.tkgui.modules.cls.EditRowWindowClass import EditRowWindow
from UEVaultManager.tkgui.modules.cls.ExtendedWidgetClasses import ExtendedText, ExtendedCheckButton, ExtendedEntry
from UEVaultManager.tkgui.modules.cls.ProgressWindowClass import ProgressWindow
from UEVaultManager.tkgui.modules.functions import *
from UEVaultManager.tkgui.modules.types import DataSourceType
from UEVaultManager.utils.cli import get_max_threads

test_only_mode = False  # add some limitations to speed up the dev process - Set to True for debug Only


class EditableTable(Table):
    """
    A class that extends the pandastable.Table class, providing additional functionalities
    such as loading data from CSV files, searching, filtering, pagination, and editing cell values.
    :param container: The parent frame for the table.
    :param data_source_type: The type of data source (DataSourceType.FILE or DataSourceType.SQLITE).
    :param data_source: The path to the source that contains the table data.
    :param rows_per_page: The number of rows to show per page.
    :param show_toolbar: Whether to show the toolbar.
    :param show_statusbar: Whether to show the status bar.
    :param update_page_numbers_func: A function that updates the page numbers.
    :param update_rows_text_func: A function that updates the text that shows the number of rows.
    :param kwargs: Additional arguments to pass to the pandastable.Table class.
    """
    _data = {}
    _filtered = {}  # do not put the word "data" here to makje search in code easier
    _last_selected_row: int = -1
    _last_selected_col: int = -1
    _changed_rows = []
    _deleted_asset_ids = []
    _db_handler = None

    _frm_quick_edit = None
    _filter_frame = None
    _filter_mask = None

    _edit_row_window = None
    _edit_row_entries = None
    _edit_row_index: int = -1

    _edit_cell_window = None
    _edit_cell_row_index: int = -1
    _edit_cell_col_index: int = -1
    _edit_cell_widget = None

    _progress_window = None

    pagination_enabled: bool = True
    is_filtered: bool = False
    current_page: int = 1
    total_pages: int = 1
    must_save: bool = False
    must_rebuild: bool = False
    data_count: int = 0
    current_count: int = 0

    def __init__(
        self,
        container=None,
        data_source_type: DataSourceType = DataSourceType.FILE,
        data_source=None,
        rows_per_page: int = 36,
        show_toolbar: bool = False,
        show_statusbar: bool = False,
        update_page_numbers_func=None,
        update_rows_text_func=None,
        **kwargs
    ):
        if container is None:
            raise ValueError('container cannot be None')
        self._container = container
        self.data_source_type: DataSourceType = data_source_type
        self.data_source = data_source
        self.show_toolbar: bool = show_toolbar
        self.show_statusbar: bool = show_statusbar
        self.rows_per_page: int = rows_per_page
        self.update_page_numbers_func = update_page_numbers_func
        self.update_rows_text_func = update_rows_text_func
        if self.data_source_type == DataSourceType.SQLITE:
            self._db_handler = UEAssetDbHandler(database_name=self.data_source, reset_database=False)
        if not self.load_data():
            log_error('Failed to load data from data source when initializing the table')
        Table.__init__(
            self, container, dataframe=self.get_data(), showtoolbar=show_toolbar, showstatusbar=show_statusbar, **kwargs
        )  # get_data checked
        self.bind('<Double-Button-1>', self.create_edit_cell_window)

    def _generate_cell_selection_changed_event(self) -> None:
        """
        Create the event bindings for the table.
        """
        selected_row = self.currentrow
        selected_col = self.currentcol
        if (selected_row != self._last_selected_row) or (selected_col != self._last_selected_col):
            self._last_selected_row = selected_row
            self._last_selected_col = selected_col
            self.event_generate('<<CellSelectionChanged>>')

    def _show_progress(self, text='Loading...Please wait') -> None:
        """
        Show the progress window.
        :param text: The text to display in the progress window.
        :return:
        """
        if self._progress_window is None:
            self._progress_window = ProgressWindow(
                title=gui_g.s.app_title, icon=gui_g.s.app_icon_filename, show_stop_button=False, show_progress=False, max_value=0
            )
        self._progress_window.set_text(text)
        self._progress_window.set_activation(False)
        self._progress_window.update()

    def _close_progress(self) -> None:
        """
        Close the progress window.
        """
        if self._progress_window is not None:
            self._progress_window.close_window()
            self._progress_window = None

    def set_filter_frame(self, filter_frame=None) -> None:
        """
        Set the filter frame.
        :param filter_frame: The filter frame.
        """
        if filter_frame is None:
            raise ValueError('filters_frame cannot be None')
        self._filter_frame = filter_frame

    def set_quick_edit_frame(self, quick_edit_frame=None) -> None:
        """
        Set the quick edit frame.
        :param quick_edit_frame:  The quick edit frame.
        """
        if quick_edit_frame is None:
            raise ValueError('quick_edit_frame cannot be None')
        self._frm_quick_edit = quick_edit_frame

    def format_columns(self) -> None:
        """
        Set the columns format for the table.
        """
        data = self.get_data()  # get_data checked
        # log_debug("\nCOL TYPES BEFORE CONVERSION\n")
        # data.info()  # direct print info
        for col in data.columns:
            converters = get_converters(col)
            # at least 2 converters are expected: one for the convertion function and one for column type
            for converter in converters:
                try:
                    if callable(converter):
                        data[col] = data[col].apply(converter)  # apply the converter function to the column
                    else:
                        data[col] = data[col].astype(converter)
                except (KeyError, ValueError) as error:
                    log_warning(f'Could not convert column "{col}" using {converter}. Error: {error}')
        # log_debug("\nCOL TYPES AFTER CONVERSION\n")
        # data.info()  # direct print info

    def get_data(self) -> pd.DataFrame:
        """
        Return the data in the table.
        :return: data.
        """
        return self._data

    def get_data_filtered(self) -> pd.DataFrame:
        """
        Return the filtered data of the table.
        :return: data.
        """
        return self._filtered

    def get_current_data(self) -> pd.DataFrame:
        """
        Return the "valid" data depending on the context. Use this method preferably to get_data or get_data_filtered methods
        :return: data.
        """
        if self.is_filtered:
            self.current_count = len(self._filtered)
            return self._filtered
        else:
            self.current_count = len(self._data)
            return self._data

    def get_row_index_with_offet(self, row_index=None) -> int:
        """
        Return the "valid" row index depending on the context. It takes into account the pagination and the current page.
        :return: The row index with a correct offset.
        """
        if row_index is None:
            row_index = self.currentrow

        if self.pagination_enabled:
            row_index += self.rows_per_page * (self.current_page - 1)

        return row_index

    def valid_source_type(self, filename: str) -> bool:
        """
        Check if the file extension is valid for the current data source type.
        :param filename: The filename to check.
        :return: True if the file extension is valid for the current data source type, False otherwise.
        """
        file, ext = os.path.splitext(filename)
        stored_type = self.data_source_type
        self.data_source_type = DataSourceType.SQLITE if ext == '.db' else DataSourceType.FILE
        go_on = True
        if stored_type != self.data_source_type:
            go_on = box_yesno(
                f'The type of data source has changed from the previous one.\nYou should quit and restart the application to avoid any data loss.\nAre you sure you want to continue ?'
            )
        return go_on

    def load_data(self) -> bool:
        """
        Load data from the specified CSV file into the table.
        :return: True if the data has been loaded successfully, False otherwise.
        """
        self._show_progress('Loading Data from data source...')
        """
        if self.data_source is None or not os.path.isfile(self.data_source):
            log_warning(f'File to read data from is not defined or not found: {self.data_source}')
            return False
        """
        self.must_rebuild = False
        if not self.valid_source_type(self.data_source):
            return False
        try:
            if self.data_source_type == DataSourceType.FILE:
                data = pd.read_csv(self.data_source, **gui_g.s.csv_options)
                if len(data) <= 0 or data.iat[0][0] is None:  # iat checked
                    log_warning(f'Empty file: {self.data_source}. Adding a dummy row.')
                    self.create_row(add_to_existing=False)
                # fill all 'NaN' like values with 'None', to be similar to the database
                data.fillna('None', inplace=True)
                self._data = data
            elif self.data_source_type == DataSourceType.SQLITE:
                data = self._db_handler.get_assets_data_for_csv()
                column_names = self._db_handler.get_columns_name_for_csv()
                if len(data) <= 0 or data[0][0] is None:
                    log_warning(f'Empty file: {self.data_source}. Adding a dummy row.')
                    self.create_row(add_to_existing=False)
                else:
                    self._data = pd.DataFrame(data, columns=column_names)
            else:
                log_error(f'Unknown data source type: {self.data_source_type}')
                return False
        except EmptyDataError:
            log_warning(f'Empty file: {self.data_source}. Adding a dummy row.')
            self.create_row(add_to_existing=False)
        self.data_count = len(self._data)
        if self.data_count <= 0:
            log_error(f'No data found in data source: {self.data_source}')
            return False
        self.format_columns()  # could take some time with lots of rows
        self.total_pages = (self.data_count - 1) // self.rows_per_page + 1
        self._close_progress()
        return True

    def create_row(self, row_data=None, add_to_existing=True) -> None:
        """
        Create an empty row in the table.
        :param row_data: The data to add to the row.
        :param add_to_existing: True to add the row to the existing data, False to replace the existing data.
        """
        table_row = None
        if self.data_source_type == DataSourceType.FILE:
            # create an empty row with the correct columns
            str_data = get_csv_field_name_list(return_as_string=True)  # column names
            str_data += '\n'
            str_data += create_empty_csv_row(return_as_string=True)  # dummy row
            table_row = pd.read_csv(io.StringIO(str_data), **gui_g.s.csv_options)
        elif self.data_source_type == DataSourceType.SQLITE:
            if self._db_handler is None:
                self._db_handler = UEAssetDbHandler(database_name=self.data_source, reset_database=False)
            # create an empty row (in the database) with the correct columns
            data = self._db_handler.create_empty_row(
                return_as_string=False, empty_cell=gui_g.s.empty_cell, empty_row_prefix=gui_g.s.empty_row_prefix
            )  # dummy row
            column_names = self._db_handler.get_columns_name_for_csv()
            table_row = pd.DataFrame(data, columns=column_names)
        else:
            log_error(f'Unknown data source type: {self.data_source_type}')
        if row_data is not None and table_row is not None:
            # add the data to the row
            for col in row_data:
                table_row[col] = row_data[col]
        if add_to_existing and table_row is not None:
            self.must_rebuild = False
            # row is added at the start of the table. As it, the index is always known
            self._data = pd.concat([table_row, self._data], copy=False, ignore_index=True)
            self.add_to_rows_to_save(0)
        else:
            self.must_rebuild = True
            self._data = table_row

    def del_row(self, row_indexes=None) -> bool:
        """
        Delete the selected row in the table.
        :param row_indexes: The row to delete. If None, the selected row is deleted.
        """
        data_current = self.get_current_data()
        if row_indexes is None:
            row_indexes = self.multiplerowlist
        index_to_delete = []
        row_index = -1
        asset_id = 'None'
        for row_index in row_indexes:
            asset_id = 'None'
            if not data_current.empty and 0 <= row_index < len(data_current):
                row_index = self.get_row_index_with_offet(row_index)
                try:
                    index = data_current.index[row_index]
                    asset_id = data_current.at[index, 'Asset_id']  # at checked
                    index_to_delete.append(index)
                    self.add_to_asset_ids_to_delete(asset_id)
                    log_info(f'adding row #{row_index + 1} with asset_id={asset_id} to the list of index to delete')
                except (IndexError, KeyError) as error:
                    log_warning(f'Could add row #{row_index + 1} with asset_id={asset_id} to the list of index to delete. Error: {error!r}')
        number_deleted = len(index_to_delete)
        asset_str = f'{number_deleted} rows' if number_deleted > 1 else f' row #{row_index + 1} with asset_id {asset_id}'
        if number_deleted and box_yesno(f'Are you sure you want to delete {asset_str}? '):
            try:
                self._data.drop(index_to_delete, inplace=True, errors='ignore')
                self._filtered.drop(index_to_delete, inplace=True, errors='ignore')
                if self._filter_mask is not None:
                    self._filter_mask.drop(index_to_delete, inplace=True, errors='ignore')
                self.must_save = True
                # self._data.reset_index(drop=True, inplace=True)
                self.clearSelected()
                self.update(keep_filters=True)
            except (IndexError, KeyError) as error:
                log_warning(f'Could not perform the deletion of list of indexes. Error: {error!r}')
        return number_deleted > 0

    def save_data(self, source_type=None) -> None:
        """
        Save the current table data to the CSV file.
        """
        if source_type is None:
            source_type = self.data_source_type
        data = self.get_data()  # get_data checked
        self.updateModel(TableModel(data))  # needed to restore all the data and not only the current page
        # noinspection GrazieInspection
        if source_type == DataSourceType.FILE:
            data.to_csv(self.data_source, index=False, na_rep='', date_format=gui_g.s.csv_datetime_format)
        else:
            for row_index in self._changed_rows:
                row_data = self.get_row(row_index, return_as_dict=True)
                if row_data is None:
                    continue
                # convert the key names to the database column names
                asset_data = convert_csv_row_to_sql_row(row_data)
                ue_asset = UEAsset()
                try:
                    ue_asset.init_from_dict(asset_data)
                    # update the row in the database
                    if self._db_handler is None:
                        self._db_handler = UEAssetDbHandler(database_name=self.data_source, reset_database=False)
                    self._db_handler.save_ue_asset(ue_asset)
                    asset_id = ue_asset.data.get('asset_id', '')
                    log_info(f'UE_asset ({asset_id}) for row #{row_index} has been saved to the database')
                except (KeyError, ValueError, AttributeError) as error:
                    log_warning(f'Unable to save UE_asset for row #{row_index} to the database. Error: {error}')
            for asset_id in self._deleted_asset_ids:
                try:
                    # delete the row in the database
                    if self._db_handler is None:
                        self._db_handler = UEAssetDbHandler(database_name=self.data_source, reset_database=False)
                    self._db_handler.delete_asset(asset_id=asset_id)
                    log_info(f'row with asset_id={asset_id} has been deleted from the database')
                except (KeyError, ValueError, AttributeError) as error:
                    log_warning(f'Unable to delete asset_id={asset_id} to the database. Error: {error}')

        # self.update()
        self.clear_rows_to_save()
        self.clear_asset_ids_to_delete()
        self.must_save = False
        self.update()  # mandatory : if not, the table will diplays all the rows and not only the current page
        box_message(f'Changed data has been saved to {self.data_source}')

    def reload_data(self) -> bool:
        """
        Reload data from the CSV file and refreshes the table display.
        :return: True if the data has been loaded successfully, False otherwise.
        """
        if not self.load_data():
            return False
        self.update()
        return True

    def rebuild_data(self) -> bool:
        """
         Rebuild the data in the table.
         :return: True if the data was successfully rebuilt, False otherwise.
         """
        self._show_progress('Rebuilding Data from database...')
        progress_window = self._progress_window
        self.clear_rows_to_save()
        self.clear_asset_ids_to_delete()
        self.must_save = False
        if self.data_source_type == DataSourceType.FILE:
            # we use a string comparison here to avoid to import of the module to check the real class of UEVM_cli_ref
            if gui_g.UEVM_cli_ref is None or 'UEVaultManagerCLI' not in str(type(gui_g.UEVM_cli_ref)):
                from_cli_only_message()
                return False
            else:
                gui_g.UEVM_cli_ref.list_assets(gui_g.UEVM_cli_args)
                self.current_page = 1
                if not self.load_data():
                    return False
                self.update()
                return True
        elif self.data_source_type == DataSourceType.SQLITE:
            # we create the progress window here to avoid lots of imports in UEAssetScraper class
            max_threads = get_max_threads()
            owned_assets_only = False
            db_asset_per_page = 100  # a bigger value will be refused by UE API
            if test_only_mode:
                start_row = 15000
                stop_row = 15000 + db_asset_per_page
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
                assets_per_page=db_asset_per_page,
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
                self._close_progress()
                return False
            scraper.save(owned_assets_only=owned_assets_only)
            self.current_page = 1
            if not self.load_data():
                return False
            self.update()
            self._close_progress()
            return True
        else:
            self._close_progress()
            return False

    def gradient_color_cells(self, col_names=None, cmap='sunset', alpha=1) -> None:
        """
        Create a gradient color for the cells os specified columns. The gradient depends on the cell value between min and max values for that column.
        :param col_names: The names of the columns to create a gradient color for.
        :param cmap: name of the colormap to use.
        :param alpha: alpha value for the color.
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
        df = self.get_data()
        for col_name in col_names:
            try:
                x = df[col_name]
                clrs = self.values_to_colors(x, cmap, alpha)
                clrs = pd.Series(clrs, index=df.index)
                rc = self.rowcolors
                rc[col_name] = clrs
            except (KeyError, ValueError) as error:
                log_debug(f'gradient_color_cells: An error as occured with {col_name} : {error!r}')
                continue

    def color_cells_if(self, col_names=None, color='green', value_to_check='True') -> None:
        """
        Set the cell color for the specified columns and the cell with a given value.
        :param col_names: The names of the columns to create a gradient color for.
        :param color: The color to set the cell to.
        :param value_to_check: The value to check for.
        """
        if col_names is None:
            return
        df = self.get_data()
        for col_name in col_names:
            try:
                mask = df[col_name] == value_to_check
                self.setColorByMask(col=col_name, mask=mask, clr=color)
            except (KeyError, ValueError) as error:
                log_debug(f'color_cells_if: An error as occured with {col_name} : {error!r}')
                continue

    def color_cells_if_not(self, col_names=None, color='grey', value_to_check='False') -> None:
        """
        Set the cell color for the specified columns and the cell with NOT a given value.
        :param col_names: The names of the columns to create a gradient color for.
        :param color: The color to set the cell to.
        :param value_to_check: The value to check for.
        """
        if col_names is None:
            return
        df = self.get_data()
        for col_name in col_names:
            try:
                mask = df[col_name] != value_to_check
                self.setColorByMask(col=col_name, mask=mask, clr=color)
            except (KeyError, ValueError) as error:
                log_debug(f'color_cells_if_not: An error as occured with {col_name} : {error!r}')
                continue

    def color_rows_if(self, col_names=None, color='#555555', value_to_check='True') -> None:
        """
        Set the row color for the specified columns and the rows with a given value.
        :param col_names: The names of the columns to check for the value.
        :param color: The color to set the row to.
        :param value_to_check: The value to check for.
        """
        if col_names is None:
            return
        df = self.get_data()
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
                except (KeyError, IndexError) as error:
                    log_debug(f'Error in color_rows_if: {error!r}')
            return

    def set_preferences(self, default_pref=None) -> None:
        """
        Initialize the table preferences.
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
        Color individual cells in column(s). Requires that the rowcolors.
        dataframe has been set. This needs to be updated if the index is reset.
        Override created to check indexes when rebuildind data from en empty table.
        """
        # df = self.model.df
        df = self.get_data()  # to check
        rc = self.rowcolors
        rows = self.visiblerows
        offset = rows[0]
        try:
            idx = df.index[rows]
        except IndexError:
            return
        for col in self.visiblecols:
            colname = df.columns[col]
            if colname in list(rc.columns):
                try:
                    colors = rc[colname].loc[idx]  # loc checked
                except KeyError:
                    colors = None
                if colors is not None:
                    for row in rows:
                        clr = colors.iloc[row - offset]  # iloc checked
                        if not pd.isnull(clr):
                            self.drawRect(row, col, color=clr, tag='colorrect', delete=0)

    def set_colors(self) -> None:
        """
        Initialize the colors of some cells depending on their values.
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
        Handls left-click events on the table.
        :param event: The event that triggered the function call.
        """
        super().handle_left_click(event)
        self._generate_cell_selection_changed_event()

    def handle_right_click(self, event) -> None:
        """
        Handle right-click events on the table.
        :param event: The event that triggered the function call.
        """
        super().handle_right_click(event)
        self._generate_cell_selection_changed_event()

    def update(self, reset_page=False, keep_filters=False) -> None:
        """
        Display the specified page of the table data.*
        :param reset_page: Whether to reset the current page to 1.
        :param keep_filters: Whether to keep the current filters.
        """
        if reset_page:
            self.current_page = 1
        data = self.get_data()  # get_data checked
        if not keep_filters:
            mask = self._filter_frame.create_mask() if self._filter_frame is not None else None
        else:
            mask = self._filter_mask
        if mask is not None:
            self._filtered = data[mask]
            self.is_filtered = True
            self.current_page = 1
        else:
            self._filtered = data
            self.is_filtered = False
        self._filter_mask = mask
        self.update_page()

    def redraw(self, event=None, callback=None):
        """
        Redraw the table
        Override created for debugging
        :param event: The event that triggered the function call.
        :param callback: The callback function to call after the table has been redrawn.
        """
        super().redraw(event, callback)

    def update_page(self) -> None:
        """
        Update the page.
        """
        self.data_count = len(self._data)
        self.current_count = len(self.get_current_data())
        if self.pagination_enabled:
            self.total_pages = (self.current_count - 1) // self.rows_per_page + 1
            start = (self.current_page - 1) * self.rows_per_page
            end = start + self.rows_per_page
            try:
                # could be empty before load_data is called
                self.model.df = self.get_current_data().iloc[start:end]  # iloc checked
            except IndexError:
                self.current_page = self.total_pages
        else:
            # Update table with all data
            self.model.df = self.get_current_data()  # model.df checked
            self.current_page = 1
            self.total_pages = 1
        # self.redraw() # done in set_colors
        self.set_colors()
        if self.update_page_numbers_func is not None:
            self.update_page_numbers_func()
        if self.update_page_numbers_func is not None:
            self.update_rows_text_func()

    def next_page(self) -> None:
        """
        Navigate to the next page of the table data.
        """
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update()

    def prev_page(self) -> None:
        """
        Navigate to the previous page of the table data.
        """
        if self.current_page > 1:
            self.current_page -= 1
            self.update()

    def first_page(self) -> None:
        """
        Navigate to the first page of the table data.
        """
        self.current_page = 1
        self.update()

    def last_page(self) -> None:
        """
        Navigate to the last page of the table data.
        """
        self.current_page = self.total_pages
        self.update()

    def expand_columns(self) -> None:
        """
        Expand the width of all columns in the table.
        """
        self.expandColumns(factor=gui_g.s.expand_columns_factor)

    def contract_columns(self) -> None:
        """
        Contract the width of all columns in the table.
        """
        self.contractColumns(factor=gui_g.s.contract_columns_factor)

    def autofit_columns(self) -> None:
        """
        Automatically resize the columns to fit their content.
        """
        # Note:
        # autoResizeColumns() will not resize table with more than 30 columns
        # same limit without settings the limit in adjustColumnWidths()
        # self.autoResizeColumns()
        self.adjustColumnWidths(limit=len(self.get_data().columns))  # get_data checked
        self.redraw()

    def zoom_in(self) -> None:
        """
        Increase the font size of the table.
        """
        self.zoomIn()

    def zoom_out(self) -> None:
        """
        Decrease the font size of the table.
        """
        self.zoomOut()

    def add_to_rows_to_save(self, row_index: int) -> None:
        """
        Adds the specified row to the list of rows to save.
        :param row_index: The index of the row to save.
        """
        if row_index < 0 or row_index > self.current_count or row_index in self._changed_rows:  # get_data checked
            return
        self._changed_rows.append(row_index)

    def clear_rows_to_save(self) -> None:
        """
        Clear the list of rows to save.
        """
        self._changed_rows = []

    def add_to_asset_ids_to_delete(self, asset_id: str) -> None:
        """
        Adds the specified row to the list of rows to delete.
        :param asset_id: The asset_id of the row to delete.
        """
        if asset_id in self._deleted_asset_ids:
            return
        self._deleted_asset_ids.append(asset_id)

    def clear_asset_ids_to_delete(self) -> None:
        """
        Clear the list of asset_ids to delete.
        """
        self._deleted_asset_ids = []

    def get_selected_rows(self):
        """
        Return the selected rows in the table.
        :return: the selected rows.
        """
        selected_rows = []
        selected_row_indices = self.multiplerowlist
        if selected_row_indices:
            selected_rows = self.get_current_data().iloc[selected_row_indices]  # iloc checked
        return selected_rows

    def get_row(self, row_index: int, return_as_dict: bool = False):
        """
        Return the row at the specified index.
        :param row_index: row index. This value must be offsetted BEFORE if needed
        :param return_as_dict: Set to True to return the row as a dict
        :return: the row at the specified index.
        """
        try:

            record = self.get_current_data().iloc[row_index]  # iloc checked
            # get the row of the pandastable
            # (not the row of the dataframe, which is offsetted by the pagination)

            if return_as_dict:
                return record.to_dict()
            else:
                return record
        except IndexError:
            return None

    def update_row(self, row_index: int, ue_asset_data: dict, no_table_update=False):
        """
        Update the row with the data from ue_asset_data
        :param row_index: row index. This value must be offsetted BEFORE if needed
        :param ue_asset_data:
        :param no_table_update:
        :return:
        """
        if ue_asset_data is None or not ue_asset_data or len(ue_asset_data) == 0:
            return
        if isinstance(ue_asset_data, list):
            ue_asset_data = ue_asset_data[0]
        asset_id = self.get_cell(row_index, self.get_col_index('Asset_id'))
        log_info(f'Updating row {row_index} with asset_id={asset_id}')
        for key, value in ue_asset_data.items():
            typed_value = get_typed_value(sql_field=key, value=value)
            # get the column index of the key
            col_name = get_csv_field_name(key)
            # if col_name == 'Tags':
            #     typed_value = 'ICICICI' # debug only
            if self.data_source_type == DataSourceType.FILE and is_on_state(key, [CSVFieldState.SQL_ONLY, CSVFieldState.ASSET_ONLY]):
                continue
            if self.data_source_type == DataSourceType.SQLITE and is_on_state(key, [CSVFieldState.CSV_ONLY, CSVFieldState.ASSET_ONLY]):
                continue
            col_index = self.get_col_index(col_name)  # return -1 col_name is not on the table
            if col_index >= 0 and not self.update_cell(row_index, col_index, typed_value):
                log_warning(f'Failed to update the cell ({row_index}, {col_name}) value')
                continue
        if not no_table_update:
            self.add_to_rows_to_save(row_index)
            self.must_save = True
            self.update()

    def get_col_name(self, col_index: int) -> str:
        """
        Return the name of the column at the specified index.
        :param col_index: column index. This value must be offsetted BEFORE if needed
        :return: the name of the column at the specified index.
        """
        try:
            return self.get_current_data().columns[col_index]  # get_current_data checked
        except IndexError:
            return ''

    def get_col_index(self, col_name: str) -> int:
        """
        Return the index of the column with the specified name.
        :param col_name: column name.
        :return: the index of the column with the specified name.
        """
        try:
            return self.get_current_data().columns.get_loc(col_name)  # get_current_data checked
        except KeyError:
            return -1

    def get_cell(self, row_index: int, col_index: int):
        """
        Return the value of the cell at the specified row and column.
        :param row_index: row index. This value must be offsetted BEFORE if needed
        :param col_index: column index.
        :return: the value of the cell or None if the row or column index is out of range.
        """
        if row_index < 0 or col_index < 0:
            return None
        try:
            return self.get_current_data().iat[row_index, col_index]  # iat checked
        except IndexError:
            return None

    def update_cell(self, row_index: int, col_index: int, value) -> bool:
        """
        Update the value of the cell at the specified row and column.
        :param row_index: row index. This value must be offsetted BEFORE if needed
        :param col_index: column index or column name.
        :param value: the new value of the cell.
        :return: True if the cell was updated, False otherwise.
        """
        if row_index < 0 or col_index < 0:
            return False
        try:
            # TODO: PB ICI CAR _data et _filtered sont différent. Quel est celui utilisé par l'affichage ?
            self.get_current_data().iat[row_index, col_index] = value  # iat checked
            """
            # debug only
            asset_id_current = self.get_current_data().iat[row_index, 0]
            asset_id_data = self._data.iat[row_index, 0]
            asset_id_filtered = self._filtered.iat[row_index, 0]
            tags_current = self.get_current_data().iat[row_index, 36]
            tags_data = self._data.iat[row_index, 36]
            tags_filtered = self._filtered.iat[row_index, 36]
            print(f'value={value} asset_id_current={asset_id_current}, asset_id_data={asset_id_data}, asset_id_filtered={asset_id_filtered}')
            print(f'tags_current={tags_current}, tags_data={tags_data}, tags_filtered={tags_filtered}')
            """
            return True
        except IndexError:
            return False

    def get_edited_row_values(self) -> dict:
        """
        Return the values of the selected row in the table.
        :return: A dictionary containing the column names and their corresponding values for the selected row.
        """
        if self._edit_row_entries is None or self._edit_row_index < 0:
            return {}
        entries_values = {}
        for key, entry in self._edit_row_entries.items():
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
        Create the edit row window for the selected row in the table.
        """
        row_index = self.getSelectedRow()
        row_index = self.get_row_index_with_offet(row_index)
        if row_index is None:
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

        self.edit_record(row_index)

    def edit_record(self, row_index: int = None) -> None:
        """
        Edit the values of the specified row in the table.
        :param row_index: The index of the row to edit.
        """
        edit_row_window = gui_g.edit_row_window_ref
        if row_index is None or edit_row_window is None:
            return
        # get and display the row data
        row_data = self.get_row(row_index, return_as_dict=True)
        if row_data is None:
            log_warning(f'edit_record: row_data is None for row_index={row_index}')
            return
        entries = {}
        image_url = ''
        for i, (key, value) in enumerate(row_data.items()):
            if self.data_source_type == DataSourceType.FILE and is_on_state(key, [CSVFieldState.SQL_ONLY, CSVFieldState.ASSET_ONLY]):
                continue
            if self.data_source_type == DataSourceType.SQLITE and is_on_state(key, [CSVFieldState.CSV_ONLY, CSVFieldState.ASSET_ONLY]):
                continue
            label = key.replace('_', ' ').title()
            ttk.Label(edit_row_window.content_frame, text=label).grid(row=i, column=0, sticky=tk.W)
            key_lower = key.lower()

            if key_lower == 'image':
                image_url = value

            # if key_lower == 'url':
            #     # we add a button to open the url in an inner frame
            #     inner_frame_url = tk.Frame(self._edit_row_window.content_frame)
            #     inner_frame_url.grid(row=i, column=1, sticky=tk.EW)
            #     entry = ttk.Entry(inner_frame_url)
            #     entry.insert(0, value)
            #     entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            #     button = ttk.Button(inner_frame_url, text="Open URL", command=self.open_asset_url)
            #     button.pack(side=tk.RIGHT)
            # elif is_from_type(key, [CSVFieldType.TEXT]):
            if is_from_type(key, [CSVFieldType.TEXT]):
                entry = ExtendedText(edit_row_window.content_frame, height=3)
                entry.set_content(value)
                entry.grid(row=i, column=1, sticky=tk.EW)
            elif is_from_type(key, [CSVFieldType.BOOL]):
                entry = ExtendedCheckButton(edit_row_window.content_frame, label='', images_folder=gui_g.s.assets_folder)
                entry.set_content(value)
                entry.grid(row=i, column=1, sticky=tk.EW)
                # TODO : add other extended widget for specific type (CSVFieldType.DATETIME , CSVFieldType.LIST)
            else:
                # other field is just a usual entry
                entry = ttk.Entry(edit_row_window.content_frame)
                entry.insert(0, value)
                entry.grid(row=i, column=1, sticky=tk.EW)

            entries[key] = entry

        # image preview
        show_asset_image(image_url=image_url, canvas_image=edit_row_window.control_frame.canvas_image)

        self._edit_row_entries = entries
        self._edit_row_index = row_index
        self._edit_row_window = edit_row_window
        edit_row_window.initial_values = self.get_edited_row_values()

    def save_edit_row_record(self) -> None:
        """
        Save the edited row values to the table data.
        """
        for key, value in self.get_edited_row_values().items():
            # if is_from_type(key, [CSVFieldType.BOOL]):
            #    value = convert_to_bool(value)
            value = get_typed_value(csv_field=key, value=value)
            self.get_current_data().at[self._edit_row_index, key] = value  # at checked
        row = self._edit_row_index
        self._edit_row_entries = None
        self._edit_row_index = -1
        self.redraw()
        self.must_save = True
        self._edit_row_window.close_window()
        self.add_to_rows_to_save(row)
        self.update_quick_edit(row)

    def move_to_prev_record(self) -> None:
        """
        Navigate to the previous row in the table and opens the edit row window.
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
        Navigate to the next row in the table and opens the edit row window.
        """
        row_selected = self.getSelectedRow()
        max_displayed_rows = self.model.df.shape[0] - 1  # df checked: best way to get the number of displayed rows
        if row_selected is None or row_selected >= max_displayed_rows:
            return
        self.setSelectedRow(row_selected + 1)
        self.redraw()
        self._generate_cell_selection_changed_event()
        self.edit_record(row_selected + 1)

    def create_edit_cell_window(self, event) -> None:
        """
        Create the edit cell window for the selected cell in the table.
        :param event: The event that triggered the creation of the edit cell window.
        """
        row_index = self.get_row_clicked(event)
        col_index = self.get_col_clicked(event)
        if row_index is None or col_index is None:
            return None
        row_index = self.get_row_index_with_offet(row_index)
        cell_value = self.get_cell(row_index, col_index)
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
        col_name = self.get_col_name(col_index)
        ttk.Label(edit_cell_window.content_frame, text=col_name).pack(side=tk.LEFT)
        if is_from_type(col_name, [CSVFieldType.TEXT]):
            widget = ExtendedText(edit_cell_window.content_frame, tag=col_name, height=3)
            widget.set_content(str(cell_value))
            widget.focus_set()
            edit_cell_window.set_size(width=width, height=height + 80)  # more space for the lines in the text
        elif is_from_type(col_name, [CSVFieldType.BOOL]):
            widget = ExtendedCheckButton(edit_cell_window.content_frame, tag=col_name, label='', images_folder=gui_g.s.assets_folder)
            widget.set_content(bool(cell_value))
        else:
            # other field is just a ExtendedEntry
            widget = ExtendedEntry(edit_cell_window.content_frame, tag=col_name)
            widget.insert(0, str(cell_value))
            widget.focus_set()

        widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._edit_cell_widget = widget
        self._edit_cell_row_index = row_index
        self._edit_cell_col_index = col_index
        self._edit_cell_window = edit_cell_window
        edit_cell_window.initial_values = self.get_edit_cell_values()

    def get_edit_cell_values(self) -> str:
        """
        Return the values of the selected cell in the table.
        :return: The value of the selected cell.
        """
        if self._edit_cell_widget is None:
            return ''
        tag = self._edit_cell_widget.tag
        value = self._edit_cell_widget.get_content()
        typed_value = get_typed_value(csv_field=tag, value=value)
        return typed_value

    def save_edit_cell_value(self) -> None:
        """
        Save the edited cell value to the table data.
        """
        widget = self._edit_cell_widget
        if widget is None or self._edit_cell_widget is None or self._edit_cell_row_index < 0 or self._edit_cell_col_index < 0:
            return
        row_index = self._edit_cell_row_index
        try:
            tag = self._edit_cell_widget.tag
            value = self._edit_cell_widget.get_content()
            row_index = self._edit_cell_row_index
            col_index = self._edit_cell_col_index
            typed_value = get_typed_value(csv_field=tag, value=value)
            if not self.update_cell(row_index, col_index, typed_value):
                log_warning(f'Failed to update the cell ({row_index}, {col_index}) value')
                return
            self.must_save = True
            self._edit_cell_widget = None
            self._edit_cell_row_index = -1
            self._edit_cell_col_index = -1
        except TypeError:
            log_warning(f'Failed to get content of {widget}')
        self.redraw()
        self._edit_cell_window.close_window()
        self.add_to_rows_to_save(row_index)
        self.update_quick_edit(row_index=row_index)

    def update_quick_edit(self, row_index: int = None) -> None:
        """
        Quick edit the content some cells of the selected row.
        :param row_index: The row index of the selected cell.
        """
        quick_edit_frame = self._frm_quick_edit
        if quick_edit_frame is None:
            quick_edit_frame = self._frm_quick_edit
        else:
            self._frm_quick_edit = quick_edit_frame

        if row_index is None or row_index >= self.current_count or quick_edit_frame is None:
            return

        column_names = ['Asset_id', 'Url']
        column_names.extend(get_csv_field_name_list(filter_on_states=[CSVFieldState.USER]))
        for col_name in column_names:
            col_index = self.get_col_index(col_name)
            value = self.get_cell(row_index, col_index)
            if col_name == 'Asset_id':
                asset_id = value
                quick_edit_frame.config(text=f'Quick Editing Asset: {asset_id}')
                continue
            typed_value = get_typed_value(csv_field=col_name, value=value)
            if col_index >= 0:
                quick_edit_frame.set_child_values(tag=col_name, content=typed_value, row=row_index, col=col_index)

    def quick_edit(self) -> None:
        """
        Reset the cell content preview.
        """
        self._frm_quick_edit.config(text='Select a row for Quick Editing')
        column_names = get_csv_field_name_list(filter_on_states=[CSVFieldState.USER])
        for col_name in column_names:
            self._frm_quick_edit.set_default_content(col_name)

    def quick_edit_save_value(self, row_index: int = -1, col_index: int = -1, value: str = '', tag=None) -> None:
        """
        Save the cell content preview.
        :param value: The value to save.
        :param row_index: The row_index index of the cell.
        :param col_index: The col_indexumn index of the cell.
        :param tag: The tag associated to the control where the value come from.
        """
        old_value = self.get_cell(row_index, col_index)

        typed_old_value = get_typed_value(sql_field=tag, value=old_value)
        typed_value = get_typed_value(sql_field=tag, value=value)

        if row_index < 0 or row_index >= self.current_count or col_index < 0 or typed_old_value == typed_value:
            return
        try:
            if not self.update_cell(row_index, col_index, typed_value):
                log_warning(f'Failed to update the cell ({row_index}, {col_index}) value')
                return
            self.redraw()
            self.must_save = True
            log_debug(f'Save preview value {typed_value} at row={row_index} col={col_index}')
            self.add_to_rows_to_save(row_index)
        except IndexError:
            log_warning(f'Failed to save preview value {typed_value} at row={row_index} col={col_index}')

    def get_image_url(self, row_index: int = None) -> str:
        """
        Return the image URL of the selected row.
        :param row_index: The row index of the selected cell.
        :return: The image URL of the selected row.
        """
        row_index = self.get_row_index_with_offet(row_index)
        return '' if row_index is None else self.get_cell(row_index, self.get_col_index('Image'))

    def open_asset_url(self, url: str = None):
        """
        Open the asset URL in a web browser.
        :param url: The URL to open.
        """
        if url is None:
            if self._edit_row_entries is None:
                return
            asset_url = self._edit_row_entries['Url'].get()
        else:
            asset_url = url
        log_info(f'calling open_asset_url={asset_url}')
        if asset_url is None or asset_url == '' or asset_url == gui_g.s.empty_cell:
            log_info('asset URL is empty for this asset')
            return
        webbrowser.open(asset_url)

    def reset_style(self) -> None:
        """
        Reset the table style. Usefull when style of the main ttk window has changed.
        """
        self.get_data().style.clear()  # get_data checked
        self.redraw()
