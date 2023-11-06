# coding=utf-8
"""
Implementation for:
- EditableTable: class that extends the pandastable.Table class, providing additional functionalities.
"""
import io
import os
import tkinter as tk
import warnings
import webbrowser
from tkinter import ttk

import pandas as pd
from pandas.errors import EmptyDataError, IndexingError
from pandastable import config, Table, TableModel

import UEVaultManager.models.csv_sql_fields as gui_t  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.models.types import DateFormat
from UEVaultManager.models.UEAssetClass import UEAsset
from UEVaultManager.models.UEAssetDbHandlerClass import UEAssetDbHandler
from UEVaultManager.models.UEAssetScraperClass import UEAssetScraper
from UEVaultManager.tkgui.modules.cls.EditCellWindowClass import EditCellWindow
from UEVaultManager.tkgui.modules.cls.EditRowWindowClass import EditRowWindow
from UEVaultManager.tkgui.modules.cls.ExtendedWidgetClasses import ExtendedCheckButton, ExtendedEntry, ExtendedText
from UEVaultManager.tkgui.modules.cls.FakeProgressWindowClass import FakeProgressWindow
from UEVaultManager.tkgui.modules.types import DataFrameUsed, DataSourceType
from UEVaultManager.utils.cli import get_max_threads

warnings.filterwarnings('ignore', category=FutureWarning)  # Avoid the FutureWarning when PANDAS use ser.astype(object).apply()


class EditableTable(Table):
    """
    A class that extends the pandastable.Table class, providing additional functionalities
    such as loading data from CSV files, searching, filtering, pagination, and editing cell values.
    :param container: parent frame for the table.
    :param data_source_type: type of data source (DataSourceType. FILE or DataSourceType. DATABASE).
    :param data_source: path to the source that contains the table data.
    :param rows_per_page: number of rows to show per page.
    :param show_toolbar: whether to show the toolbar.
    :param show_statusbar: whether to show the status bar.
    :param update_controls_state_func: function that updates the page numbers.
    :param update_preview_info_func: function that updates previewed infos of the current asset.
    :param kwargs: additional arguments to pass to the pandastable.Table class.
    """
    _data: pd.DataFrame = None
    _last_selected_row: int = -1
    _last_selected_col: int = -1
    _last_cell_value: str = ''
    _changed_rows = []
    _deleted_asset_ids = []
    _db_handler = None
    _frm_quick_edit = None
    _frm_filter = None
    _edit_row_window = None
    _edit_row_entries = None
    _edit_row_number: int = -1
    _edit_cell_window = None
    _edit_cell_row_number: int = -1
    _edit_cell_col_index: int = -1
    _edit_cell_widget = None
    _dftype_for_coloring = DataFrameUsed.MODEL  # type of dataframe used for coloring
    _is_scanning = False  # True when a folders scan is in progress
    _errors: [Exception] = []
    _current_page: int = 1
    _current_page_saved: int = 1
    _is_filtered: bool = False
    _is_filtered_saved: bool = False
    _column_infos_saved = False  # used to see if column_infos has changed
    columns_saved_str: str = ''
    is_header_dragged = False  # true when a col header is currently dragged by a mouse mouvement
    logger = gui_f.logging.getLogger(__name__.split('.')[-1])  # keep only the class name
    gui_f.update_loggers_level(logger)
    model: TableModel = None  # setup in table.__init__
    rowcolors: pd.DataFrame = None  # setup in table.__init__
    df_unfiltered: pd.DataFrame = None  # unfiltered dataframe (default)
    df_filtered: pd.DataFrame = None  # filtered dataframe
    progress_window: FakeProgressWindow = None
    pagination_enabled: bool = True
    total_pages: int = 1
    must_save: bool = False
    must_rebuild: bool = False

    def __init__(
        self,
        container=None,
        data_source_type: DataSourceType = DataSourceType.FILE,
        data_source=None,
        rows_per_page: int = 37,
        show_toolbar: bool = False,
        show_statusbar: bool = False,
        update_controls_state_func=None,
        update_preview_info_func=None,
        **kwargs
    ):
        if container is None:
            raise ValueError('container can not be None')
        self._container = container
        self.data_source_type: DataSourceType = data_source_type
        self.data_source = data_source
        self.show_toolbar: bool = show_toolbar
        self.show_statusbar: bool = show_statusbar
        self.rows_per_page: int = rows_per_page
        self.update_controls_state_func = update_controls_state_func
        self.update_preview_info_func = update_preview_info_func
        self.set_defaults()  # will create and reset all the table properties. To be done FIRST
        gui_f.show_progress(container, text='Loading Data from data source...')
        if self.is_using_database():
            self._db_handler = UEAssetDbHandler(database_name=self.data_source)
        df_loaded = self.read_data()
        if df_loaded is None:
            self.logger.error('Failed to load data from data source when initializing the table')
            # previous line will NOT quit the application (why ?)
            return
        else:
            Table.__init__(self, container, dataframe=df_loaded, showtoolbar=show_toolbar, showstatusbar=show_statusbar, **kwargs)
            # self.set_data(self.set_columns_type(df_loaded), df_type=DataFrameUsed.UNFILTERED)  # is format necessary ?
            self.set_data(df_loaded, df_type=DataFrameUsed.UNFILTERED)
            self.resize_columns()
            self.bind('<Double-Button-1>', self.create_edit_cell_window)
        gui_f.close_progress(self)

    @property
    def current_page(self) -> int:
        """
        Get the current page.
        :return: current page number.
        """
        return self._current_page

    @current_page.setter
    def current_page(self, value: int) -> None:
        """
        Set the current page.
        :param value: page number to set.
        """
        self._current_page_saved = self._current_page
        self._current_page = value
        # self.update_controls_state_func()
        # self.update_preview_info_func()

    @property
    def is_filtered(self) -> int:
        """
        Get the current page.
        :return: current page number.
        """
        return self._is_filtered

    @is_filtered.setter
    def is_filtered(self, value: bool) -> None:
        """
        Set the filtered state.
        :param value: filtered state to set.
        """
        self._is_filtered_saved = self._is_filtered
        self._is_filtered = value

    @property
    def db_handler(self) -> UEAssetDbHandler:
        """
        Get the db handler.
        :return: db handler.
        """
        return self._db_handler

    @staticmethod
    def fillna_fixed(dataframe: pd.DataFrame) -> None:
        """
        Fill the empty cells in the dataframe. Fix FutureWarning messages by using the correct value for each dtype
        :param dataframe: dataframe to fill.
        """
        for col in dataframe.columns:
            if dataframe[col].dtype == 'object':
                # dataframe[col].fillna(gui_g.s.empty_cell, inplace=True)  # does not replace all possible values
                dataframe[col].replace(gui_g.s.cell_is_empty_list, gui_g.s.empty_cell, regex=False, inplace=True)
            elif dataframe[col].dtype == 'int64':
                dataframe[col].fillna(0, inplace=True)
            elif dataframe[col].dtype == 'float64':
                dataframe[col].fillna(0.0, inplace=True)
            elif dataframe[col].dtype == 'bool':
                dataframe[col].fillna(False, inplace=True)

    def handle_arrow_keys(self, event):
        """
        Handle arrow keys events.
        :param event: event that triggered the function call.

        Overrided to add new key bindings
        """
        control_pressed = event.state == 4 or event.state & 0x00004 != 0
        # alt_pressed = event.state == 8 or event.state & 0x20000 != 0
        if control_pressed and event.keysym == 'Right':
            self.next_page()
            return 'break'
        elif control_pressed and event.keysym == 'Left':
            self.prev_page()
            return 'break'
        elif control_pressed and event.keysym == 'Up':
            self.prev_row()
            return 'break'
        elif control_pressed and event.keysym == 'Down':
            self.next_row()
            return 'break'
        super().handle_arrow_keys(event)

    def on_header_drag(self, event):
        """
        Handle left mouse button release events.
        :param event: event that triggered the function call.

        Overrided for handle columns reordering.
        Just a placeholder for now.
        """
        # print("header drag")
        self.colheader.handle_mouse_drag(event)  # mandatory to propagate the event in the col headers
        self.is_header_dragged = True

    def on_header_release(self, event):
        """
        Handle left mouse button release events.
        :param event: event that triggered the function call.

        Overrided for handle columns reordering
        Just a placeholder for now.
        """
        self.colheader.handle_left_release(event)  # mandatory to propagate the event in the col headers
        # print(str(event.type))
        # Check if the event is a button release
        if str(event.type) == '5' and self.is_header_dragged:
            # button is release after a drag in the col headers
            self.is_header_dragged = False
            # print("release")
            # not usefull here because the columns are not reodered yet
            # self.update_col_infos()

    def get_selected_row_fixed(self):
        """
        Get currently selected row.
        :return: currently selected row or None if none is selected.

        Notes:
            The original method returns 0 if none is selected OR if the first row is selected
            We don't want to return 0 if the first row is selected
            We don"t override the original method because a changed return type could break the code
        """
        current_row = self.currentrow
        if current_row == 0:
            current_row = self.multiplerowlist[-1] if len(self.multiplerowlist) > 0 else None
        return current_row

    def redraw(self, event=None, callback=None):
        """
        Redraw the table
        :param event: event that triggered the function call.
        :param callback: callback function to call after the table has been redrawn.

        Overrided for debugging
        """
        super().redraw(event, callback)

    def colorRows(self):
        """
        Color individual cells in column(s). Requires that the rowcolors.
        dataframe has been set. This needs to be updated if the index is reset.

        Overrided to check indexes when rebuildind data from en empty table.
        """
        df = self.get_data(df_type=self._dftype_for_coloring)
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

    def setColPositions(self):
        """
        Determine current column grid positions

        Overrided for debugging
        """
        try:
            super().setColPositions()
        except IndexError:
            pass

    def resizeColumn(self, col: int, width: int):
        """
        Resize a column by dragging
        :param col: column to resize.
        :param width: new width of the column.

        Overrided to remove the minimal size and for debugging
        """
        colname = self.model.getColumnName(col)
        # if self.colheader.wrap:
        #     if width < 40:
        #         width = 40
        self.columnwidths[colname] = width
        self.setColPositions()
        self.delete('colrect')
        self._set_with_for_hidden_columns()
        self.redraw()
        # save the new column width in the config file
        new_columns_infos = gui_g.s.get_column_infos(self.data_source_type)
        try:
            new_columns_infos[colname]['width'] = width
            gui_g.s.set_column_infos(new_columns_infos, self.data_source_type)
            gui_g.s.save_config_file()
        except KeyError:
            pass

    # noinspection PyPep8Naming
    def sortTable(self, columnIndex=None, ascending=1, index=False):
        """
        Sort the table by a column.
        :param columnIndex: column to sort.
        :param ascending: 1 for ascending, -1 for descending.
        :param index: True to sort by index, False to sort by column.

        Overrided to allow fixing index_copy column
        """
        # super().sortTable(columnIndex, ascending, index)

        df = self.get_data()
        if columnIndex is None:
            columnIndex = self.multiplecollist
        if isinstance(columnIndex, int):
            columnIndex = [columnIndex]

        if index:
            df.sort_index(inplace=True)
        else:
            colnames = list(df.columns[columnIndex])
            try:
                # noinspection PyTypeChecker
                df.sort_values(by=colnames, inplace=True, ascending=ascending)
            except (Exception, ) as error:
                self.add_error(error)
                self.logger.warning(f'Could not sort the columns. Error: {error!r}')
        self.update_index_copy_column()
        self.update()
        return

    def tableChanged(self) -> None:
        """
        Called when the table is changed.

        Overrided for debugging
        """
        super().tableChanged()
        self.must_save = True
        self.update_controls_state_func()

    def handle_left_release(self, event):
        """
        Handle left mouse button release events.
        :param event: event that triggered the function call.

        Overrided to trap raised error when clicking on an empty row
        """
        try:
            super().handle_left_release(event)
        except IndexError:
            pass

    def handleCellEntry(self, row, col):
        """
        Callback for cell entry

        Overrided for debugging
        """
        # get the value from the MODEL because the value in the datatable could not have been updated yet
        try:
            value_saved = self.get_data(df_type=DataFrameUsed.MODEL).iat[row, col]  # iat checked
        except IndexError:
            value_saved = None
        super().handleCellEntry(row, col)
        self._check_cell_has_changed(value_saved)

    def handleEntryMenu(self, *args):
        """
        Callback for option menu in categorical columns entry

        Overrided for debugging
        """
        # get the value from the MODEL because the value in the datatable could not have been updated yet
        try:
            value_saved = self.get_data(df_type=DataFrameUsed.MODEL).iat[self._last_selected_row, self._last_selected_col]  # iat checked
        except IndexError:
            value_saved = None
        super().handleEntryMenu(*args)
        self._check_cell_has_changed(value_saved)

    def resetColors(self):
        """
        Reset the colors of the cells. Initialize the rowcolors dataframe.

        Notes:
            Overridden for selecting the right datatable to use.
        """
        df = self.get_data(df_type=self._dftype_for_coloring)
        try:
            # index copy column is not always present
            self.rowcolors = pd.DataFrame(index=df[gui_g.s.index_copy_col_name])
        except KeyError:
            self.rowcolors = pd.DataFrame(index=df.index)
        return

    def _set_with_for_hidden_columns(self) -> None:
        """
        Set the with for the hidden columns.
        """
        col_list = [gui_g.s.index_copy_col_name] + gui_g.s.hidden_column_names
        for colname in col_list:
            self.columnwidths[colname] = 2

    def _generate_cell_selection_changed_event(self) -> None:
        """
        Create the event bindings for the table.

        Notes:
            A CellSelectionChanged event is generated if the selected cell has changed.
        """
        selected_row = self.currentrow
        selected_col = self.currentcol
        if (selected_row != self._last_selected_row) or (selected_col != self._last_selected_col):
            self._last_selected_row = selected_row
            self._last_selected_col = selected_col
            self._last_cell_value = self.get_cell(selected_row, selected_col)
            self.event_generate('<<CellSelectionChanged>>')

    def _check_cell_has_changed(self, value_saved) -> bool:
        """
        Check if the cell value has changed. If so, the row is added to the list of changed rows.
        :param value_saved: old value of the cell.
        :return: True if the cell value has changed, False otherwise.
        """
        row = self._last_selected_row
        col = self._last_selected_col
        # new_value = self.get_cell(row, col)
        df_model = self.get_data(df_type=DataFrameUsed.MODEL)  # always used the MODEL here because the user changes are always done in model
        new_value = df_model.iat[row, col]  # iat checked
        if new_value is not None and value_saved != new_value:
            row_index = self.get_real_index(row)
            self.update_cell(row_index, col, new_value, convert_row_number_to_row_index=False)  # copy the value in the unfiltered dataframe
            self.add_to_rows_to_save(row_index)
            # self.tableChanged() # done in add_to_rows_to_save
            return True
        return False

    def is_using_database(self) -> bool:
        """ Check if the table is using a database as data source. """
        return self.data_source_type == DataSourceType.DATABASE

    def set_frm_filter(self, frm_filter=None) -> None:
        """
        Set the filter frame.
        :param frm_filter: filter frame.
        """
        if frm_filter is None:
            raise ValueError('frm_filter can not be None')
        self._frm_filter = frm_filter

    def set_frm_quick_edit(self, frm_quick_edit=None) -> None:
        """
        Set the quick edit frame.
        :param frm_quick_edit: quick edit frame.
        """
        if frm_quick_edit is None:
            raise ValueError('frm_quick_edit can not be None')
        self._frm_quick_edit = frm_quick_edit

    def set_columns_type(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Set the columns format for the table.
        :param df: dataframe to format.
        :return: formatted dataframe.
        """
        # self.logger.info("\nCOL TYPES BEFORE CONVERSION\n")
        # df.info()  # direct print info
        for col in df.columns:
            converters = gui_t.get_converters(col)
            # at least 2 converters are expected: one for the convertion function and one for column type
            for converter in converters:
                try:
                    if callable(converter):
                        df[col] = df[col].apply(converter)  # apply the converter function to the column
                    else:
                        df[col] = df[col].astype(converter)
                except (KeyError, ValueError) as error:
                    self.add_error(error)
                    self.logger.warning(f'Could not convert column "{col}" using {converter}. Error: {error!r}')
        # self.logger.debug("\nCOL TYPES AFTER CONVERSION\n")
        # df.info()  # direct print info
        return df

    def get_col_infos(self) -> dict:
        """
        GHet the current column infos sorted
        :return: current column infos sorted by position.

        Notes:
            The config file is not saved here.
        """
        col_infos = {}
        for index, col in enumerate(self.model.df.columns):  # df.model checked
            col_infos[col] = {}
            col_infos[col]['width'] = self.columnwidths.get(col, -1)  # -1 means default width. Still save the value to
            col_infos[col]['pos'] = index
        sorted_cols_by_pos = dict(sorted(col_infos.items(), key=lambda item: item[1]['pos']))
        if gui_g.s.index_copy_col_name not in sorted_cols_by_pos:
            # add the index_copy column to sorted cols list at the last position if missing
            sorted_cols_by_pos[gui_g.s.index_copy_col_name] = {'width': -1, 'pos': len(sorted_cols_by_pos)}
        return sorted_cols_by_pos

    def update_col_infos(self, updated_info: dict = None, apply_resize_cols: bool = True):
        """
        Update the column infos in the config file.
        :param updated_info: updated column infos.
        :param apply_resize_cols: True to apply the new column width, False otherwise.

        Notes:
            The config file is not saved here.
        """
        if updated_info is None:
            updated_info = self.get_col_infos()
        gui_g.s.set_column_infos(updated_info, self.data_source_type)
        if apply_resize_cols:
            self.resize_columns()

    def get_real_index(self, row_number: int, df_type: DataFrameUsed = DataFrameUsed.AUTO, add_page_offset: bool = True) -> int:
        """
        Get the real row index for a row number from the value saved in the 'Index copy' column.
        :param row_number: row number from a datatable. Will be converted into real row index.
        :param df_type: dataframe type to get. See DataFrameUsed type description for more details.
        :param add_page_offset: True to add the page offset to the row number, False otherwise.
        :return: real row index or -1 if not found.
        """
        # OLD if row_number < 0 or row_number == '':
        if row_number < 0:
            return -1
        if add_page_offset:
            row_number = self.add_page_offset(row_number)
        # get the REAL index of the row from its backup
        if df_type == DataFrameUsed.AUTO:
            if self.is_filtered:
                df = self.df_filtered
            else:
                df = self.df_unfiltered
        elif df_type == DataFrameUsed.UNFILTERED:
            df = self.df_unfiltered
        elif df_type == DataFrameUsed.FILTERED:
            df = self.df_filtered
        elif df_type == DataFrameUsed.MODEL:
            df = self.model.df
        elif df_type == DataFrameUsed.BOTH:
            self.logger.warning('The df_type parameter can not be "DataFrameUsed.BOTH" in that case. Using "DataFrameUsed.AUTO" instead.')
            return int(self.get_real_index(row_number))
        else:
            return int(self.get_real_index(row_number))
        # copy_col_index = self.get_col_index(gui_g.s.index_copy_col_name)  # issue if df and unfiltred data does not have the same columns
        copy_col_index = df.columns.get_loc(gui_g.s.index_copy_col_name)
        result = -1
        idx_max = len(df)
        if row_number >= idx_max:
            return -1
        try:
            idx = df.index[row_number]
            result = int(idx)
            if copy_col_index >= 0:
                idx_copy = df.iat[row_number, copy_col_index]  # could return '' if the column is empty
                result = int(idx_copy) if str(idx_copy) else -1
            else:
                self.logger.warning(f'Column "{gui_g.s.index_copy_col_name}" not found in the table. We use the row number instead.')
        except (ValueError, IndexError) as error:
            self.add_error(error)
            self.logger.warning(f'Could not get the real index for row number #{row_number + 1}. Error: {error!r}')
        return result

    def get_data(self, df_type: DataFrameUsed = DataFrameUsed.UNFILTERED) -> pd.DataFrame:
        """
        Get a dataframe content depending on the df_type parameter. By default, the unfiltered dataframe is returned.
        :param df_type: dataframe type to get. See DataFrameUsed type description for more details.
        :return: dataframe.

        Notes:
            The unfiltered dataframe must be returned by default because it's used in by the FilterFrame class.
        """
        if df_type == DataFrameUsed.AUTO:
            if self.is_filtered:
                return self.df_filtered
            else:
                return self.df_unfiltered
        elif df_type == DataFrameUsed.UNFILTERED:
            return self.df_unfiltered
        elif df_type == DataFrameUsed.FILTERED:
            return self.df_filtered
        elif df_type == DataFrameUsed.MODEL:
            return self.model.df
        elif df_type == DataFrameUsed.BOTH:
            self.logger.warning('The df_type parameter can not be "DataFrameUsed.BOTH" in that case. Using "DataFrameUsed.AUTO" instead.')
            return self.get_data(df_type=DataFrameUsed.AUTO)

    def set_data(self, df: pd.DataFrame, df_type: DataFrameUsed = DataFrameUsed.UNFILTERED) -> None:
        """
        Set a dataframe content depending on the df_type parameter. By default, the unfiltered dataframe is used.
        :param df: dataframe content to set.
        :param df_type: dataframe type to set. See DataFrameUsed type description for more details.
        """
        if df_type == DataFrameUsed.AUTO:
            if self.is_filtered:
                self.df_filtered = df
            else:
                self.df_unfiltered = df
        elif df_type == DataFrameUsed.UNFILTERED:
            self.df_unfiltered = df
        elif df_type == DataFrameUsed.FILTERED:
            self.df_filtered = df
        elif df_type == DataFrameUsed.BOTH:
            self.df_unfiltered = df
            self.df_filtered = df
        elif df_type == DataFrameUsed.MODEL:
            self.model.df = df
            # self.logger.error("The df_type parameter can't be DataFrameUsed.MODEL in that case. THIS MUST NOT OCCUR. Exiting application...")
            # previous line will quit the application

    def resize_columns(self) -> None:
        """
        Resize and reorder the columns of the table.
        """
        column_infos = gui_g.s.get_column_infos(self.data_source_type)
        column_infos_len = len(column_infos)
        if column_infos_len <= 0:
            return
        df = self.get_data(DataFrameUsed.UNFILTERED)
        column_len = len(df.columns)
        diff_len = column_infos_len - column_len
        if diff_len > 1:  # the difference could be 0 or 1 depending on the index_copy column has been added to the datatable
            gui_f.box_message(
                f'The number of columns in data source ({column_len}) does not match the number of values in "column_infos" from the config file ({column_infos_len}).\nA backup of the current config file has been made.\nNormally, this will be fixed automatically on quit.\nIf not, please check the config file.'
            )
        # just for debugging
        col_list = column_infos.copy().keys()
        for col in col_list:
            if col not in df.columns and col != gui_g.s.index_copy_col_name:
                self.logger.warning(f'Column "{col}" is in column_infos BUT not in the datatable. It has been removed from column_infos.')
                # remove col from dict column_infos
                column_infos.pop(col)
        for col in df.columns:
            if col not in column_infos.keys() and col != gui_g.s.index_copy_col_name:
                self.logger.info(f'Column "{col}" is in the datatable BUT not in column_infos.')
        try:
            # Add columns to column_infos that are not already present, with a width of 2
            pos = column_infos_len
            for col in df.columns:
                if col not in column_infos:
                    column_infos[str(col)] = {'width': 2, 'pos': pos}
                    pos += 1

            # Update position for an unordered and hidden columns
            max_pos = column_infos_len
            for col, info in column_infos.items():
                pos = info['pos']
                width = info['width']
                if pos > max_pos:
                    max_pos = pos
                elif pos < 0 or width == 2:  # hidden column
                    max_pos += 1
                    column_infos[col]['pos'] = max_pos
            column_infos[gui_g.s.index_copy_col_name] = {'pos': max_pos + 1, 'width': 2}  # always put 'Index copy' col at the end

            # Reorder columns based on position
            if 'pos' not in column_infos[next(iter(column_infos))]:
                # Old format without the 'pos' key
                keys_ordered = column_infos.keys()
            else:
                # Sort by position
                sorted_cols_by_pos = dict(sorted(column_infos.items(), key=lambda item: item[1]['pos']))
                # Set new positions
                for i, (col, info) in enumerate(sorted_cols_by_pos.items()):
                    info['pos'] = i
                # Save the new column_infos in the config file
                gui_g.s.set_column_infos(sorted_cols_by_pos, self.data_source_type)
                gui_g.s.save_config_file()
                keys_ordered = sorted_cols_by_pos.keys()

            # reorder columns
            df = df.reindex(columns=keys_ordered, fill_value='')
            self.set_data(df, DataFrameUsed.UNFILTERED)
            df = self.get_data(DataFrameUsed.MODEL).reindex(columns=keys_ordered, fill_value='')
            self.set_data(df, DataFrameUsed.MODEL)
            self.columns_saved_str = gui_fn.check_and_convert_list_to_str(df.columns.values)
            df = self.get_data(DataFrameUsed.FILTERED)
            if df is not None:
                df.reindex(columns=keys_ordered, fill_value='')  # reorder columns
                self.set_data(df, DataFrameUsed.FILTERED)
        except KeyError:
            self.logger.warning('Error when reordering the columns.')
        else:
            try:
                # resizing columns
                for colname, info in column_infos.items():
                    width = int(info.get('width', -1))
                    if width > 0:
                        self.columnwidths[colname] = width
            except KeyError:
                self.logger.warning('Error when resizing the columns.')
        self._set_with_for_hidden_columns()
        self.setColPositions()
        self.redraw()

    def add_page_offset(self, value: int = None, remove_offset: bool = False) -> int:
        """
        Return the "valid" row index depending on the context. It takes into account the pagination and the current page.
        :param value: value to add or remove offset to. It could be a row number or a row index. If None, the selected row number will be used.
        :param remove_offset: whether the offset is removed from the row index. If False, the offset is added to the row index.
        :return: row index with a correct offset.
        """
        if value is None:
            value = self.currentrow

        if self.pagination_enabled:
            offset = self.rows_per_page * (self.current_page - 1)
            if remove_offset:
                value -= offset
            else:
                value += offset

        return value

    def valid_source_type(self, filename: str) -> bool:
        """
        Check if the file extension is valid for the current data source type.
        :param filename: filename to check.
        :return: True if the file extension is valid for the current data source type, False otherwise.
        """
        file, ext = os.path.splitext(filename)
        type_saved = self.data_source_type
        self.data_source_type = DataSourceType.DATABASE if ext == '.db' else DataSourceType.FILE
        go_on = True
        if type_saved != self.data_source_type:
            go_on = gui_f.box_yesno(
                f'The type of data source has changed from the previous one.\nYou should quit and restart the application to avoid any data loss.\nAre you sure you want to continue ?'
            )
        return go_on

    def read_data(self) -> pd.DataFrame:
        """
        Load data from the specified CSV file or database.
        :return: data loaded from the file.
        """
        self.must_rebuild = False
        if not self.valid_source_type(self.data_source):
            # noinspection PyTypeChecker
            return None
        try:
            if self.data_source_type == DataSourceType.FILE:
                df = pd.read_csv(self.data_source, **gui_g.s.csv_options)
                data_count = len(df)  # model. df checked
                if data_count <= 0 or df.iat[0, 0] is None:  # iat checked
                    self.logger.warning(f'Empty file: {self.data_source}. Adding a dummy row.')
                    df, _ = self.create_row(add_to_existing=False)
            elif self.is_using_database():
                if self._db_handler is None:
                    # could occur after a call to self.valid_source_type()
                    self._db_handler = UEAssetDbHandler(database_name=self.data_source)
                data = self._db_handler.get_assets_data_for_csv()
                column_names: list = self._db_handler.get_columns_name_for_csv()
                col_index = column_names.index('Uid')
                data_count = len(data)
                # check to see if the first row has a value in the Uid column
                if data_count <= 0 or data[0][col_index] is None:
                    self.logger.warning(f'Empty file: {self.data_source}. Adding a dummy row.')
                    df, _ = self.create_row(add_to_existing=False)
                else:
                    df = pd.DataFrame(data, columns=column_names)
                # use the
            else:
                self.logger.error(f'Unknown data source type: {self.data_source_type}')
                # previous line will quit the application
                # noinspection PyTypeChecker
                return None
        except EmptyDataError:
            self.logger.warning(f'Empty file: {self.data_source}. Adding a dummy row.')
            df, _ = self.create_row(add_to_existing=False)
            data_count = len(df)
        if df is None or df.empty:
            self.logger.error(f'No data found in data source: {self.data_source}')
            # previous line will quit the application
            # noinspection PyTypeChecker
            return None
        else:
            self.df_unfiltered = df
            self.total_pages = (data_count - 1) // self.rows_per_page + 1
            return df

    def create_row(self, row_data=None, add_to_existing: bool = True, do_not_save: bool = False) -> (pd.DataFrame, int):
        """
        Create an empty row in the table.
        :param row_data: data to add to the row.
        :param add_to_existing: True to add the row to the existing data, False to replace the existing data.
        :param do_not_save: True to not save the row in the database.
        :return: (The created row, the index of the created row).

        Notes:
            Be sure to call self.update() after calling this function to copy the changes in all the dataframes.
        """
        table_row = None
        new_index = 0
        df = self.get_data()
        if self.data_source_type == DataSourceType.FILE:
            # create an empty row with the correct columns
            col_data = gui_t.get_csv_field_name_list(return_as_string=True)  # column names
            str_data = col_data + '\n' + gui_t.create_empty_csv_row(return_as_string=True)  # dummy row
            table_row = pd.read_csv(io.StringIO(str_data), usecols=col_data.split(','), nrows=1, **gui_g.s.csv_options)
        elif self.is_using_database():
            # create an empty row (in the database) with the correct columns
            data = self._db_handler.create_empty_row(return_as_string=False, do_not_save=do_not_save)  # dummy row
            column_names = self._db_handler.get_columns_name_for_csv()
            table_row = pd.DataFrame(data, columns=column_names, index=[new_index])
            try:
                table_row[gui_g.s.index_copy_col_name] = new_index
            except KeyError:
                self.logger.warning(f'Could not add column "{gui_g.s.index_copy_col_name}" to the row')
        else:
            self.logger.error(f'Unknown data source type: {self.data_source_type}')
            # previous line will quit the application
        if table_row is None:
            self.logger.warning(f'Could not create an empty row for data source: {self.data_source}')
            return None, -1
        if row_data is not None:
            # add the data to the row
            for col in row_data:
                table_row[col] = row_data[col]
        if add_to_existing and table_row is not None:
            self.must_rebuild = False
            if new_index == 0:
                # the row is added at the start of the table. As it, the index is always known
                new_df = pd.concat([table_row, df], copy=False, ignore_index=True)
            else:
                # the row is added at the end
                new_df = pd.concat([df, table_row], copy=False, ignore_index=True)
            self.set_data(new_df)
            self.add_to_rows_to_save(new_index)  # done inside self.must_save = True
        elif table_row is not None:
            self.must_rebuild = True
        # table_row.fillna(gui_g.s.empty_cell, inplace=True)   # cause a FutureWarning
        # self.fillna_fixed(table_row)
        return table_row, new_index

    def del_rows(self, row_numbers=None, convert_to_index=True, confirm_dialog=True) -> bool:
        """
        Delete rows from the table.
        :param row_numbers: row to delete. If None, the selected row is deleted.
        :param convert_to_index: True to convert the row number to the real index, False otherwise.
        :param confirm_dialog: True to display a confirmation dialog, False otherwise.

        Notes:
            self.tableChanged() is called if some rows have been deleted
        """
        if row_numbers is None:
            row_numbers = self.multiplerowlist
        if isinstance(row_numbers, list):
            asset_str = f'{len(row_numbers)} rows'
            row_numbers.sort(reverse=True)  # delete from the end to the start to avoid index change
        else:
            asset_str = f' row #{row_numbers + 1}'
            row_numbers = [row_numbers]
        if not confirm_dialog or gui_f.box_yesno(f'Are you sure you want to delete {asset_str}? '):
            index_to_delete = []
            for row_number in row_numbers:
                df = self.get_data()
                asset_id = gui_g.s.cell_is_empty_list[0]
                idx = self.get_real_index(int(row_number), add_page_offset=True) if convert_to_index else row_number
                if 0 <= idx <= len(df):
                    try:
                        asset_id = df.at[idx, 'Asset_id']  # at checked
                        index_to_delete.append(idx)
                        self.add_to_asset_ids_to_delete(asset_id)
                        self.logger.info(f'Adding row index {idx} with asset_id={asset_id} to the list of index to delete')
                    except (IndexError, KeyError) as error:
                        self.add_error(error)
                        self.logger.warning(f'Could add row index {idx} with asset_id={asset_id} to the list of index to delete. Error: {error!r}')

                    # update the index copy column because index is changed after each deletion
                    df[gui_g.s.index_copy_col_name] = df.index
                    check_asset_id = df.at[idx, 'Asset_id']
                    # done one by on to check if the asset_id is still OK
                    if check_asset_id not in self._deleted_asset_ids:
                        self.logger.error(f'The row to delete with asset_id={check_asset_id} is not the good one')
                    else:
                        try:
                            df.drop(idx, inplace=True)
                            # next changes will be done in self.update()
                            # self.model.df.drop(idx, inplace=True)
                            # if self.df_filtered is not None:
                            #    self.df_filtered.drop(idx, inplace=True)
                        except (IndexError, KeyError) as error:
                            self.add_error(error)
                            self.logger.warning(f'Could not perform the deletion of list of indexes. Error: {error!r}')

            self.selectNone()
            self.update_index_copy_column()
            number_deleted = len(index_to_delete)
            if number_deleted:
                cur_row = self.getSelectedRow()
                if cur_row < number_deleted:
                    # move to the next row
                    self.move_to_row(cur_row)
                else:
                    # or move to the prev row of the first deleted row
                    self.move_to_row(cur_row - number_deleted)
                # self.redraw() # DOES NOT WORK need a self.update() to copy the changes to model. df AND to self.filtered_df
                self.update()
                self.tableChanged()
            return number_deleted > 0
        else:
            return False

    def save_data(self, source_type: DataSourceType = None) -> None:
        """
        Save the current table data to the CSV file.
        """
        if source_type is None:
            source_type = self.data_source_type
        df = self.get_data(df_type=DataFrameUsed.AUTO)
        self.updateModel(TableModel(df))  # needed to restore all the data and not only the current page
        if source_type == DataSourceType.FILE:
            df.to_csv(self.data_source, index=False, na_rep='', date_format=DateFormat.csv)
        else:
            for row_number in self._changed_rows:
                row_data = self.get_row(row_number, return_as_dict=True)
                if row_data is None:
                    continue
                _id = row_data.get('Asset_id', '')
                if _id.startswith(gui_g.s.temp_id_prefix):
                    # this a new row , partialled empty, created before scraping the data.
                    # No need to save it, It will produce a database error.
                    # It will be saved after scraping
                    if len(self._changed_rows) > 1:
                        continue
                    else:
                        self.must_save = False
                        return
                asset_id = row_data.get('Asset_id', '')
                if asset_id in gui_g.s.cell_is_empty_list and _id in gui_g.s.cell_is_empty_list:
                    self.logger.warning(f'The asset for row #{row_number + 1} is missing asset_id or if field value. Bypassing the save.')
                    continue
                if asset_id in self._deleted_asset_ids:
                    # do not update an asset if that will be deleted
                    continue
                # convert the key names to the database column names
                asset_data = gui_t.convert_csv_row_to_sql_row(row_data)
                ue_asset = UEAsset()
                try:
                    ue_asset.init_from_dict(asset_data)
                    # update the row in the database
                    tags = ue_asset.get('tags', [])
                    tags_str = self._db_handler.convert_tag_list_to_string(tags)
                    ue_asset.set('tags', tags_str)
                    self._db_handler.save_ue_asset(ue_asset)
                    asset_id = ue_asset.get('asset_id', '')
                    self.logger.info(f'UE_asset ({asset_id}) for row #{row_number + 1} has been saved to the database')
                except (KeyError, ValueError, AttributeError) as error:
                    self.add_error(error)
                    self.logger.warning(f'Failed to save UE_asset for row #{row_number + 1} to the database. Error: {error!r}')
            for asset_id in self._deleted_asset_ids:
                try:
                    # delete the row in the database
                    self._db_handler.delete_asset(asset_id=asset_id)
                    self.logger.info(f'Row with asset_id={asset_id} has been deleted from the database')
                except (KeyError, ValueError, AttributeError) as error:
                    self.add_error(error)
                    self.logger.warning(f'Failed to delete asset_id={asset_id} to the database. Error: {error!r}')

        self.clear_rows_to_save()
        self.clear_asset_ids_to_delete()
        self.must_save = False
        self.update_page()

    def update_downloaded_size(self, asset_sizes: dict) -> None:
        """
        Update the downloaded size for the assets in the table using the asset_sizes dictionnary (filled at start up)
        :param asset_sizes: asset_sizes.
        """
        if asset_sizes:
            df = self.get_data(df_type=DataFrameUsed.UNFILTERED)
            # update the downloaded_size field in the datatable using asset_id as key
            for asset_id, size in asset_sizes.items():
                try:
                    size = int(size)
                    size = gui_fn.format_size(size) if size > 1 else gui_g.s.unknown_size  # convert size to readable text
                    df.loc[df['Asset_id'] == asset_id, 'Downloaded size'] = size
                    # print(f'asset_id={asset_id} size={size}')
                except KeyError:
                    pass
            # self.editable_table.set_data(df, df_type=DataFrameUsed.UNFILTERED)

    def reload_data(self, asset_sizes: dict) -> bool:
        """
        Reload data from the CSV file and refreshes the table display.
        :param asset_sizes: asset_sizes.
        :return: True if the data has been loaded successfully, False otherwise.
        """
        gui_f.show_progress(self, text='Reloading Data from data source...')
        df_loaded = self.read_data()  # fill the UNFILTERED dataframe
        if df_loaded is None:
            return False
        self.set_data(df_loaded)
        self.update_downloaded_size(asset_sizes)
        self.update(update_format=True)  # this call will copy the changes to model. df AND to self.filtered_df
        # mf.close_progress(self)  # done in data_table.update(update_format=True)
        return True

    def rebuild_data(self, asset_sizes: dict) -> bool:
        """
        Rebuild the data in the table.
        :param asset_sizes: asset_sizes.
        :return: True if the data was successfully rebuilt, False otherwise.
        """
        self.clear_rows_to_save()
        self.clear_asset_ids_to_delete()
        self.must_save = False
        use_database = self.is_using_database()
        message = 'Rebuilding Data For database...' if use_database else 'Rebuilding Data For CSV file...'
        pw = gui_f.show_progress(self, message, force_new_window=True)
        # we create the progress window here to avoid lots of imports in UEAssetScraper class
        max_threads = get_max_threads()
        owned_assets_only = False
        scraped_assets_per_page = gui_g.s.scraped_asset_per_page  # a bigger value will be refused by UE API
        if gui_g.s.testing_switch == 1:
            start_row = 15000
            stop_row = 15000 + scraped_assets_per_page * 5
        else:
            start_row = 0
            stop_row = 0
        if gui_g.s.offline_mode:
            load_from_files = True
        else:
            if gui_g.UEVM_cli_args and gui_g.UEVM_cli_args.get('force_refresh', False):
                load_from_files = False
            else:
                load_from_files = gui_g.UEVM_cli_args.get('offline', True)
        scraper = UEAssetScraper(
            datasource_filename=self.data_source,
            use_database=use_database,
            start=start_row,
            stop=stop_row,
            assets_per_page=scraped_assets_per_page,
            max_threads=max_threads,
            save_parsed_to_files=True,
            load_from_files=load_from_files,
            store_ids=False,  # useless for now
            clean_database=False,
            progress_window=pw,
            core=None if gui_g.UEVM_cli_ref is None else gui_g.UEVM_cli_ref.core,
        )
        scraper.clear_ignored_asset_names()

        result_count = 0
        if not load_from_files:
            result_count = scraper.gather_all_assets_urls(owned_assets_only=owned_assets_only)  # return -1 if interrupted or error
        if result_count == -1:
            gui_f.close_progress(self)
            return False
        if scraper.save(owned_assets_only=owned_assets_only):
            self.current_page = 1
            df_loaded = self.read_data()
            if df_loaded is None:
                gui_f.close_progress(self)
                return False
            self.set_data(df_loaded)
            self.update_downloaded_size(asset_sizes)
        self.update(update_format=True)  # this call will copy the changes to model. df AND to self.filtered_df
        # gui_f.close_progress(self)  # done in data_table.update(update_format=True)
        return True

    def gradient_color_cells(
        self, col_names: [] = None, cmap: str = 'blues', alpha: float = 1, min_val=None, max_val=None, is_reversed: bool = False
    ) -> None:
        """
        Create a gradient color for the cells os specified columns. The gradient depends on the cell value between min and max values for that column.
        :param col_names: names of the columns to create a gradient color for.
        :param cmap: name of the colormap to use.
        :param alpha: alpha value for the color.
        :param min_val: minimum value to use for the gradient. If None, the minimum value of each column is used.
        :param max_val: maximum value to use for the gradient. If None, the maximum value of each column is used.
        :param is_reversed: True to reverse the gradient, False otherwise.

        Notes:
            Called by set_colors() on each update
        """
        if col_names is None:
            return
        df = self.get_data(df_type=self._dftype_for_coloring)
        for col_name in col_names:
            try:
                x = df[col_name]
                if min_val is None:
                    min_val = x.min()
                if max_val is None:
                    max_val = x.max()
                x = (x - min_val) / (max_val - min_val)
                if is_reversed:
                    x = max_val - x
                clrs = self.values_to_colors(x, cmap, alpha)
                clrs = pd.Series(clrs, index=df.index)
                rc = self.rowcolors
                rc[col_name] = clrs
            except (KeyError, ValueError, TypeError) as error:
                self.add_error(error)
                self.logger.debug(f'gradient_color_cells: An error as occured with {col_name} : {error!r}')
                continue

    def setColorByMask(self, col, mask, clr):
        """Color individual cells in a column using a mask."""
        if len(self.rowcolors) == 0:
            self.resetColors()
        rc = self.rowcolors
        if col not in rc.columns:
            rc[col] = pd.Series()
        try:
            rc[col] = rc[col].where(-mask, clr)
        except (KeyError, ValueError) as error:
            self.add_error(error)
            self.logger.debug(f'setColorByMask: An error as occured with {col} : {error!r}')
        return

    def color_cells_if(self, col_names: [] = None, color: str = 'green', value_to_check: any = True) -> None:
        """
        Set the cell color for the specified columns and the cell with a given value.
        :param col_names: name of the columns to color if the value is found.
        :param color: color to set the cell to.
        :param value_to_check: value to check for.

        Notes:
            Called by set_colors() on each update
        """
        if col_names is None:
            return
        df = self.get_data(df_type=self._dftype_for_coloring)
        for col_name in col_names:
            mask = df[col_name] == value_to_check
            try:
                self.setColorByMask(col=col_name, mask=mask, clr=color)
            except (KeyError, ValueError) as error:
                self.add_error(error)
                self.logger.debug(f'color_cells_if: An error as occured with {col_name} : {error!r}')

    def color_cells_if_not(self, col_names: [] = None, color: str = 'grey', value_to_check: any = False) -> None:
        """
        Set the cell color for the specified columns and the cell with NOT a given value.
        :param col_names: name of the columns to color if the value is not found.
        :param color: color to set the cell to.
        :param value_to_check: value to check for.

        Notes:
            Called by set_colors() on each update
        """
        if col_names is None:
            return
        df = self.get_data(df_type=self._dftype_for_coloring)
        for col_name in col_names:
            try:
                mask = df[col_name] != value_to_check
                self.setColorByMask(col=col_name, mask=mask, clr=color)
            except (KeyError, ValueError) as error:
                self.add_error(error)
                self.logger.debug(f'color_cells_if_not: An error as occured with {col_name} : {error!r}')
                continue

    def color_rows_if(self, col_name_to_check: str, color: str = '#555555', value_to_check: any = True) -> None:
        """
        Set the row color for the specified columns and the rows with a given value.
        :param col_name_to_check: name of the column to check for the value.
        :param color: color to set the row to.
        :param value_to_check: value to check for.

        Notes:
            Called by set_colors() on each update
        """

        df = self.get_data(df_type=self._dftype_for_coloring)
        mask = df[col_name_to_check] == value_to_check
        for col_name in df.columns:
            try:
                self.setColorByMask(col=col_name, mask=mask, clr=color)
            except (KeyError, ValueError) as error:
                self.add_error(error)
                self.logger.debug(f'color_rows_if: An error as occured with {col_name} : {error!r}')

    def set_preferences(self, default_pref=None) -> None:
        """
        Initialize the table preferences.
        :param default_pref: default preferences to apply to the table.
        """
        # remove the warning: "A value is trying to be set on a copy of a slice from a DataFrame"
        # when sorting the table with pagination enabled
        # see: https://stackoverflow.com/questions/20625582/how-to-deal-with-settingwithcopywarning-in-pandas
        pd.options.mode.chained_assignment = None
        if default_pref is not None:
            config.apply_options(default_pref, self)

    def set_colors(self) -> None:
        """
        Initialize the colors of some cells depending on their values.
        """
        """
        import pylab as plt
        cmaps = sorted(m for m in plt.cm.datad)
        print(cmaps)
        
        possible cmaps (exemples: https://matplotlib.org/stable/tutorials/colors/colormaps.html):
        'Accent', 'Accent_r', 'Blues', 'Blues_r', 'BrBG', 'BrBG_r', 'BuGn', 'BuGn_r', 'BuPu', 'BuPu_r', 'CMRmap', 
        'CMRmap_r', 'Dark2', 'Dark2_r', 'GnBu', 'GnBu_r', 'Greens', 'Greens_r', 'Greys', 'Greys_r', 'OrRd', 'OrRd_r',
        'Oranges', 'Oranges_r', 'PRGn', 'PRGn_r', 'Paired', 'Paired_r', 'Pastel1', 'Pastel1_r', 'Pastel2', 
        'Pastel2_r', 'PiYG', 'PiYG_r', 'PuBu', 'PuBuGn', 'PuBuGn_r', 'PuBu_r', 'PuOr', 'PuOr_r', 'PuRd', 'PuRd_r', 
        'Purples', 'Purples_r', 'RdBu', 'RdBu_r', 'RdGy', 'RdGy_r', 'RdPu', 'RdPu_r', 'RdYlBu', 'RdYlBu_r', 
        'RdYlGn', 'RdYlGn_r', 'Reds', 'Reds_r', 'Set1', 'Set1_r', 'Set2', 'Set2_r', 'Set3', 'Set3_r', 'Spectral', 
        'Spectral_r', 'Wistia', 'Wistia_r', 'YlGn', 'YlGnBu', 'YlGnBu_r', 'YlGn_r', 'YlOrBr', 'YlOrBr_r', 'YlOrRd',
        'YlOrRd_r', 'afmhot', 'afmhot_r', 'autumn', 'autumn_r', 'binary', 'binary_r', 'bone', 'bone_r', 'brg', 
        'brg_r', 'bwr', 'bwr_r', 'cividis', 'cividis_r', 'cool', 'cool_r', 'coolwarm', 'coolwarm_r', 'copper', 
        'copper_r', 'cubehelix', 'cubehelix_r', 'flag', 'flag_r', 'gist_earth', 'gist_earth_r', 'gist_gray', 
        'gist_gray_r', 'gist_heat', 'gist_heat_r', 'gist_ncar', 'gist_ncar_r', 'gist_rainbow', 'gist_rainbow_r', 
        'gist_stern', 'gist_stern_r', 'gist_yarg', 'gist_yarg_r', 'gnuplot', 'gnuplot2', 'gnuplot2_r', 'gnuplot_r',
        'gray', 'gray_r', 'hot', 'hot_r', 'hsv', 'hsv_r', 'inferno', 'inferno_r', 'jet', 'jet_r', 'magma', 
        'magma_r', 'nipy_spectral', 'nipy_spectral_r', 'ocean', 'ocean_r', 'pink', 'pink_r', 'plasma', 'plasma_r',
        'prism', 'prism_r', 'rainbow', 'rainbow_r', 'seismic', 'seismic_r', 'spring', 'spring_r', 'summer', 
        'summer_r', 'tab10', 'tab10_r', 'tab20', 'tab20_r', 'tab20b', 'tab20b_r', 'tab20c', 'tab20c_r', 'terrain', 
        'terrain_r', 'turbo', 'turbo_r', 'twilight', 'twilight_r', 'twilight_shifted', 'twilight_shifted_r', 
        'viridis', 'viridis_r', 'winter', 'winter_r'
        
        list of color names: https://matplotlib.org/stable/gallery/color/named_colors.html
        """
        if not gui_g.s.use_colors_for_data:
            self.redraw()
            return
        # self.logger.debug('set_colors')
        self.gradient_color_cells(col_names=['Review'], cmap='cool_r', alpha=1, min_val=0, max_val=5)
        self.color_cells_if(col_names=['Owned', 'Discounted'], color='palegreen', value_to_check=True)
        self.color_cells_if(col_names=['Grab result'], color='skyblue', value_to_check='NO_ERROR')
        self.color_cells_if_not(col_names=['Status'], color='darkgrey', value_to_check='ACTIVE')
        self.color_rows_if(col_name_to_check='Status', color='darkgrey', value_to_check='SUNSET')
        self.color_rows_if(col_name_to_check='Obsolete', color='dimgrey', value_to_check=True)
        self.color_cells_if_not(col_names=['Downloaded size'], color='palegreen', value_to_check='')
        self.redraw()

    def handle_left_click(self, event) -> None:
        """
        Handls left-click events on the table.
        :param event: event that triggered the function call.
        """
        super().handle_left_click(event)
        self._generate_cell_selection_changed_event()

    def handle_right_click(self, event) -> None:
        """
        Handle right-click events on the table.
        :param event: event that triggered the function call.
        """
        super().handle_right_click(event)
        self._generate_cell_selection_changed_event()

    def update_index_copy_column(self) -> None:
        """
        Update the index copy column for the 3 dataframes. Must be called when rows are added or deleted
        """
        self.df_unfiltered.reset_index(drop=True, inplace=True)
        self.df_unfiltered[gui_g.s.index_copy_col_name] = self.df_unfiltered.index
        if self.df_filtered is not None:
            self.df_filtered[gui_g.s.index_copy_col_name] = self.df_filtered.index
        if self.model.df is not None:
            self.model.df[gui_g.s.index_copy_col_name] = self.model.df.index

    def update(self, reset_page: bool = False, update_format: bool = False) -> None:
        """
        Display the specified page of the table data.*
        :param reset_page: whether to reset the current page to 1.
        :param update_format: whether to update the table format.
        """
        self._column_infos_saved = self.get_col_infos()  # stores col infos BEFORE self.model.df is updated
        df = self.get_data()
        self.is_filtered = False
        if update_format:
            # Done here because the changes in the unfiltered dataframe will be copied to the filtered dataframe
            gui_f.show_progress(self, text='Formating and converting DataTable...', keep_existing=True)
            self.set_data(self.set_columns_type(df))
            self.fillna_fixed(df)
            # df.fillna(gui_g.s.empty_cell, inplace=True)  # cause a FutureWarning
        loaded_filter = self._frm_filter.loaded_filter if self._frm_filter is not None else None
        if loaded_filter:
            try:
                ftype = loaded_filter.ftype
                filter_value = loaded_filter.value
                if str(ftype).lower() in ('callable', 'method') and filter_value:
                    # filter_value is a string with a function to call and some parameters
                    # that returns a mask (boolean Series)
                    func_name, func_params = gui_f.parse_callable(filter_value)
                    # get the method to call from the _frm_filter.callable class
                    method = self._frm_filter.callable.get_method(func_name)
                    if method is None:
                        raise AttributeError(f'Could not find the method {func_name} in the class {self._frm_filter.callable.__class__.__name__}')
                    # noinspection PyUnusedLocal
                    mask_from_callable = method(*func_params)
                    query = '@mask_from_callable'  # with pandas, we can pass a reference to a mask to execute a query !!!!
                else:
                    query = filter_value
                if query:
                    self.is_filtered = True
                    df_queried = df.query(query)
                    self.set_data(df_queried, df_type=DataFrameUsed.FILTERED)
            except (AttributeError, IndexingError):
                self.logger.warning(f'Error with defined filters. Updating filter...')
                self._frm_filter.clear_filters()
                self.set_data(df, df_type=DataFrameUsed.FILTERED)
        # if not self.is_filtered:
        #     self.set_data(df, df_type=DataFrameUsed.FILTERED)
        self.model.df = self.get_data(df_type=DataFrameUsed.AUTO)
        if update_format:
            self.update_index_copy_column()
            gui_f.close_progress(self)
        if reset_page:
            self.current_page = 1
            self.update_preview_info_func()
        if self._is_filtered_saved != self.is_filtered:
            self.resetColors()
        self.update_page(keep_col_infos=True)

    def filter_search(self, *args) -> pd.Series:
        """
        Create a mask to filter the data where a columns (or 'all') contains a value. Search is case-insensitive.
        :param args: list of parameters.
        :return: mask to filter the data.

        Notes:
            args: list with the following values in order:
                the column name to search in. If 'all', search in all columns.
                the value to search for.
        """
        col_name = args[0]
        value = args[1]
        df = self.get_data(df_type=DataFrameUsed.UNFILTERED)
        mask = df[col_name].str.contains(value, case=False)
        return mask

    def update_page(self, keep_col_infos=False) -> None:
        """
        Update the page.
        """
        if not keep_col_infos:
            self._column_infos_saved = self.get_col_infos()  # stores col infos BEFORE self.model.df is updated
        df = self.get_data(df_type=DataFrameUsed.AUTO)
        try:
            # self.model could be None before load_data is called
            if self.pagination_enabled:
                self.total_pages = (len(df) - 1) // self.rows_per_page + 1
                start = (self.current_page - 1) * self.rows_per_page
                end = start + self.rows_per_page
                self.model.df = df.iloc[start:end]  # model. df checked iloc checked
            else:
                # Update table with all data
                self.model.df = df  # model. df checked
                self.current_page = 1
                self.total_pages = 1
        except IndexError:
            self.current_page = 1
        # backup index value
        self.df_unfiltered[gui_g.s.index_copy_col_name] = self.df_unfiltered.index
        self.model.df[gui_g.s.index_copy_col_name] = self.model.df.index
        if self.df_filtered is not None:
            self.df_filtered[gui_g.s.index_copy_col_name] = self.df_filtered.index
        # check if the columns order has changed
        new_cols_infos = self.get_col_infos()
        if self._column_infos_saved != new_cols_infos:
            # resize the columns using the data stored before the update
            self.update_col_infos(updated_info=self._column_infos_saved, apply_resize_cols=True)
        if self._current_page_saved != self.current_page:
            self.resetColors()
        self.set_colors()
        if self.update_controls_state_func is not None:
            self.update_controls_state_func()
        if self.update_preview_info_func is not None:
            self.update_preview_info_func()

    def move_to_row(self, row_index: int) -> None:
        """
        Navigate to the specified row in the table.
        :param row_index: (real) ndex of the row to navigate to.
        """
        if row_index < 0 or row_index > len(self.get_data()) - 1:
            return
        self.setSelectedRow(row_index)
        self.redraw()
        self._generate_cell_selection_changed_event()

    def prev_row(self) -> int:
        """
        Navigate to the previous row in the table and opens the edit row window.
        :return: index of the previous row or -1 if the first row is already selected.
        """
        self.gotoprevRow()
        self._generate_cell_selection_changed_event()
        return self.getSelectedRow()

    def next_row(self) -> int:
        """
        Navigate to the next row in the table and opens the edit row window.
        :return: index of the next row, or -1 if the last row is already selected.
        """
        self.gotonextRow()
        self._generate_cell_selection_changed_event()
        return self.getSelectedRow()

    def next_page(self) -> None:
        """
        Navigate to the next page of the table data.
        """
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_page()

    def prev_page(self) -> None:
        """
        Navigate to the previous page of the table data.
        """
        if self.current_page > 1:
            self.current_page -= 1
            self.update_page()

    def first_page(self) -> None:
        """
        Navigate to the first page of the table data.
        """
        self.current_page = 1
        self.update_page()

    def last_page(self) -> None:
        """
        Navigate to the last page of the table data.
        """
        self.current_page = self.total_pages
        self.update_page()

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
        self.adjustColumnWidths(limit=self.cols)
        self._set_with_for_hidden_columns()
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
        :param row_index: (real) index of the row to save.

        Notes:
            self.tableChanged() is called if some rows must be saved
        """
        self.tableChanged()  # to force a controls update
        if row_index < 0 or row_index > len(self.get_data()) or row_index in self._changed_rows:
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
        :param asset_id: asset_id of the row to delete.
        """
        if asset_id in self._deleted_asset_ids:
            return
        self._deleted_asset_ids.append(asset_id)

    def clear_asset_ids_to_delete(self) -> None:
        """
        Clear the list of asset_ids to delete.
        """
        self._deleted_asset_ids = []

    def get_row(self, row_index: int, return_as_dict: bool = False):
        """
        Return the row at the specified index.
        :param row_index: (real) index of the row to get.
        :param return_as_dict: set to True to return the row as a dict.
        :return: row at the specified index.
        """
        try:

            row = self.get_data().iloc[row_index]  # iloc checked
            if return_as_dict:
                return row.to_dict()
            else:
                return row
        except IndexError:
            self.logger.warning(f'Could not get data for row index {row_index} from the datatable')
            return None

    def update_row(self, row_number: int, ue_asset_data: dict, convert_row_number_to_row_index: bool = False) -> None:
        """
        Update the row with the data from ue_asset_data
        :param row_number: row number from a datatable. Will be converted into real row index.
        :param ue_asset_data: data to update the row with.
        :param convert_row_number_to_row_index: set to True to convert the row_number to a row index when editing each cell value.
        """
        # OLD if ue_asset_data is None or not ue_asset_data or len(ue_asset_data) == 0:
        if not ue_asset_data:
            return
        if isinstance(ue_asset_data, list):
            ue_asset_data = ue_asset_data[0]
        asset_id = self.get_cell(row_number, self.get_col_index('Asset_id'), convert_row_number_to_row_index)
        if asset_id in gui_g.s.cell_is_empty_list[1:]:  # exclude 'NA'
            asset_id = ue_asset_data.get('asset_id', gui_g.s.cell_is_empty_list[0])
        text = f'Row #{row_number + 1}' if convert_row_number_to_row_index else f'row index {row_number}'
        self.logger.info(f'Updating {text} with asset_id={asset_id}')
        error_count = 0
        for key, value in ue_asset_data.items():
            typed_value = gui_t.get_typed_value(sql_field=key, value=value)
            # get the column index of the key
            col_name = gui_t.get_csv_field_name(key)
            if gui_t.is_on_state(key, [gui_t.CSVFieldState.ASSET_ONLY]):
                continue
            col_index = self.get_col_index(col_name)  # return -1 col_name is not on the table
            if col_index >= 0:
                if not self.update_cell(row_number, col_index, typed_value, convert_row_number_to_row_index):
                    error_count += 1
        if error_count > 0:
            self.logger.warning(f'{error_count} Errors occured when updating {len(ue_asset_data.items())} cells for row {text}')
        self.update_page()

    def get_col_name(self, col_index: int) -> str:
        """
        Return the name of the column at the specified index.
        :param col_index: column index.
        :return: name of the column at the specified index or '' if the column index is out of range.
        """
        try:
            return self.get_data().columns[col_index]  # Use Unfiltered here to be sure to have all the columns
        except IndexError:
            return ''

    def get_col_index(self, col_name: str) -> int:
        """
        Return the index of the column with the specified name.
        :param col_name: column name.
        :return: index of the column with the specified name or -1 if the column name is not found.
        """
        try:
            return self.get_data().columns.get_loc(col_name)  # Use Unfiltered here to be sure to have all the columns
        except KeyError:
            return -1

    def get_cell(self, row_number: int = -1, col_index: int = -1, convert_row_number_to_row_index: bool = True):
        """
        Return the value of the cell at the specified row and column from the FILTERED or UNFILTERED data
        :param row_number: row number from a datatable. Will be converted into real row index if convert_row_number_to_row_index is set to True. Done by default.
        :param col_index: column index.
        :param convert_row_number_to_row_index: set to True to convert the row_number to a row index when editing each cell value.
        :return: value of the cell or None if the row or column index is out of range.

        Notes:
            If row_number or col_index are not passed, the last selected row or column will be used.
        """
        if row_number < 0:
            row_number = self._last_selected_row
        if col_index < 0:
            col_index = self._last_selected_col

        if row_number < 0 or col_index < 0:
            return None
        try:
            idx = self.get_real_index(row_number) if convert_row_number_to_row_index else row_number
            df = self.get_data(df_type=DataFrameUsed.UNFILTERED)  # always used the unfiltered because the real index is set from unfiltered dataframe
            if idx < 0 or idx >= len(df):
                return None
            return df.iat[idx, col_index]  # iat checked
        except IndexError:
            return None

    def update_cell(self, row_number: int = -1, col_index: int = -1, value=None, convert_row_number_to_row_index: bool = True) -> bool:
        """
        Update the value of the cell at the specified row and column from the FILTERED or UNFILTERED data.
        :param row_number: row number from a datatable. Will be converted into real row index if convert_row_number_to_row_index is set to True. Done by default.
        :param col_index: column index.
        :param value: new value of the cell.
        :param convert_row_number_to_row_index: set to True to convert the row_number to a row index when editing each cell value.
        :return: True if the cell was updated, False otherwise.
        """
        if row_number < 0 or col_index < 0 or value is None:
            return False
        value = gui_g.s.empty_cell if value in gui_g.s.cell_is_empty_list else value  # convert 'None' values to ''
        try:
            idx = self.get_real_index(row_number) if convert_row_number_to_row_index else row_number
            df = self.get_data()  # always used the unfiltered because the real index is set from unfiltered dataframe
            if idx < 0 or idx >= len(df):
                return False
            df.iat[idx, col_index] = value  # iat checked
            self.must_save = True
            return True
        except (ValueError, TypeError) as error:
            self.add_error(error)
            if not self._is_scanning and 'Cannot setitem on a Categorical with a new category' in str(error):
                # this will occur when scanning folder with category that are not in the table yet
                col_name = self.get_col_name(col_index)
                gui_f.log_warning(f'Trying to set a value that is not an existing category for field {col_name}.')
            return False
        except IndexError:
            return False

    def get_edited_row_values(self) -> dict:
        """
        Return the values of the selected row in the table.
        :return: dictionary containing the column names and their corresponding values for the selected row.
        """
        if not self._edit_row_entries or self._edit_row_number < 0:
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

    def get_container(self) -> ttk.Frame:
        """
        Return the container of the table.
        :return: container of the table.
        """
        return self._container

    def create_edit_row_window(self, event=None) -> None:
        """
        Create the edit row window for the selected row in the table.
        :param event: event that triggered the function call.
        """
        if gui_g.WindowsRef.edit_row is not None and gui_g.WindowsRef.edit_row.winfo_viewable():
            gui_g.WindowsRef.edit_row.focus_set()
            return

        if event is not None:
            if event.type != tk.EventType.KeyPress:
                row_number = self.get_row_clicked(event)
            else:
                row_number = self.get_selected_row_fixed()
        else:
            row_number = self.get_selected_row_fixed()
        if row_number is None or row_number >= len(self.model.df):  # model. df checked:
            return None
        title = 'Edit current row'
        width = 800
        height = 1010 if self.data_source_type == DataSourceType.DATABASE else 920
        # window is displayed at mouse position
        # x = self.master.winfo_rootx()
        # y = self.master.winfo_rooty()
        edit_row_window = EditRowWindow(
            parent=self.master, title=title, width=width, height=height, icon=gui_g.s.app_icon_filename, editable_table=self
        )
        edit_row_window.minsize(width, height)
        # configure the grid
        edit_row_window.frm_content.columnconfigure(0, weight=0)
        edit_row_window.frm_content.columnconfigure(1, weight=1)
        self.edit_row(row_number)

    def edit_row(self, row_number: int = None) -> None:
        """
        Edit the values of the specified row in the table.
        :param row_number: row number from a datatable. Will be converted into real row index.
        """
        edit_row_window = gui_g.WindowsRef.edit_row
        if row_number is None or edit_row_window is None:
            return
        idx = self.get_real_index(row_number)
        row_data = self.get_row(idx, return_as_dict=True)
        if row_data is None:
            self.logger.warning(f'edit_row: row_data is None for index #{idx}')
            return
        entries = {}
        image_url = ''
        previous_was_a_bool = False
        row = 0
        hidden_col_list = [gui_g.s.index_copy_col_name] + gui_g.s.hidden_column_names
        hidden_col_list_lower = [col.lower() for col in hidden_col_list]
        for key, value in row_data.items():
            # print(f'row {row}:key={key} value={value} previous_was_a_bool={previous_was_a_bool})  # debug only
            key_lower = key.lower()
            if key_lower in hidden_col_list_lower:
                continue
            if gui_t.is_on_state(key, [gui_t.CSVFieldState.ASSET_ONLY]):
                continue
            label = gui_t.get_label_for_field(key)

            if key_lower == 'image':
                image_url = value
            if gui_t.is_from_type(key, [gui_t.CSVFieldType.TEXT]):
                if previous_was_a_bool:
                    row += 1  # the previous row was a bool, we have to move to the next row
                previous_was_a_bool = False
                ttk.Label(edit_row_window.frm_content, text=label).grid(row=row, column=0, sticky=tk.W)
                entry = ExtendedText(edit_row_window.frm_content, height=3)
                entry.set_content(value)
                entry.grid(row=row, column=1, columnspan=3, sticky=tk.EW)
            elif gui_t.is_from_type(key, [gui_t.CSVFieldType.BOOL]):
                # values by default. keep here !
                col_span = 1
                if previous_was_a_bool:
                    col_label = 2
                    col_value = 3
                else:
                    col_label = 0
                    col_value = 1
                ttk.Label(edit_row_window.frm_content, text=label).grid(row=row, column=col_label, sticky=tk.W)
                entry = ExtendedCheckButton(edit_row_window.frm_content, label='', images_folder=gui_g.s.assets_folder)
                entry.set_content(value)
                entry.grid(row=row, column=col_value, columnspan=col_span, sticky=tk.EW)
                previous_was_a_bool = not previous_was_a_bool
                if previous_was_a_bool:
                    row -= 1  # we stay on the same row for the next loop
                # TODO : add other extended widget for specific type (CSVFieldType.DATETIME , CSVFieldType.LIST)
            else:
                # other field is just a usual entry
                if previous_was_a_bool:
                    row += 1  # the previous row was a bool, we have to move to the next row
                previous_was_a_bool = False
                ttk.Label(edit_row_window.frm_content, text=label).grid(row=row, column=0, sticky=tk.W)
                entry = ttk.Entry(edit_row_window.frm_content)
                entry.insert(0, value)
                entry.grid(row=row, column=1, columnspan=3, sticky=tk.EW)
            row += 1
            entries[key] = entry
        self._edit_row_entries = entries
        self._edit_row_number = row_number
        self._edit_row_window = edit_row_window
        edit_row_window.initial_values = self.get_edited_row_values()
        # image preview
        if not gui_f.show_asset_image(
            image_url=image_url, canvas_image=edit_row_window.frm_control.canvas_image, scale=edit_row_window.preview_scale
        ):
            # the image could not be loaded and the offline mode could have been enabled
            self._container.update_controls_state(update_title=True)
        gui_f.make_modal(edit_row_window)

    def save_edit_row(self) -> None:
        """
        Save the edited row values to the table data.
        """
        row_number = self._edit_row_number
        for col_name, value in self.get_edited_row_values().items():
            col_index = self.get_col_index(col_name)
            value_saved = self.get_cell(row_number, col_index)
            typed_value_saved = gui_t.get_typed_value(csv_field=col_name, value=value_saved)
            typed_value = gui_t.get_typed_value(csv_field=col_name, value=value)
            try:
                typed_value = typed_value.strip('\n\t\r')  # remove unwanted characters
            except AttributeError:
                # no strip method
                pass
            if col_name == 'Installed folders' and typed_value != gui_g.s.empty_cell and typed_value != typed_value_saved:
                if not gui_f.box_yesno(
                    'Usually, the "installed folders" field should not be manually change to avoid incoherent data.\nAre you sure you want to change this value ?'
                ):
                    continue
            if not self.update_cell(row_number, col_index, typed_value):
                self.logger.warning(f'Failed to update the row #{row_number + 1}')
                continue
        self._edit_row_entries = None
        self._edit_row_number = -1
        idx = self.get_real_index(row_number)
        self.add_to_rows_to_save(idx)  # self.must_save = True is done inside
        self._edit_row_window.close_window()
        self.update()  # this call will copy the changes to model. df AND to self.filtered_df
        self.update_quick_edit(row_number)

    def create_edit_cell_window(self, event) -> None:
        """
        Create the edit cell window for the selected cell in the table.
        :param event: event that triggered the creation of the edit cell window.
        """
        if gui_g.WindowsRef.edit_cell is not None and gui_g.WindowsRef.edit_cell.winfo_viewable():
            gui_g.WindowsRef.edit_cell.focus_set()
            return

        if event.type != tk.EventType.KeyPress:
            row_number = self.get_row_clicked(event)
            col_index = self.get_col_clicked(event)
        else:
            row_number = self.get_selected_row_fixed()
            col_index = self.getSelectedColumn()

        if row_number is None or col_index is None or row_number >= len(self.model.df):  # model. df checked
            return None
        cell_value = self.get_cell(row_number, col_index)
        title = 'Edit current cell values'
        width = 300
        height = 120
        # window is displayed at mouse position
        # x = self.master.winfo_rootx()
        # y = self.master.winfo_rooty()
        edit_cell_window = EditCellWindow(parent=self.master, title=title, width=width, height=height, editable_table=self)
        edit_cell_window.minsize(width, height)

        # get and display the cell data
        col_name = self.get_col_name(col_index)
        label = gui_t.get_label_for_field(col_name)
        ttk.Label(edit_cell_window.frm_content, text=label).pack(side=tk.LEFT)
        cell_value_str = str(cell_value) if (cell_value not in gui_g.s.cell_is_empty_list) else ''
        if gui_t.is_from_type(col_name, [gui_t.CSVFieldType.TEXT]):
            widget = ExtendedText(edit_cell_window.frm_content, tag=col_name, height=3)
            widget.set_content(cell_value_str)
            widget.tag_add('sel', '1.0', tk.END)  # select the content
            edit_cell_window.set_size(width=width, height=height + 80)  # more space for the lines in the text
        elif gui_t.is_from_type(col_name, [gui_t.CSVFieldType.BOOL]):
            widget = ExtendedCheckButton(edit_cell_window.frm_content, tag=col_name, label='', images_folder=gui_g.s.assets_folder)
            widget.set_content(bool(cell_value))
        else:
            # other field is just a ExtendedEntry
            widget = ExtendedEntry(edit_cell_window.frm_content, tag=col_name)
            widget.insert(0, cell_value_str)
            widget.selection_range(0, tk.END)  # select the content

        widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._edit_cell_widget = widget
        self._edit_cell_row_number = row_number
        self._edit_cell_col_index = col_index
        self._edit_cell_window = edit_cell_window
        edit_cell_window.initial_values = self.get_edit_cell_values()
        gui_f.make_modal(edit_cell_window, widget_to_focus=widget)

    def get_edit_cell_values(self) -> str:
        """
        Return the values of the selected cell in the table.
        :return: value of the selected cell.
        """
        if self._edit_cell_widget is None:
            return ''
        tag = self._edit_cell_widget.tag
        value = self._edit_cell_widget.get_content()
        typed_value = gui_t.get_typed_value(csv_field=tag, value=value)
        return typed_value

    def save_edit_cell_value(self) -> None:
        """
        Save the edited cell value to the table data.
        """
        widget = self._edit_cell_widget
        if widget is None or self._edit_cell_widget is None or self._edit_cell_row_number < 0 or self._edit_cell_col_index < 0:
            return
        try:
            tag = self._edit_cell_widget.tag
            value = self._edit_cell_widget.get_content()
            row_number = self._edit_cell_row_number
            col_index = self._edit_cell_col_index
            value_saved = self.get_cell(row_number, col_index)
            typed_value_saved = gui_t.get_typed_value(csv_field=tag, value=value_saved)
            typed_value = gui_t.get_typed_value(csv_field=tag, value=value)
            try:
                typed_value = typed_value.strip('\n\t\r')  # remove unwanted characters
            except AttributeError:
                # no strip method for the typed_value
                pass
            col_installed_folders = self.get_col_index('Installed folders')
            if col_index == col_installed_folders and typed_value != gui_g.s.empty_cell and typed_value != typed_value_saved:
                if not gui_f.box_yesno(
                    'Usually, the "installed folders" field should not be manually change to avoid incoherent data.\nAre you sure you want to change this value ?'
                ):
                    self._edit_cell_window.close_window()
                    return
            if not self.update_cell(row_number, col_index, typed_value):
                self.logger.warning(f'Failed to update the row #{row_number + 1}')
                return
            self._edit_cell_widget = None
            self._edit_cell_row_number = -1
            self._edit_cell_col_index = -1
        except TypeError:
            self.logger.warning(f'Failed to get content of {widget}')
            return
        idx = self.get_real_index(row_number)
        self.add_to_rows_to_save(idx)  # self.must_save = Trueis done inside
        self._edit_cell_window.close_window()
        self.update()  # this call will copy the changes to model. df AND to self.filtered_df
        self.update_quick_edit(idx)

    def update_quick_edit(self, row_number: int = None) -> None:
        """
        Quick edit the content some cells of the selected row.
        :param row_number: row number from a datatable. Will be converted into real row index.
        """
        frm_quick_edit = self._frm_quick_edit
        if frm_quick_edit is None:
            frm_quick_edit = self._frm_quick_edit
        else:
            self._frm_quick_edit = frm_quick_edit

        if row_number is None or row_number >= len(self.get_data(df_type=DataFrameUsed.MODEL)) or frm_quick_edit is None:
            return

        column_names = ['Asset_id', 'Url']
        column_names.extend(gui_t.get_csv_field_name_list(filter_on_states=[gui_t.CSVFieldState.USER]))
        for col_name in column_names:
            col_index = self.get_col_index(col_name)
            value = self.get_cell(row_number, col_index)
            if col_name == 'Asset_id':
                frm_content = self._container
                uevm_gui = frm_content.container
                uevm_gui.set_asset_id(value)
                continue
            typed_value = gui_t.get_typed_value(csv_field=col_name, value=value)
            if col_index >= 0:
                frm_quick_edit.set_child_values(tag=col_name, content=typed_value, row=row_number, col=col_index)

    def quick_edit(self) -> None:
        """
        Reset the cell content preview.
        """
        self._frm_quick_edit.config(text='Select a row for Quick Editing its USER FIELDS')
        column_names = gui_t.get_csv_field_name_list(filter_on_states=[gui_t.CSVFieldState.USER])
        for col_name in column_names:
            self._frm_quick_edit.set_default_content(col_name)

    def save_quick_edit_cell(self, row_number: int = -1, col_index: int = -1, value: str = '', tag: str = None) -> None:
        """
        Save the cell content preview.
        :param value: value to save.
        :param row_number: row number from a datatable. Will be converted into real row index.
        :param col_index: column index of the cell.
        :param tag: tag associated to the control where the value come from.
        """
        value_saved = self.get_cell(row_number, col_index)
        typed_value_saved = gui_t.get_typed_value(sql_field=tag, value=value_saved)
        typed_value = gui_t.get_typed_value(sql_field=tag, value=value)
        try:
            typed_value = typed_value.strip('\n\t\r')  # remove unwanted characters
        except AttributeError:
            # no strip method for the typed_value
            pass
        if row_number < 0 or row_number >= len(self.get_data(df_type=DataFrameUsed.MODEL)) or col_index < 0 or typed_value_saved == typed_value:
            return
        col_installed_folders = self.get_col_index('Installed folders')
        if col_index == col_installed_folders and typed_value != gui_g.s.empty_cell and typed_value != typed_value_saved:
            if not gui_f.box_yesno(
                'Usually, the "installed folders" field should not be manually change to avoid incoherent data.\nAre you sure you want to change this value ?'
            ):
                self.update_quick_edit(row_number)  # reset the value
                return
        try:
            if not self.update_cell(row_number, col_index, typed_value):
                self.logger.warning(f'Failed to update the row #{row_number + 1}')
                return
            idx = self.get_real_index(row_number)
            self.add_to_rows_to_save(idx)  # self.must_save = True is done inside
            self.logger.debug(f'Saved cell value {typed_value} at ({row_number},{col_index})')
            self.update()  # this call will copy the changes to model. df AND to self.filtered_df
        except IndexError:
            self.logger.warning(f'Failed to save cell value {typed_value} at ({row_number},{col_index})')

    def get_image_url(self, row_number: int = None) -> str:
        """
        Return the image URL of the selected row.
        :param row_number: row number from a datatable. Will be converted into real row index.
        :return: image URL of the selected row.
        """
        return '' if row_number is None else self.get_cell(row_number, self.get_col_index('Image'))

    def open_asset_url(self, url: str = None):
        """
        Open the asset URL in a web browser.
        :param url: URL to open.
        """
        if url is None:
            if self._edit_row_entries is None:
                return
            asset_url = self._edit_row_entries['Url'].get()
        else:
            asset_url = url
        self.logger.info(f'calling open_asset_url={asset_url}')
        if not asset_url or asset_url == gui_g.s.empty_cell:
            self.logger.info('asset URL is empty for this asset')
            return
        webbrowser.open(asset_url)

    def open_origin_folder(self) -> None:
        """
        Open the asset origin folder.
        """
        row_number = self.get_selected_row_fixed()
        if row_number is None or row_number < 0:
            return
        added = self.get_cell(row_number, self.get_col_index('Added manually'))
        # open the folder of the asset
        if added:
            origin = self.get_cell(row_number, self.get_col_index('Origin'))
            # open the folder of the asset
            if not gui_fn.open_folder_in_file_explorer(origin):
                gui_f.box_message(f'Error while opening the folder of the asset "{origin}"', 'warning')
        else:
            gui_f.box_message('Only possible with asset that have been mannualy added.', 'info')

    def get_release_info(self, row_number: int = None) -> str:
        """
        Return the "Release info" field the selected row.
        :param row_number: row number from a datatable. Will be converted into real row index.
        :return: "Release info" dict as a json string.
        """
        row_number = row_number or self.get_selected_row_fixed()
        if row_number is None or row_number < 0:
            return ''
        col_index = self.get_col_index('Release info')
        if col_index < 0:
            return ''
        else:
            return self.get_cell(row_number, col_index)

    def set_release_info(self, row_number: int = None, value=None) -> None:
        """
        Return the "Release info" field the selected row.
        :param row_number: row number from a datatable. Will be converted into real row index.
        :param value: "Release info" dict as a json string.
        :return: "Release info" dict as a json string.
        """
        row_number = row_number or self.get_selected_row_fixed()
        if row_number is None or row_number < 0 or value is None:
            return
        col_index = self.get_col_index('Release info')
        if col_index >= 0:
            self.update_cell(row_number, col_index, value)

    def reset_style(self) -> None:
        """
        Reset the table style. Usefull when style of the main ttk window has changed.
        """
        self.get_data(df_type=DataFrameUsed.UNFILTERED).style.clear()
        df = self.get_data(df_type=DataFrameUsed.FILTERED)
        if df is not None:
            df.style.clear()
        self.redraw()

    def add_error(self, error: Exception) -> None:
        """
        Add an error to the list of errors.
        :param error: error to add.
        """
        self._errors.append(error)
