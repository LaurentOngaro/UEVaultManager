# coding=utf-8
"""
Implementation for:
_ clean_ue_asset_name: clean a name to remove unwanted characters.
- UEVMGui: main window of the application.
"""
import filecmp
import logging
import os
import re
import shutil
import tkinter as tk
from datetime import datetime
from time import sleep
from tkinter import filedialog as fd, simpledialog
from typing import Optional

import pandas as pd
from rapidfuzz import fuzz
from requests import ReadTimeout

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.api.egs import EPCAPI
from UEVaultManager.core import AppCore
from UEVaultManager.lfs.utils import get_version_from_path, path_join
from UEVaultManager.models.csv_sql_fields import debug_parsed_data
from UEVaultManager.models.types import DateFormat
from UEVaultManager.models.UEAssetDbHandlerClass import UEAssetDbHandler
from UEVaultManager.models.UEAssetScraperClass import UEAssetScraper
from UEVaultManager.tkgui.modules.cls.ChoiceFromListWindowClass import ChoiceFromListWindow
from UEVaultManager.tkgui.modules.cls.DbToolWindowClass import DbToolWindowClass
from UEVaultManager.tkgui.modules.cls.DisplayContentWindowClass import DisplayContentWindow
from UEVaultManager.tkgui.modules.cls.EditableTableClass import EditableTable
from UEVaultManager.tkgui.modules.cls.FakeProgressWindowClass import FakeProgressWindow
from UEVaultManager.tkgui.modules.cls.FilterValueClass import FilterValue
from UEVaultManager.tkgui.modules.cls.ImagePreviewWindowClass import ImagePreviewWindow
from UEVaultManager.tkgui.modules.cls.JsonToolWindowClass import JsonToolWindow
from UEVaultManager.tkgui.modules.comp.FilterFrameComp import FilterFrame
from UEVaultManager.tkgui.modules.comp.functions_panda import post_update_installed_folders
from UEVaultManager.tkgui.modules.comp.UEVMGuiContentFrameComp import UEVMGuiContentFrame
from UEVaultManager.tkgui.modules.comp.UEVMGuiControlFrameComp import UEVMGuiControlFrame
from UEVaultManager.tkgui.modules.comp.UEVMGuiOptionFrameComp import UEVMGuiOptionFrame
from UEVaultManager.tkgui.modules.comp.UEVMGuiToolbarFrameComp import UEVMGuiToolbarFrame
from UEVaultManager.tkgui.modules.types import DataFrameUsed, DataSourceType, FilterType, UEAssetType
from UEVaultManager.tkgui.modules.types import GrabResult


# not needed here
# warnings.filterwarnings('ignore', category=FutureWarning)  # Avoid the FutureWarning when PANDAS use ser.astype(object).apply()


def clean_ue_asset_name(name_to_clean: str) -> str:
    """
    Clean a name to remove unwanted characters.
    :param name_to_clean: name to clean.
    :return: cleaned name.
    """
    name_cleaned = name_to_clean
    # ONE: convert some unwanted strings to @. @ is used to identify the changes made
    patterns = [
        r'UE_[\d._]+',  # any string starting with 'UE_' followed by any digit, dot or underscore ex: 'UE_4_26'
        r'_UE[\d._]+',  # any string starting with '_UE' followed by any digit, dot or underscore ex: '_UE4_26'
        r'\d+[._]+',  # at least one digit followed by a dot or underscore  ex: '1.0' or '1_0'
        ' - UE Marketplace',  # remove ' - UE Marketplace'
        r'\b(\w+)\b in (\1){1}.',
        # remove ' in ' and the string before and after ' in ' are the same ex: "Linhi Character in Characters" will keep only "Linhi"
        r' in \b.+?$',  # any string starting with ' in ' and ending with the end of the string ex: ' in Characters'
    ]
    patterns = [re.compile(p) for p in patterns]
    for pattern in patterns:
        name_cleaned = pattern.sub('@', name_cleaned)

    # TWO: remove converted string with relicats
    patterns = [
        r'v\d+[._\w\d]+',  # v followed by at least one digit followed by dot or underscore or space or digit ex: 'v1.0' or 'v1_0' or 'v1 '
        r'v[@]+\d+',  # v followed by @ followed by at least one digit ex: 'v@1' or 'v@11'
        r'[@]+\d+',  # a @ followed by at least one digit ex: '@1' or '@11'
        # r'\d+[@]+',  # at least one digit followed by @ ex: '1@' or '1@@'
        r'[@]+',  # any @  ex: '@' or '@@'
    ]
    patterns = [re.compile(p) for p in patterns]
    for pattern in patterns:
        name_cleaned = pattern.sub('', name_cleaned)

    name_cleaned = name_cleaned.replace('_', '-')
    return name_cleaned.strip()  # Remove leading and trailing spaces


class UEVMGui(tk.Tk):
    """
    This class is used to create the main window for the application.
    :param title: title.
    :param icon: icon.
    :param screen_index: screen index where the window will be displayed.
    :param data_source: source where the data is stored or read from.
    """
    is_fake = False
    logger = logging.getLogger(__name__.split('.')[-1])  # keep only the class name
    gui_f.update_loggers_level(logger)
    _errors: [Exception] = []

    def __init__(
        self, title: str = 'UVMEGUI', icon='', screen_index: int = 0, data_source_type: DataSourceType = DataSourceType.FILE, data_source=None,
    ):
        self._frm_toolbar: Optional[UEVMGuiToolbarFrame] = None
        self._frm_control: Optional[UEVMGuiControlFrame] = None
        self._frm_option: Optional[UEVMGuiOptionFrame] = None
        self._frm_content: Optional[UEVMGuiContentFrame] = None
        self._frm_filter: Optional[FilterFrame] = None
        self._releases_choice = {}
        self._update_delay: int = 2000
        self._silent_mode: bool = False
        self._choice_result: str = ''
        self._image_url: str = ''

        self.editable_table: Optional[EditableTable] = None
        self.progress_window: Optional[FakeProgressWindow] = None
        self.egs: Optional[EPCAPI] = None
        # using a global scraper to avoid creating a new one and a new db connection on multiple scrapes
        self.ue_asset_scraper: Optional[UEAssetScraper] = None

        super().__init__()
        self.data_source_type = data_source_type

        self.title(title)
        self.style = gui_fn.set_custom_style(gui_g.s.theme_name, gui_g.s.theme_font)
        width: int = gui_g.s.width
        height: int = gui_g.s.height
        x_pos: int = gui_g.s.x_pos
        y_pos: int = gui_g.s.y_pos
        if not (x_pos and y_pos):
            x_pos, y_pos = gui_fn.get_center_screen_positions(screen_index, width, height)
        self.geometry(f'{width}x{height}+{x_pos}+{y_pos}')
        gui_fn.set_icon_and_minmax(self, icon)
        self.screen_index = screen_index
        self.resizable(True, True)
        pack_def_options = {'ipadx': 5, 'ipady': 5, 'padx': 3, 'pady': 3}

        frm_content = UEVMGuiContentFrame(self)
        self._frm_content = frm_content

        # get the core instance from the cli application if it exists
        self.core = None if gui_g.UEVM_cli_ref is None else gui_g.UEVM_cli_ref.core
        # if the core instance is not set, create a new one
        if not self.core:
            self.core = AppCore()

        if self.is_using_database:
            # if using DATABASE
            # ________________
            # update the "installed folders" BEFORE loading the data in the datatable (because datatable content <> database content)
            # update the installed folder field from the installed_assets json file
            db_handler = UEAssetDbHandler(database_name=data_source)  # we need it BEFORE CREATING the editable_table and use its db_handler property
            self.core.uevmlfs.pre_update_installed_folders(db_handler=db_handler)

        data_table = EditableTable(
            container=frm_content,
            data_source_type=data_source_type,
            data_source=data_source,
            rows_per_page=37,
            show_statusbar=True,
            update_controls_state_func=self.update_controls_state,
            update_preview_info_func=self.update_preview_info,
            set_widget_state_func=gui_f.set_widget_state
        )

        # get the data AFTER updating the installed folder field in database
        df = data_table.get_data()
        if df is None:
            self.logger.error('No valid source to read data from. Application will be closed')
            self.quit()
            self.core.clean_exit(1)  # previous line could not quit

        if not self.is_using_database:
            # if using FILE
            # ________________
            # update the "installed folders" AFTER loading the data in the datatable (because datatable content = CSV content)
            installed_assets_json = self.core.uevmlfs.get_installed_assets().copy()  # copy because the content could change during the process
            post_update_installed_folders(installed_assets_json, df)

        self.editable_table = data_table

        data_table.set_preferences(gui_g.s.datatable_default_pref)
        data_table.show()

        frm_toolbar = UEVMGuiToolbarFrame(self, data_table)
        self._frm_toolbar = frm_toolbar
        frm_control = UEVMGuiControlFrame(self, data_table)
        self._frm_control = frm_control
        frm_option = UEVMGuiOptionFrame(self)
        self._frm_option = frm_option

        frm_toolbar.pack(**pack_def_options, fill=tk.X, side=tk.TOP, anchor=tk.NW)
        frm_content.pack(**pack_def_options, fill=tk.BOTH, side=tk.LEFT, anchor=tk.NW, expand=True)
        frm_control.pack(**pack_def_options, fill=tk.BOTH, side=tk.RIGHT, anchor=tk.NW)
        # not displayed at start
        # _frm_option.pack(**pack_def_options, fill=tk.BOTH, side=tk.RIGHT, anchor=tk.NW)

        self.bind('<Tab>', self._focus_next_widget)
        self.bind('<Control-Tab>', self._focus_next_widget)
        self.bind('<Shift-Tab>', self._focus_prev_widget)
        self.bind('<Key>', self.on_key_press)
        # Bind the table to the mouse motion event
        data_table.bind('<Motion>', self.on_mouse_over_cell)
        data_table.bind('<Leave>', self.on_mouse_leave_cell)
        data_table.bind('<<CellSelectionChanged>>', self.on_selection_change)
        # Bind mouse drag event on column header.
        # THIS COULD NOT BE DONE IN THE CLASS __init__ METHOD because the widget is not yet created
        data_table.colheader.bind('<B1-Motion>', self.on_header_drag)
        data_table.colheader.bind('<ButtonRelease-1>', self.on_header_release)
        data_table.showIndex = True

        self.bind('<Button-1>', self.on_left_click)
        self.protocol('WM_DELETE_WINDOW', self.on_close)
        gui_g.WindowsRef.uevm_gui = self

    @property
    def is_using_database(self) -> bool:
        """ Check if the table is using a database as data source. """
        return self.data_source_type == DataSourceType.DATABASE

    def setup(self, show_open_file_dialog: bool = False, rebuild_data: bool = False) -> None:
        """
        Set up the application. Called after the window is created.
        :param show_open_file_dialog: whether the open file dialog will be shown at startup.
        :param rebuild_data: whether the data will be rebuilt at startup.
        """
        data_table = self.editable_table  # shortcut
        if data_table.is_using_database:
            show_open_file_dialog = False
        if not show_open_file_dialog and (rebuild_data or data_table.must_rebuild):
            if gui_f.box_yesno('Data file is invalid or empty. Do you want to rebuild data from sources files ?'):
                if not data_table.rebuild_data(self.core.uevmlfs.asset_sizes):
                    self.logger.error('Rebuild data error. This application could not run without a file to read from or some data to build from it')
                    self.destroy()  # self.quit() won't work here
                    return
            elif data_table.data_source_type == DataSourceType.FILE and gui_f.box_yesno(
                'So, do you want to load another file ? If not, the application will be closed'
            ):
                show_open_file_dialog = True
            else:
                # self.logger.error('No valid source to read data from. Application will be closed', )
                # self.close_window(True)
                msg = 'No valid source to read data from. The datatable will contain fake data. You should rebuild ou import real data from a file or a database.'
                gui_f.box_message(msg, level='warning')

        if show_open_file_dialog:
            if not self.open_file():
                self.logger.error('This application could not run without a file to read data from')
                self.close_window(True)

        data_table.update_downloaded_size(self.core.uevmlfs.asset_sizes)

        if gui_g.s.last_opened_filter:
            filter_value = self.core.uevmlfs.load_filter(gui_g.s.last_opened_filter)
            if filter_value is not None:
                gui_f.show_progress(self, text=f'Loading filters from {gui_g.s.last_opened_filter}...')
                try:
                    self._frm_filter.set_filter(filter_value)
                    self._frm_filter.update_controls()
                    data_table.update(update_format=True)
                except (Exception, ) as error:
                    self.add_error(error)
                    self.logger.error(f'Error loading filters: {error!r}')
        else:
            gui_f.show_progress(self, text='Initializing Data Table...')
            data_table.update(update_format=True)
        show_option_fist = False  # debug_only
        gui_f.close_progress(self)
        if show_option_fist:
            self.toggle_options_panel(True)
            self.toggle_actions_panel(False)

    def mainloop(self, n=0):
        """
        Mainloop method
        :param n: threshold.

        Overrided to add logging function for debugging
        """
        self.logger.info(f'starting mainloop in {__name__}')
        self.after(self._update_delay, self.update_progress_windows)
        self.tk.mainloop(n)
        # check is a child window is still open
        # child_windows = self.progress_window or gui_g.WindowsRef.edit_cell or gui_g.WindowsRef.edit_row
        # print('root loop')
        # if child_windows:
        #     self._wait_for_window(child_windows)
        self.logger.info(f'ending mainloop in {__name__}')

    def update_progress_windows(self):
        """
        Update the child progress windows.
        """
        if self.progress_window:
            self.progress_window.update()
            # print('UPDATE')
        self.after(self._update_delay, self.update_progress_windows)

    @staticmethod
    def _focus_next_widget(event):
        event.widget.tk_focusNext().focus()
        return 'break'

    @staticmethod
    def _focus_prev_widget(event):
        event.widget.tk_focusPrev().focus()
        return 'break'

    @staticmethod
    def _open_file_dialog(save_mode: bool = False, filename: str = None, initial_dir: str = '', filetypes: str = '') -> str:
        """
        Open a file dialog to choose a file to save or load data to/from.
        :param save_mode: whether the dialog will be in saving mode, else in loading mode.
        :param filename: default filename to use.
        :param initial_dir: initial directory to use. If empty, the last opened folder will be used.
        :param filetypes: filetypes to use. If empty, the default filetypes will be used.
        :return: chosen filename.
        """
        if filename:
            initial_dir = os.path.dirname(filename) or initial_dir
        else:
            filename = gui_g.s.default_filename
            initial_dir = initial_dir or gui_g.s.last_opened_folder
        default_filename = os.path.basename(filename)  # remove dir
        filetypes = filetypes or gui_g.s.data_filetypes
        if save_mode:
            filename = fd.asksaveasfilename(
                title='Choose a file to save data to', initialdir=initial_dir, filetypes=filetypes, initialfile=default_filename
            )
        else:
            filename = fd.askopenfilename(
                title='Choose a file to read data from', initialdir=initial_dir, filetypes=filetypes, initialfile=default_filename
            )
        filename = os.path.normpath(filename) if filename else ''
        return filename

    def _check_and_get_widget_value(self, tag: str) -> tuple:
        """
        Check if the widget with the given tags exists and return its value and itself.
        :param tag: tag of the widget that triggered the event.
        :return: (value, widget) tuple.
        """
        if not tag:
            return None, None

        widget = self._frm_control.lbtf_quick_edit.get_child_by_tag(tag)

        if widget is None:
            self.logger.warning(f'Could not find a widget with tag {tag}')
            return None, None
        value = widget.get_content()
        # not sure the next code is useful
        # col, row = widget.col, widget.row
        # if col is None or row is None or col < 0 or row < 0:
        #     self.logger.debug(f'invalid values for row={row} and col={col}')
        #     return None, widget
        return value, widget

    def _wait_for_window(self, window: tk.Toplevel) -> None:
        """
        Wait for a window to be closed.
        :param window: window to wait for.
        """
        if not window:
            # the window could have been closed before this call
            return
        try:
            while window.winfo_viewable():
                window.focus_set()
                window.attributes('-topmost', True)  # keep the window on top. Windows only
                # if gui_g.s.testing_switch == 2:
                #     window.grab_set()  # make the window modal
                window.grab_set()  # make the window modal
                sleep(0.5)
                self.update()
                self.update_idletasks()
        except tk.TclError as error:
            # the window has been closed so an error is raised
            self.add_error(error)

    def _update_installed_folders_cell(self, row_index: int, installed_folders: str = None) -> None:
        """
        update the content of the 'Installed folders' cell of the row and the quick edit window.
        :param row_index: index of the row to update.
        :param installed_folders: new value for the cell.
        """
        data_table = self.editable_table
        if installed_folders:
            col_index = data_table.get_col_index('Installed folders')
            if data_table.update_cell(row_index, col_index, installed_folders):
                data_table.update()  # because the "installed folder" field changed
        data_table.update_quick_edit(row_index)

    def _get_choice_result(self, selection):
        """
        Get the result of the choice window.
        """
        self._choice_result = selection

    def on_key_press(self, event):
        """
        Handle key press events.
        :param event: event that triggered the call.
        """
        # Note: this event will be triggered AFTER the event in the editabletable
        # print(event.keysym)
        # shift_pressed = event.state == 1 or event.state & 0x00001 != 0
        # alt_pressed = event.state == 8 or event.state & 0x20000 != 0
        # 4th keys of (FRENCH) keyboard: ampersand eacute quotedbl apostrophe
        control_pressed = event.state == 4 or event.state & 0x00004 != 0
        if event.keysym == 'Escape':
            if gui_g.WindowsRef.edit_cell:
                gui_g.WindowsRef.edit_cell.on_close()
                gui_g.WindowsRef.edit_cell = None
            elif gui_g.WindowsRef.edit_row:
                gui_g.WindowsRef.edit_row.on_close()
                gui_g.WindowsRef.edit_row = None
            else:
                self.on_close()
        elif control_pressed and (event.keysym == 's' or event.keysym == 'S'):
            self.save_changes()
        elif control_pressed and (event.keysym == '1' or event.keysym == 'ampersand'):
            self.editable_table.create_edit_cell_window(event)
        elif control_pressed and (event.keysym == '2' or event.keysym == 'eacute'):
            self.editable_table.create_edit_row_window(event)
        elif control_pressed and (event.keysym == '3' or event.keysym == 'quotedbl'):
            self.scrap_asset()
        return 'break'

        # return 'break'  # stop event propagation

    def on_mouse_over_cell(self, event=None) -> None:
        """
        Show the image of the asset when the mouse is over the cell.
        :param event: event that triggered the call.
        """
        if event is None:
            return
        canvas_image = self._frm_control.canvas_image
        try:
            row_number: int = self.editable_table.get_row_clicked(event)
            if row_number < 0:
                return
            self.update_preview_info(row_number)
            self._image_url = self.editable_table.get_image_url(row_number)
            if not gui_f.show_asset_image(image_url=self._image_url, canvas_image=canvas_image):
                # the image could not be loaded and the offline mode could have been enabled
                self.update_controls_state(update_title=True)
        except IndexError:
            gui_f.show_default_image(canvas_image)

    def on_mouse_leave_cell(self, _event=None) -> None:
        """
        Show the default image when the mouse leaves the cell.
        :param _event: event that triggered the call.

        Note:
            If defined, it will display the last selected row info.
        """
        row_number = self.editable_table.last_selected_row
        canvas_image = self._frm_control.canvas_image
        if row_number < 0:
            self.update_preview_info()
            gui_f.show_default_image(canvas_image=canvas_image)
        else:
            self.update_preview_info(row_number)
            self._image_url = self.editable_table.get_image_url(row_number)
            gui_f.show_asset_image(image_url=self._image_url, canvas_image=canvas_image)

    def on_selection_change(self, event=None) -> None:
        """
        When the selection changes, show the selected row in the quick edit frame.
        :param event: event that triggered the call.
        """
        row_number = event.widget.currentrow
        self.editable_table.update_quick_edit(row_number)
        self.update_controls_state()

    def on_left_click(self, event=None) -> None:
        """
        When the left mouse button is clicked, show the selected row in the quick edit frame.
        :param event: event that triggered the call.
        """
        data_table = self.editable_table  # shortcut
        # if the clic is on a frame (i.e. an empty zone), clean the selection in the table
        try:
            if event.widget.widgetName == 'ttk::frame':
                data_table.selectNone()
                data_table.clearSelected()
                data_table.delete('rowrect')  # remove the highlight rect
        except AttributeError:
            pass
        self.update_controls_state()

    def on_entry_current_item_changed(self, _event=None) -> None:
        """
        When the item (i.e. row or page) number changes, show the corresponding item.
        :param _event: event that triggered the call.
        """
        item_num = self._frm_toolbar.entry_current_item.get()
        try:
            item_num = int(item_num)
        except (ValueError, UnboundLocalError) as error:
            self.add_error(error)
            self.logger.error(f'could not convert item number {item_num} to int. {error!r}')
            return

        data_table = self.editable_table  # shortcut
        if data_table.pagination_enabled:
            self.logger.debug(f'showing page {item_num}')
            data_table.current_page = item_num
            data_table.update_page()
        else:
            self.logger.debug(f'showing row {item_num}')
            data_table.move_to_row(item_num)

    # noinspection PyUnusedLocal
    def on_quick_edit_focus_out(self, tag: str, event=None) -> None:
        """
        When the focus leaves a quick edit widget, save the value.
        :param event: ignored but required for an event handler.
        :param tag: tag of the widget that triggered the event.
        """
        value, widget = self._check_and_get_widget_value(tag)
        if widget and widget.row and widget.col:
            self.editable_table.save_quick_edit_cell(row_number=widget.row, col_index=widget.col, value=value, tag=tag)

    # noinspection PyUnusedLocal
    def on_quick_edit_focus_in(self, tag: str, event=None) -> None:
        """
        When the focus enter a quick edit widget, check (and clean) the value.
        :param event: ignored but required for an event handler.
        :param tag: tag of the widget that triggered the event.
        """
        value, widget = self._check_and_get_widget_value(tag=tag)
        # empty the widget if the value is the default value or none
        if widget and (value in ('None', 'nan', gui_g.s.empty_cell, widget.default_content)):
            value = ''
            widget.set_content(value)

    # noinspection PyUnusedLocal
    def on_switch_edit_flag(self, tag: str, event=None) -> None:
        """
        When the focus leaves a quick edit widget, save the value.
        :param event: event that triggered the call.
        :param tag: tag of the widget that triggered the event.
        """
        _, widget = self._check_and_get_widget_value(tag)
        if widget:
            value = widget.switch_state(event=event)
            self.editable_table.save_quick_edit_cell(row_number=widget.row, col_index=widget.col, value=value, tag=tag)

    def on_header_drag(self, event):
        """
        When the mouse is dragged on the header.
        :param event: event that triggered the call.
        """
        self.editable_table.on_header_drag(event)

    def on_header_release(self, event):
        """
        When the mouse is released on the header.
        :param event: event that triggered the call.
        """
        data_table = self.editable_table  # shortcut
        data_table.on_header_release(event)
        columns = data_table.model.df.columns  # df. model checked
        columns_str = gui_fn.check_and_convert_list_to_str(columns)
        if data_table.columns_saved_str == columns_str:
            return
        widget_list = gui_g.stated_widgets.get('table_has_changed', [])
        gui_f.enable_widgets_in_list(widget_list)
        # update the column infos
        columns_infos_saved = gui_g.s.get_column_infos(self.data_source_type)
        # reorder column_infos using columns keys
        new_columns_infos = {}
        for i, col in enumerate(columns):
            try:
                new_columns_infos[col] = columns_infos_saved.get(col, {'width': 40, 'pos': i})  # columns_infos_saved could be empty
                new_columns_infos[col]['pos'] = i
            except KeyError:
                pass
        gui_g.s.set_column_infos(new_columns_infos, self.data_source_type)
        gui_g.s.save_config_file()
        data_table._columns_saved = gui_fn.check_and_convert_list_to_str(data_table.model.df.columns.values)

    def on_close(self, _event=None) -> None:
        """
        When the window is closed, check if there are unsaved changes and ask the user if he wants to save them.
        :param _event: event that triggered the call of this function.
        """
        if self.editable_table is not None and self.editable_table.must_save:
            if gui_f.box_yesno('Changes have been made. Do you want to save them in the source file ?'):
                self.save_changes()  # will save the settings too
        self.close_window()  # will save the settings too

    def close_window(self, force_quit=False) -> None:
        """
        Close the window.
        """
        self.save_settings()
        self.quit()
        if force_quit:
            gui_f.exit_and_clean_windows(0)

    def add_error(self, error: Exception) -> None:
        """
        Add an error to the list of errors.
        :param error: error to add.
        """
        self._errors.append(error)

    def save_settings(self) -> None:
        """
        Save the settings of the window.
        :return:
        """
        data_table = self.editable_table  # shortcut
        if gui_g.s.reopen_last_file:
            gui_g.s.last_opened_file = data_table.data_source
        # store window geometry in config settings
        gui_g.s.width = self.winfo_width()
        gui_g.s.height = self.winfo_height()
        gui_g.s.x_pos = self.winfo_x()
        gui_g.s.y_pos = self.winfo_y()
        file_backup = gui_f.create_file_backup(gui_g.s.config_file_gui)
        gui_g.s.save_config_file()
        # delete the backup if the files and the backup are identical
        if filecmp.cmp(gui_g.s.config_file_gui, file_backup):
            os.remove(file_backup)

    def open_file(self) -> str:
        """
        Open a file and Load data from it.
        :return: name of the file that was loaded.
        """
        data_table = self.editable_table  # shortcut
        filename = self._open_file_dialog(filename=gui_g.s.last_opened_file)
        if filename and os.path.isfile(filename):
            data_table.data_source = filename
            if data_table.valid_source_type(filename):
                gui_f.show_progress(self, text='Loading Data from file...')
                df_loaded = data_table.read_data()
                if df_loaded is None:
                    gui_f.box_message('Error when loading data', level='warning')
                    gui_f.close_progress(self)
                    return filename
                data_table.current_page = 1
                data_table.update(update_format=True)
                self.update_controls_state()
                self.update_data_source()
                gui_f.box_message(f'The data source {filename} as been read')
                # gui_f.close_progress(self)  # done in data_table.update(update_format=True)
                return filename
            else:
                gui_f.box_message('Operation cancelled')

    def save_changes(self) -> str:
        """
        Save the data to the current data source.
        :return: name of the file that was saved.
        """
        return self.save_changes_as(show_dialog=False)

    def save_changes_as(self, show_dialog: bool = True) -> str:
        """
        Save the data to the current data source.
        :param show_dialog: whether to show a dialog to select the file to save to, if False, use the current file.
        :return: name of the file that was saved.
        """
        data_table = self.editable_table  # shortcut
        self.save_settings()
        data_table.update_col_infos(apply_resize_cols=False)
        if data_table.data_source_type == DataSourceType.FILE:
            if show_dialog:
                filename = self._open_file_dialog(filename=data_table.data_source, save_mode=True)
                if filename:
                    data_table.data_source = filename
            else:
                filename = data_table.data_source
            if filename:
                data_table.save_data()
                self.update_data_source()
                gui_f.box_message(f'Changed data has been saved to {data_table.data_source}')
        else:
            data_table.save_data()
            filename = ''
            gui_f.box_message(f'Changed data has been saved to {data_table.data_source}')
        return filename

    def export_selection(self) -> None:
        """
        Export the selected rows to a file.
        """
        data_table = self.editable_table  # shortcut
        selected_rows = None
        row_numbers = data_table.multiplerowlist
        col_name_to_export = 'Asset_id'
        if row_numbers:
            # convert row numbers to row indexes
            row_indexes = [data_table.get_real_index(row_number) for row_number in row_numbers]
            selected_rows = data_table.get_data().iloc[row_indexes]  # iloc checked
        if selected_rows is not None and not selected_rows.empty:
            json_data = {
                'csv': {
                    'value': 'csv',
                    'desc': 'All the columns data of the selected rows will be exported in a CSV file (comma separated values)'
                },
                'list': {
                    'value': 'list',
                    'desc': f'Only the "{col_name_to_export}" column of the selected rows will be exported in a text file (one value by line)'
                },
                'filter': {
                    'value': 'filter',
                    'desc': f'The "{col_name_to_export}" column will be exported as a ready to use filter in a json file '
                },
            }
            ChoiceFromListWindow(
                window_title='Choose the export format',
                width=220,
                height=250,
                json_data=json_data,
                show_validate_button=True,
                first_list_width=13,
                get_result_func=self._get_choice_result,
                is_modal=True,
            )
            # NOTE: next line will only be executed when the ChoiceFromListWindow will be closed
            # so, the self._get_choice_result method has been called
            file_name = f'{col_name_to_export}_{datetime.now().strftime(DateFormat.file_suffix)}'
            if self._choice_result == 'list':
                filename = self._open_file_dialog(save_mode=True, filename=f'{file_name}.txt', filetypes=gui_g.s.data_filetypes_text)
            elif self._choice_result == 'filter':
                filename = self._open_file_dialog(
                    save_mode=True, filename=f'{file_name}.json', filetypes=gui_g.s.data_filetypes_json, initial_dir=gui_g.s.filters_folder
                )
            else:
                filename = self._open_file_dialog(save_mode=True, filename=f'{file_name}.csv')

            if filename:
                if self._choice_result == 'list':
                    # save the list of "Asset_id" of the selected row to the selected file
                    selected_rows.to_csv(filename, index=False, columns=['Asset_id'], header=False)
                elif self._choice_result == 'filter':
                    # create a filter file with the list of "Asset_id" of the selected row
                    asset_ids = selected_rows[col_name_to_export].tolist()
                    # asset_ids = json.dumps(asset_ids)
                    filter_value = FilterValue(name=col_name_to_export, value=asset_ids, ftype=FilterType.LIST)
                    with open(filename, 'w') as file:
                        file.write(filter_value.to_json())
                else:
                    # export all the columns of the selected rows to the selected file
                    selected_rows.to_csv(filename, index=False)
                gui_f.box_message(f'Selected rows exported to "{filename}"')
        else:
            gui_f.box_message('Select at least one row first', level='warning')

    def add_row(self, row_data=None) -> None:
        """
        Add a new row at the current position.
        :param row_data: data to add to the row.
        """
        add_new_row = True
        data_table = self.editable_table  # shortcut
        if gui_g.s.browse_when_add_row:
            title = 'Choose a folder for the assets to add to the datatable.\nThis folder will be used to scan for assets, Url slugs and marketplace urls.\nIf no folder is selected, an empty row will be added.'
            folder = fd.askdirectory(
                title=title,
                initialdir=gui_g.s.last_opened_folder
                if gui_g.s.last_opened_folder else gui_g.s.folders_to_scan[0] if gui_g.s.folders_to_scan else None,
            )
            if folder:
                folder = os.path.normpath(folder)
                gui_g.s.last_opened_folder = folder
                add_new_row = False
                self.scan_for_assets([folder], from_add_button=True)
                # if row_data is None:
                #     row_data = {}
                # row_data['Origin'] = os.path.abspath(folder)
            else:
                add_new_row = True
        if add_new_row:
            row, new_index = data_table.create_row(row_data=row_data)
            data_table.update(update_format=True)
            data_table.move_to_row(new_index)
            self.event_generate('<<tableChanged>>')
            text = f' with asset_id={row["Asset_id"][0]}' if row is not None else ''
            gui_f.box_message(f'A new row{text} has been added at index {new_index} of the datatable')

    def del_row(self) -> None:
        """
        Remove the selected row from the DataFrame (Wrapper).
        """
        self.editable_table.del_rows()

    def edit_row(self) -> None:
        """
        Edit the selected row (Wrapper).
        """
        self.editable_table.create_edit_row_window()

    def search_for_url(self, folder: str, parent: str, check_if_valid: bool = False) -> str:
        """
        Search for a marketplace_url file that matches a folder name in a given folder.
        :param folder: name to search for.
        :param parent: parent folder to search in.
        :param check_if_valid: whether to check if the marketplace_url is valid. Return an empty string if not.
        :return: marketplace_url found in the file or an empty string if not found.
        """

        def read_from_url_file(entry, folder_name: str, returned_urls: [str]) -> bool:
            """
            Read an url from a .url file and add it to the list of urls to return.
            :param entry: entry to process.
            :param folder_name: name of the folder to search for.
            :param returned_urls: list of urls to return. We use a list instead of a str because we need to modify it from the inner function.
            :return: True if the entry is a file and the name matches the folder name, False otherwise.
            """
            if entry.is_file() and entry.name.lower().endswith('.url'):
                folder_name_cleaned = clean_ue_asset_name(folder_name)
                file_name = os.path.splitext(entry.name)[0]
                file_name_cleaned = clean_ue_asset_name(file_name)
                fuzz_score = fuzz.ratio(folder_name_cleaned, file_name_cleaned)
                self.logger.debug(f'Fuzzy compare {folder_name} ({folder_name_cleaned}) with {file_name} ({file_name_cleaned}): {fuzz_score}')
                minimal_score = gui_g.s.minimal_fuzzy_score_by_name.get('default', 70)
                for key, value in gui_g.s.minimal_fuzzy_score_by_name.items():
                    key = key.lower()
                    if key in folder_name_cleaned.lower() or key in file_name_cleaned.lower():
                        minimal_score = value
                        break

                if fuzz_score >= minimal_score:
                    with open(entry.path, 'r', encoding='utf-8') as file:
                        for line in file:
                            if line.startswith('URL='):
                                returned_urls[0] = line.replace('URL=', '').strip()
                                return True
                self.logger.debug(f'Fuzzy compare minimal score was: {minimal_score}')
            return False

        if self.core is None:
            return ''
        egs = self.core.egs
        read_urls = ['']
        entries = os.scandir(parent)
        if any(read_from_url_file(entry, folder, read_urls) for entry in entries):
            found_url = read_urls[0]
        else:
            found_url = egs.get_marketplace_product_url(asset_slug=clean_ue_asset_name(folder))
        try:
            if check_if_valid and egs is not None and not egs.is_valid_url(found_url):
                found_url = ''
        except (Exception, ):  # trap all exceptions on connection
            message = f'Request timeout when accessing {found_url}\n.Operation is stopped, check you internet connection or try again later.',
            self.logger.warning(message)
            found_url = ''
        return found_url

    def silent_yesno(self, message: str) -> bool:
        """
        Ask the user a yes/no box and return the answer ONLY if the silent mode is NOT enabled.
        :param message: message to display.
        :return: True if the user answered yes, False otherwise.
        """
        if self._silent_mode:
            return True
        else:
            return gui_f.box_yesno(message)

    def silent_message(self, message: str, level='info') -> None:
        """
        Display a message box ONLY if the silent mode is NOT enabled.
        :param message: message to display.
        :param level: level of the message.

        Notes:
            This function must be called FROM this class to use the right logger. It can't be replaced by a call to gui_f.box_message
        """
        level_lower = level.lower()

        if self._silent_mode:
            if level_lower == 'warning':
                self.logger.warning(message)
            elif level_lower == 'error':
                self.logger.error(message)
            else:
                self.logger.info(message)
        else:
            gui_f.box_message(message, level=level)

    def scan_for_assets(self, folder_list: list = None, from_add_button: bool = False) -> None:
        """
        Scan the folders to find files that can be loaded.
        :param folder_list: list of folders to scan. If empty, use the folders in the config file.
        :param from_add_button: whether the call has been done from the "add" button or not.
        """

        def _fix_folder_structure(content_folder_name: str = gui_g.s.ue_asset_content_subfolder):
            """
            Fix the folder structure by moving all the subfolders inside a "Content" subfolder.
            :param content_folder_name: name of the subfolder to create.
            """
            if self.silent_yesno(
                f'The folder {parent_folder} seems to be a valid UE folder but with a bad structure. Do you want to move all its subfolders inside a "{content_folder_name}" subfolder ?'
            ):
                content_folder = path_join(parent_folder, content_folder_name)
                if not os.path.isdir(content_folder):
                    os.makedirs(content_folder, exist_ok=True)
                    for entry_p in os.scandir(parent_folder):
                        if entry_p.name != content_folder_name:
                            path_p = entry_p.path
                            shutil.move(path_p, content_folder)
                            if path_p in folder_to_scan:
                                folder_to_scan.remove(path_p)
                msg_p = f'-->Found {parent_folder}. The folder has been restructured as a valid UE folder'
                self.logger.debug(msg_p)
                # if full_folder in folder_to_scan:
                #     folder_to_scan.remove(full_folder)
                if parent_folder not in folder_to_scan:
                    folder_to_scan.append(parent_folder)

        data_from_valid_folders = {}
        invalid_folders = []
        folder_to_scan = folder_list if (folder_list is not None and len(folder_list) > 0) else gui_g.s.folders_to_scan
        if not from_add_button:
            if gui_g.s.testing_switch == 2:  # here, do_not_ask is used to detect if the caller is the "add" button and not the "scan" button
                # noinspection GrazieInspection
                folder_to_scan = [
                    'G:/Assets/pour UE/02 Warez/Battle Royale Island Pack',  # # test folder n'existe pas OK
                    'G:/Assets/pour UE/02 Warez/Plugins/Riverology UE_5',  # OK
                    'G:/Assets/pour UE/02 Warez/Environments/Elite_Landscapes_Desert_II',  # OK
                    'G:/Assets/pour UE/02 Warez/Characters/Female/FurryS1 Fantasy Warrior',  # OK
                ]  # ETAPEOK
            elif gui_g.s.testing_switch == 3:
                # noinspection GrazieInspection
                folder_to_scan = [
                    'G:/Assets/pour UE/02 Warez/Characters/Female/FurryS1 Fantasy Warrior',  # update ERREUR APRES l'update dans la BD
                    'G:/Assets/pour UE/02 Warez/Plugins/Riverology UE_5',  # update
                    'G:/Assets/pour UE/02 Warez/Environments/Battle Royale Island Pack',  # new OK
                    'G:/Assets/pour UE/02 Warez/Environments/Elite_Landscapes_Desert_II',  # update
                ]
            elif gui_g.s.testing_switch == 4:
                # noinspection GrazieInspection
                folder_to_scan = [
                    'G:/Assets/pour UE/02 Warez/Animations/Female Movement Animset Pro 4.26',  # new
                    'G:/Assets/pour UE/02 Warez/Plugins/Riverology UE_5',  # update
                    'G:/Assets/pour UE/02 Warez/Environments/Battle Royale Island Pack',  # update
                ]
        if not from_add_button and (
            len(folder_to_scan) > 1 and not gui_f.box_yesno(
                'Specified Folders to scan saved in the config file will be processed.\nSome assets will be added to the table and the process could take come time.\nDo you want to continue ?'
            )
        ):
            return
        self._silent_mode = gui_f.box_yesno(
            f'Do you want to run the scan silently ?\nIt will use choices by default and avoid user confirmation dialogs.'
        )
        if gui_g.s.offline_mode:
            self.silent_message('You are in offline mode, Scraping and scanning features are not available')
            return
        if self.core is None:
            gui_f.from_cli_only_message('URL Scraping and scanning features are only accessible', show_dialog=not self._silent_mode)
            return
        if not folder_to_scan:
            self.silent_message('No folder to scan. Please add some in the config file', level='warning')
            return
        if gui_g.s.check_asset_folders:
            self.clean_asset_folders()

        data_table = self.editable_table  # shortcut
        gui_f.create_file_backup(data_table.data_source, backup_to_keep=1, suffix='BEFORE_SCAN')
        pw = gui_f.show_progress(self, text='Scanning folders for new assets', width=500, height=120, show_progress_l=False, show_btn_stop_l=True)
        while folder_to_scan:
            full_folder = folder_to_scan.pop()
            full_folder = os.path.abspath(full_folder)
            # full_folder_abs = os.path.abspath(full_folder)
            folder_name = os.path.basename(full_folder)
            parent_folder = os.path.dirname(full_folder)
            folder_name_lower = folder_name.lower()

            msg = f'Scanning folder {full_folder}'
            self.logger.info(msg)
            if not pw.update_and_continue(value=0, text=f'Scanning folder:\n{gui_fn.shorten_text(full_folder, 70)}'):
                gui_f.close_progress(self)
                return

            if os.path.isdir(full_folder):
                if self.core.scan_assets_logger:
                    self.core.scan_assets_logger.info(msg)

                folder_is_valid = folder_name_lower in gui_g.s.ue_valid_asset_subfolder
                parent_could_be_valid = folder_name_lower in gui_g.s.ue_invalid_content_subfolder or folder_name_lower in gui_g.s.ue_possible_asset_subfolder
                version = get_version_from_path(full_folder)
                supported_versions = 'UE_' + version if version else ''
                if folder_is_valid:
                    folder_name = os.path.basename(parent_folder)
                    parent_folder = os.path.dirname(parent_folder)
                    path = os.path.dirname(full_folder)
                    pw.set_text(f'{folder_name} as a valid folder.\nChecking asset url...')
                    msg = f'-->Found {folder_name} as a valid project'
                    self.logger.info(msg)
                    marketplace_url = self.search_for_url(folder=folder_name, parent=parent_folder, check_if_valid=False)
                    grab_result = ''
                    comment = ''
                    if marketplace_url:
                        try:
                            grab_result = GrabResult.NO_ERROR.name if self.core.egs.is_valid_url(marketplace_url) else GrabResult.NO_RESPONSE.name
                        except (Exception, ) as error:  # trap all exceptions on connection
                            self.add_error(error)
                            self.silent_message(
                                f'Request timeout when accessing {marketplace_url}\n.Operation is stopped, check you internet connection or try again later.',
                                level='warning'
                            )
                            gui_f.close_progress(self)
                            # grab_result = GrabResult.TIMEOUT.name
                            return
                    data_from_valid_folders[folder_name] = {
                        'path': path,
                        'asset_type': UEAssetType.Asset,
                        'marketplace_url': marketplace_url,
                        'grab_result': grab_result,
                        'comment': comment,
                        'supported_versions': supported_versions,
                        'downloaded_size': gui_g.s.unknown_size  # as it's local, it's downloaded, so we add a size
                    }
                    if self.core.scan_assets_logger:
                        self.core.scan_assets_logger.info(msg)
                    continue
                elif parent_could_be_valid:
                    # the parent folder contains some UE folders but with a bad structure
                    _fix_folder_structure(gui_g.s.ue_asset_content_subfolder)

                try:
                    for entry in os.scandir(full_folder):
                        entry_is_valid = entry.name.lower() not in gui_g.s.ue_invalid_content_subfolder
                        comment = ''
                        if entry.is_file():
                            asset_type = UEAssetType.Asset
                            extension_lower = os.path.splitext(entry.name)[1].lower()
                            filename_lower = os.path.splitext(entry.name)[0].lower()
                            # check if full_folder contains a "data" sub folder
                            if filename_lower == gui_g.s.ue_manifest_filename.lower() or extension_lower in gui_g.s.ue_valid_file_ext:
                                path = full_folder
                                has_valid_folder_inside = any(
                                    os.path.isdir(path_join(full_folder, folder_inside)) for folder_inside in gui_g.s.ue_valid_manifest_subfolder
                                )
                                if filename_lower == gui_g.s.ue_manifest_filename.lower():
                                    manifest_is_valid = False
                                    app_name_from_manifest = ''
                                    if has_valid_folder_inside:
                                        folder_name = os.path.basename(full_folder)
                                        # the manifest file MUST be in a "two level" folder structure with a correct folder name
                                        manifest_infos = self.core.open_manifest_file(entry.path)
                                        app_name_from_manifest = manifest_infos.get('app_name', '')
                                        if app_name_from_manifest == folder_name:
                                            # we need to move to parent folder to get the real names because manifest files are inside a specific sub folder
                                            asset_type = UEAssetType.Manifest
                                            folder_name = os.path.basename(parent_folder)
                                            parent_folder = os.path.dirname(parent_folder)
                                            path = os.path.dirname(full_folder)
                                            manifest_is_valid = True
                                        else:
                                            # we miss a folder between the folder with the "asset name" and the manifest file
                                            # we create a subfolder with the asset name and move the manifest file and the content inside
                                            parent_folder = full_folder
                                            _fix_folder_structure(app_name_from_manifest)
                                            continue
                                    if not manifest_is_valid:
                                        msg = f'{full_folder} has a manifest file but without a data or a valid subfolder folder.It will be considered as an asset'
                                        self.logger.warning(msg)
                                        comment = msg
                                        if app_name_from_manifest:
                                            comment += f'\nThe manifest file and the folder should be moved inside a folder named:\n{app_name_from_manifest}'
                                else:
                                    asset_type = UEAssetType.Plugin if extension_lower == '.uplugin' else UEAssetType.Asset
                                marketplace_url = self.search_for_url(folder=folder_name, parent=parent_folder, check_if_valid=False)
                                grab_result = ''
                                if marketplace_url:
                                    try:
                                        grab_result = GrabResult.NO_ERROR.name if self.core.egs.is_valid_url(
                                            marketplace_url
                                        ) else GrabResult.TIMEOUT.name
                                    except (Exception, ) as error:  # trap all exceptions on connection
                                        self.add_error(error)
                                        self.silent_message(
                                            f'Request timeout when accessing {marketplace_url}\n.Operation is stopped, check you internet connection or try again later.',
                                            level='warning'
                                        )
                                        grab_result = GrabResult.TIMEOUT.name
                                data_from_valid_folders[folder_name] = {
                                    'path': path,
                                    'asset_type': asset_type,
                                    'marketplace_url': marketplace_url,
                                    'grab_result': grab_result,
                                    'comment': comment,
                                    'supported_versions': supported_versions,
                                    'downloaded_size': gui_g.s.unknown_size  # as it's local, it's downloaded, so we add a size
                                }
                                if grab_result != GrabResult.NO_ERROR.name or not marketplace_url:
                                    invalid_folders.append(full_folder)
                                    msg = f'-->{folder_name} is an invalid folder'
                                    if self.core.scan_assets_logger:
                                        self.core.scan_assets_logger.warning(msg)
                                else:
                                    msg = f'-->Found {folder_name} as a valid project containing a {asset_type.name}' if extension_lower in gui_g.s.ue_valid_file_ext else f'-->Found {folder_name} containing a {asset_type.name}'
                                    if self.core.scan_assets_logger:
                                        self.core.scan_assets_logger.info(msg)
                                self.logger.debug(msg)
                                # remove all the subfolders from the list of folders to scan
                                folder_to_scan = [folder for folder in folder_to_scan if not folder.startswith(full_folder)]
                                continue

                        # add subfolders to the list of folders to scan
                        elif entry.is_dir() and entry_is_valid:
                            folder_to_scan.append(entry.path)
                except FileNotFoundError as error:
                    self.add_error(error)
                    self.logger.debug(f'{full_folder} has been removed during the scan')

            # sort the list to have the parent folder POPED (by the end) before the subfolders
            folder_to_scan = sorted(folder_to_scan, key=lambda x: len(x), reverse=True)

        msg = '\n\nValid folders found after scan:\n'
        self.logger.info(msg)
        if self.core.scan_assets_logger:
            self.core.scan_assets_logger.info(msg)
        date_added = datetime.now().strftime(DateFormat.csv)
        # Note:
        #   we need to create fake ids here because all the datatable will be saved in database in self.scrap_asset()
        #   BEFORE scraping and getting real Ids
        temp_id = gui_g.s.temp_id_prefix + gui_fn.create_uid()
        row_data = {'Asset_id': temp_id, 'Date added': date_added, 'Creation date': date_added, 'Update date': date_added, 'Added manually': True}
        folders_count = len(data_from_valid_folders)
        pw.reset(new_text='Scraping data and updating assets', new_max_value=folders_count)
        row_added = 0
        data_table.is_scanning = True
        count = 0
        # copy_col_index = data_table.get_col_index(gui_g.s.index_copy_col_name)
        for folder_name, folder_data in data_from_valid_folders.items():
            df = data_table.get_data(df_type=DataFrameUsed.UNFILTERED)  # put the df here to have it updated after each row
            marketplace_url = folder_data['marketplace_url']
            self.logger.info(f'{folder_name} : {folder_data["asset_type"].name} at {folder_data["path"]} with marketplace_url {marketplace_url} ')
            # set default values for the row, some will be replaced after scraping
            row_data.update(
                {
                    'App name': folder_name,
                    'Origin': folder_data['path'],
                    'Url': folder_data['marketplace_url'],
                    'Grab result': folder_data['grab_result'],
                    'Category': folder_data['asset_type'].category_name,
                    'Comment': folder_data['comment'],
                    'Supported versions': folder_data.get('supported_versions', ''),
                    'Added manually': True,
                    'Downloaded size': folder_data['downloaded_size'],
                }
            )
            row_index = -1
            text = f'Checking {folder_name}'
            existing_data_in_row = {}
            # check if the row already exists
            try:
                # we try to get the indexes if value already exists in column 'Origin' for a pandastable
                rows_serie = df.loc[lambda x: x['Origin'].str.lower() == folder_data['path'].lower()]
                row_indexes = rows_serie.index  # returns a list of indexes. It should contain only 1 value
                if not row_indexes.empty:
                    # FOUND, we update the row
                    # we pass the rows_serie we've found to get the existing values. it has only one row, so row_index is always 1
                    existing_data_in_row = self._get_existing_data_in_row(row_index=1, df=rows_serie)
                    row_index = existing_data_in_row.pop('row_index')
                    text = f'Updating row index {row_index}.\nExisting Asset_id is {existing_data_in_row["asset_id"]}'
                    self.logger.info(f"{text} with path {folder_data['path']}")
            except (IndexError, ValueError) as error:
                self.add_error(error)
                self.logger.warning(f'Error when checking the existence for {folder_name} at {folder_data["path"]}: error {error!r}')
                invalid_folders.append(folder_data['path'])
                text = f'An Error occured when cheking {folder_name}'
                pw.set_text(text)
                continue
            is_adding = row_index == -1
            if is_adding:
                # NOT FOUND, we add a new row
                _, row_index = data_table.create_row(row_data=row_data, do_not_save=True)
                text = f'Adding "{folder_name}" at row index {row_index}'
                self.logger.info(f"{text} with path {folder_data['path']}")
                row_added += 1
            count += 1
            if not pw.update_and_continue(value=count, max_value=folders_count, text=text):
                break
            # need to keep the local value created when adding an existing asset
            forced_data = existing_data_in_row.copy()
            # set the data the must be kept after the scraping
            forced_data.update(
                {
                    # these value will overwrite those returned by existing_data_in_row()
                    'origin': folder_data['path'],
                    'asset_url': folder_data['marketplace_url'],
                    'grab_result': folder_data['grab_result'],
                    'added_manually': True,
                    'category': folder_data['asset_type'].category_name,
                    'downloaded_size': folder_data['downloaded_size']
                }
            )
            if forced_data.get('comment', ''):
                forced_data['comment'] += '\n' + folder_data['comment']

            if folder_data['grab_result'] == GrabResult.NO_ERROR.name:
                try:
                    self.scrap_asset(
                        marketplace_url=marketplace_url,
                        row_index=row_index,
                        forced_data=forced_data,
                        update_dataframe=False,
                        check_unicity=is_adding,
                        is_silent=self._silent_mode,
                    )  # !! IMPORTANT: update_row() and save in database already DONE inside scrap_asset()
                except ReadTimeout as error:
                    self.add_error(error)
                    self.silent_message(
                        f'Request timeout when accessing {marketplace_url}\n.Operation is stopped, check you internet connection or try again later.',
                        level='warning'
                    )
                    forced_data['grab_result'] = GrabResult.TIMEOUT.name
                    data_table.update_row(row_number=row_index, ue_asset_data=forced_data, convert_row_number_to_row_index=False)
                    data_table.add_to_rows_to_save(row_index)  # done inside self.must_save = True
        pw.hide_progress_bar()
        pw.hide_btn_stop()
        pw.set_text('Updating the table. Could take a while...')
        data_table.is_scanning = False
        data_table.update(update_format=True)
        data_table.update_col_infos()
        gui_f.close_progress(self)

        if invalid_folders:
            result = '\n'.join(invalid_folders)
            result = f'The following folders have produce invalid results during the scan:\n{result}'
            if gui_g.WindowsRef.display_content is None:
                file_name = f'scan_folder_results_{datetime.now().strftime(DateFormat.us_short)}.txt'
                gui_g.WindowsRef.display_content = DisplayContentWindow(
                    title='UEVM: status command output', quit_on_close=False, result_filename=file_name
                )
                gui_g.WindowsRef.display_content.display(result)
                gui_f.make_modal(gui_g.WindowsRef.display_content)
            self.logger.warning(result)

    def _scrap_from_url(self, marketplace_url: str, app_name: str = '') -> dict:
        """
        Scrap the data from a marketplace_url.
        :param marketplace_url: marketplace_url to scrap.
        :param app_name: name of the app to scrap (Optional).
        :return: data scraped from the marketplace_url Or None if the marketplace_url is invalid.
        """
        is_ok = False
        asset_data = None
        # check if the marketplace_url is a marketplace marketplace_url
        ue_marketplace_url = self.core.egs.get_marketplace_product_url()
        if ue_marketplace_url.lower() in marketplace_url.lower():
            # get the data from the marketplace marketplace_url
            asset_data = self.core.egs.get_asset_data_from_marketplace(marketplace_url)
            if not asset_data or asset_data.get('grab_result', None) != GrabResult.NO_ERROR.name or not asset_data.get('id', ''):
                msg = f'Failed to grab data from {marketplace_url}'
                gui_f.box_message(msg, level='warning', show_dialog=not self._silent_mode)
                if self.core.notfound_logger:
                    self.core.notfound_logger.info(msg)
                return {}
            api_product_url = self.core.egs.get_api_product_url(asset_data['id'])
            if self.ue_asset_scraper is None:
                # using a global scraper to avoid creating a new one and a new db connection for each row
                self.ue_asset_scraper = UEAssetScraper(
                    datasource_filename=self.editable_table.data_source,
                    use_database=self.editable_table.is_using_database,
                    start=0,
                    assets_per_page=1,  # scrap only one asset
                    max_threads=1,
                    save_parsed_to_files=True,
                    load_from_files=False,
                    store_ids=False,  # useless for now
                    core=self.core  # VERY IMPORTANT: pass the core object to the scraper to keep the same session
                )
            else:
                # next line because the scraper is initialized only at startup
                self.ue_asset_scraper.keep_intermediate_files = gui_g.s.debug_mode
            self.ue_asset_scraper.get_data_from_url(api_product_url)
            asset_data = self.ue_asset_scraper.pop_last_scraped_data()  # returns a list of one element
            is_ok = asset_data is not None and len(asset_data) > 0
        if not is_ok:
            asset_data = None
            msg = f'The asset url {marketplace_url} is invalid and could not be scraped for this row'
            if self.core.notfound_logger:
                self.core.notfound_logger.info(f'{app_name}: invalid url "{marketplace_url}"')
            gui_f.box_message(msg, level='warning', show_dialog=not self._silent_mode)
            # change the grab result to CONTENT_NOT_FOUND in database
            if self.is_using_database and self.ue_asset_scraper:
                self.ue_asset_scraper.asset_db_handler.update_asset('grab_result', GrabResult.CONTENT_NOT_FOUND.name, asset_id=app_name)
        return asset_data[0] if asset_data is not None else None

    def scrap_range(self) -> None:
        """
        Scrap a range of assets in the table.
        :return:
        """
        data_table = self.editable_table  # shortcut
        df = data_table.get_data(df_type=DataFrameUsed.UNFILTERED)
        min_val = 0
        max_val = len(df) - 1
        start = simpledialog.askinteger(
            parent=self,  #
            title='Select the starting asset',  #
            prompt=f'INDEX (not row number) between {min_val} and {max_val - 1})',  #
            minvalue=min_val,  #
            maxvalue=max_val - 1
        )
        if start is not None:
            end = simpledialog.askinteger(
                parent=self,
                title='Select the ending asset',  #
                prompt=f'INDEX (not row number) between {start + 1} and {max_val})',  #
                minvalue=start + 1,  #
                maxvalue=max_val
            )
            if end is not None:
                self._silent_mode = gui_f.box_yesno(
                    f'Do you want to run the scan silently ?\nIt will use choices by default and avoid user confirmation dialogs.'
                )
                start = max(min_val, start)
                end = min(max_val, end)
                all_row_numbers = list(range(start, end))
                self.scrap_asset(row_numbers=all_row_numbers, check_unicity=False, is_silent=self._silent_mode)
                self.ue_asset_scraper = None

    def scrap_asset(
        self,
        marketplace_url: str = None,
        row_index: int = -1,
        row_numbers: list = None,
        forced_data: {} = None,
        update_dataframe: bool = True,
        check_unicity: bool = False,
        is_silent: bool = False,
    ) -> None:
        """
        Scrap the data for the current row or a given marketplace_url.
        :param marketplace_url: marketplace_url to scrap.
        :param row_numbers: list a row numbers to scrap. If None, will use the selected rows.
        :param row_index: (real) index of the row to scrap. If >= 0, will scrap only this row and will ignore the marketplace_url and row_numbers.
        :param forced_data: if not None, all the key in forced_data_initial will replace the scraped data.
        :param update_dataframe: whether to update the dataframe after scraping.
        :param check_unicity: whether to check if the data are unique and ask the user to update the row if not.
        :param is_silent: whether to show message boxes or not.
        """
        # by default (i.e. self.silent_mode sis not changed), we show the following message boxes
        if gui_g.s.offline_mode:
            self.silent_message('You are in offline mode, Scraping and scanning features are not available')
            return
        if self.core is None:
            gui_f.from_cli_only_message('URL Scraping and scanning features are only accessible', show_dialog=not self._silent_mode)
            return
        self._silent_mode = is_silent
        if forced_data is None:
            forced_data = {}
        is_unique = not check_unicity  # by default, we consider that the data are unique
        data_table = self.editable_table  # shortcut
        data_table.save_data()  # save the data before scraping because we will update the row(s) and override non saved changes
        if not row_numbers:
            row_numbers = data_table.multiplerowlist
            use_range = False
            self._silent_mode = False if not is_silent else True  # NO silent_mode only if it has explicitly been set to False
        else:
            use_range = True
        if row_index < 0 and marketplace_url is None and row_numbers is None and len(row_numbers) < 1:
            self.silent_message('You must select a row first', level='warning')
        if row_index >= 0:
            # a row index has been given, we scrap only this row
            row_indexes = [row_index]
        elif use_range:
            # convert row numbers to row indexes
            row_indexes = [
                data_table.get_real_index(row_number, add_page_offset=False, df_type=DataFrameUsed.UNFILTERED) for row_number in row_numbers
            ]
        else:
            # convert row numbers to row indexes
            row_indexes = [data_table.get_real_index(row_number) for row_number in row_numbers]
        pw = None
        row_count = len(row_indexes)

        if self.is_using_database:
            tags_count_saved = data_table.db_handler.get_rows_count('tags')
            rating_count_saved = data_table.db_handler.get_rows_count('ratings')
        else:
            tags_count_saved, rating_count_saved = 0, 0
        if marketplace_url is None:
            base_text = "Scraping asset's data. Could take a while..."
            if row_count > 1:
                pw = gui_f.show_progress(
                    self, text=base_text, max_value_l=row_count, width=450, height=150, show_progress_l=True, show_btn_stop_l=True
                )
            for count, row_index in enumerate(row_indexes):
                if row_index < 0:
                    # a conversion error in get_real_index has occured
                    continue
                row_data = data_table.get_row(row_index, return_as_dict=True)
                marketplace_url = row_data['Url']
                asset_slug_from_url = marketplace_url.split('/')[-1]
                # we keep UrlSlug here because it can arise from the scraped data
                asset_slug_from_row = row_data.get('urlSlug', '') or row_data.get('Asset slug', '')
                if asset_slug_from_row and asset_slug_from_url and not asset_slug_from_row.startswith(
                    gui_g.s.duplicate_row_prefix
                ) and asset_slug_from_url != asset_slug_from_row:
                    msg = f'The Asset slug from the given Url {asset_slug_from_url} is different from the existing data {asset_slug_from_row}.'
                    self.logger.warning(msg)
                    # we use existing_url and not asset_data['asset_url'] because it could have been corrected by the user
                    if gui_f.box_yesno(
                        f'{msg}.\nDo you wan to create a new Url with {asset_slug_from_row} and use it for scraping ?\nIf no, the given url with {asset_slug_from_url} will be used',
                        show_dialog=not self._silent_mode
                    ):
                        marketplace_url = self.core.egs.get_marketplace_product_url(asset_slug_from_row)
                        col_index = data_table.get_col_index('Url')
                        data_table.update_cell(row_index, col_index, marketplace_url, convert_row_number_to_row_index=False)
                text = base_text + f'\n Row index {row_index}: scraping {gui_fn.shorten_text(marketplace_url)}'
                # if pw and not pw.update_and_continue(value=count, text=text, max_value=row_count):  # uses value and max_value here because increment does not work well with multiple rows
                if pw and not pw.update_and_continue(increment=1, text=text):
                    gui_f.close_progress(self)
                    return
                asset_data = self._scrap_from_url(marketplace_url)
                if not asset_data and row_data['Added manually']:
                    # it's a local asset, we can try to get an url file from the local folder
                    local_folder = row_data['Origin']
                    folder_name = os.path.basename(local_folder)
                    parent_folder = os.path.dirname(local_folder)
                    marketplace_url = self.search_for_url(folder=folder_name, parent=parent_folder, check_if_valid=False)
                    asset_data = self._scrap_from_url(marketplace_url)
                if asset_data:
                    if forced_data:
                        asset_forced_data = forced_data.copy()
                    else:
                        asset_forced_data = {}
                    if self.core.verbose_mode or gui_g.s.debug_mode:
                        debug_parsed_data(asset_data, self.editable_table.data_source_type)
                    if check_unicity:  # note: only done when ADDING a row
                        is_unique, asset_data = self._check_unicity(asset_data)
                    else:
                        # when updating, check if the asset_id if this asset is a "local" asset
                        existing_data = self._get_existing_data_in_row(row_index=row_index)
                        asset_id = existing_data.get('asset_id', '')
                        if asset_id and asset_id.startswith(gui_g.s.duplicate_row_prefix):
                            # we KEEP some existing values (the "local" ones) when updating
                            asset_forced_data = existing_data.copy()

                    for key, value in asset_forced_data.items():
                        if str(value) not in gui_g.s.cell_is_nan_list + [gui_g.s.missing_category]:
                            asset_data[key] = value
                    if is_unique or gui_f.box_yesno(
                        f'The scraped data for row index {row_index} ({asset_data["title"]}) is not unique.\nDo you want to create a row using tthis data ?\nIf No, the row will be skipped',
                        show_dialog=not self._silent_mode
                    ):
                        data_table.update_row(row_index, ue_asset_data=asset_data, convert_row_number_to_row_index=False)
                        if self.is_using_database:
                            self.ue_asset_scraper.asset_db_handler.set_assets(asset_data, update_progress=False)
                else:
                    col_index = data_table.get_col_index('Grab result')
                    data_table.update_cell(row_index, col_index, GrabResult.CONTENT_NOT_FOUND.name, convert_row_number_to_row_index=False)
            gui_f.close_progress(self)
            if row_count > 1:
                message = f'All Datas for {row_count} rows have been updated from the marketplace.'
            else:
                message = f'Data for row index {row_index} have been updated from the marketplace.'
            tags_message = ''
            if self.is_using_database:
                tags_count = data_table.db_handler.get_rows_count('tags')
                rating_count = data_table.db_handler.get_rows_count('ratings')
                tags_message = f'\n{tags_count - tags_count_saved} tags and {rating_count - rating_count_saved} ratings have been added to the database.'
            self.silent_message(message + tags_message)
        else:
            asset_data = self._scrap_from_url(marketplace_url)
            if asset_data:
                if self.core.verbose_mode or gui_g.s.debug_mode:
                    debug_parsed_data(asset_data, self.editable_table.data_source_type)
                if check_unicity:  # note: only done when ADDING a row
                    is_unique, asset_data = self._check_unicity(asset_data)
                if is_unique or gui_f.box_yesno(
                    f'The data for row index {row_index} ({asset_data["title"]}) is not unique.\nDo you want to update the row with the new data ?\nIf No, the row will be skipped',
                    show_dialog=not self._silent_mode
                ):
                    if forced_data is not None:
                        for key, value in forced_data.items():
                            if str(value) not in gui_g.s.cell_is_nan_list:
                                asset_data[key] = value
                    data_table.update_row(row_index, ue_asset_data=asset_data, convert_row_number_to_row_index=False)
                    if self.is_using_database:
                        self.ue_asset_scraper.asset_db_handler.set_assets(asset_data)
            else:
                col_index = data_table.get_col_index('Grab result')
                data_table.update_cell(row_index, col_index, GrabResult.CONTENT_NOT_FOUND.name, convert_row_number_to_row_index=False)

        if update_dataframe:
            data_table.update()

    def _get_existing_data_in_row(self, row_index: int = -1, df: pd.DataFrame = None) -> dict:
        if df is None:
            df = self.editable_table.get_data(df_type=DataFrameUsed.UNFILTERED)
            idx = df.loc[row_index, gui_g.s.index_copy_col_name]  # important to get the value before updating the row
            row_index = idx
        else:
            idx = 0
            row_index = df.index[0]
        df_row = df.iloc[idx]
        existing_data = {
            # create an id field from the asset_id to be able to update the corresponding row in the database (id is the primary key)
            'row_index': row_index,  # need to keep the index of the row to update in the datatable. Will be suppressed later
            'id': df_row.loc['Asset_id'],
            'asset_id': df_row.loc['Asset_id'],
            'asset_slug': df_row.loc['Asset slug'],
            'comment': df_row.loc['Comment'],
            'origin': df_row.loc['Origin'],
            'added_manually': df_row.loc['Added manually'],
            'category': df_row.loc['Category'],
            'downloaded_size': df_row.loc['Downloaded size']
        }
        # need to keep the local value created when adding an existing asset
        return existing_data

    def _check_unicity(self, asset_data: {}) -> (bool, dict):
        """
        Check if the given asset_data is unique in the table. If not, will change the asset_id and/or the asset_slug to avoid issue.
        :param asset_data: asset data to check.
        :return: asset_data with the updated asset_id and/or asset_slug.
        """
        is_unique = True
        df = self.editable_table.get_data(df_type=DataFrameUsed.UNFILTERED)
        asset_id = asset_data['asset_id']
        asset_slug = asset_data['asset_slug']
        rows_serie_for_id = df.loc[lambda x: x['Asset_id'] == asset_id]
        rows_serie_for_slug = df.loc[lambda x: x['Asset slug'].str.lower() == asset_slug.lower()]
        if not rows_serie_for_id.empty:
            is_unique = False
            new_asset_id = gui_g.s.duplicate_row_prefix + gui_fn.create_uid()
            asset_data['asset_id'] = new_asset_id
            asset_data['id'] = new_asset_id
            self.logger.warning(
                f'A row with Asset_id={asset_id} already exists. To avoid issue, the Asset_id of the new row has been set to {new_asset_id}'
            )
        if not rows_serie_for_slug.empty:
            is_unique = False
            new_slug = gui_g.s.duplicate_row_prefix + asset_slug
            asset_data['asset_slug'] = new_slug
            self.logger.warning(
                f'A row with "Asset slug"={asset_slug} already exists. To avoid issue, the "Asset slug" of the new row has been set to {new_slug}'
            )
        return is_unique, asset_data

    def toggle_pagination(self, forced_value: bool = None) -> None:
        """
        Toggle pagination. Will change the navigation buttons states when pagination is changed.
        :param forced_value: if not None, will force the pagination to the given value.
        """
        data_table = self.editable_table  # shortcut
        if forced_value is not None:
            data_table.pagination_enabled = forced_value
        else:
            data_table.pagination_enabled = not data_table.pagination_enabled
        data_table.update_page()
        if not data_table.pagination_enabled:
            self._frm_toolbar.btn_toggle_pagination.config(text='Enable  Pagination')
        else:
            self._frm_toolbar.btn_toggle_pagination.config(text='Disable Pagination')
        self.update_controls_state()  # will also update buttons status

    def first_item(self) -> None:
        """
        Show the first page of the table.
        """
        data_table = self.editable_table  # shortcut
        if data_table.pagination_enabled:
            data_table.first_page()
        else:
            data_table.move_to_row(0)
            data_table.yview_moveto(0)
            data_table.redrawVisible()
        self.update_controls_state()

    def last_item(self) -> None:
        """
        Show the last page of the table.
        """
        data_table = self.editable_table  # shortcut
        if data_table.pagination_enabled:
            data_table.last_page()
        else:
            data_table.move_to_row(len(data_table.get_data()) - 1)
            data_table.yview_moveto(1)
            data_table.redrawVisible()
        self.update_controls_state()

    def prev_page(self) -> None:
        """
        Show the previous page of the table.
        """
        self.editable_table.prev_page()
        self.update_controls_state()

    def next_page(self) -> None:
        """
        Show the next page of the table.
        """
        self.editable_table.next_page()
        self.update_controls_state()

    def prev_asset(self) -> None:
        """
        Move to the previous asset in the table.
        """
        self.editable_table.prev_row()
        self.update_controls_state()

    def next_asset(self) -> None:
        """
        Move to the next asset in the table.
        """
        self.editable_table.next_row()
        self.update_controls_state()

    # noinspection DuplicatedCode
    def toggle_actions_panel(self, force_showing: bool = None) -> None:
        """
        Toggle the visibility of the Actions panel.
        :param force_showing: whether to will force showing the actions panel, if False, will force hiding it.If None, will toggle the visibility.
        """
        if force_showing is None:
            force_showing = not self._frm_control.winfo_ismapped()
        if force_showing:
            self._frm_control.pack(side=tk.RIGHT, fill=tk.BOTH)
            self._frm_toolbar.btn_toggle_controls.config(text=' Hide Actions')
            # self._frm_toolbar.btn_toggle_options.config(state=tk.DISABLED)
        else:
            self._frm_control.pack_forget()
            self._frm_toolbar.btn_toggle_controls.config(text='Show Actions')
            # self._frm_toolbar.btn_toggle_options.config(state=tk.NORMAL)

    # noinspection DuplicatedCode
    def toggle_options_panel(self, force_showing: bool = None) -> None:
        """
        Toggle the visibility of the Options panel.
        :param force_showing: whether to will force showing the options panel, if False, will force hiding it.If None, will toggle the visibility.
        """
        # noinspection DuplicatedCode
        if force_showing is None:
            force_showing = not self._frm_option.winfo_ismapped()
        if force_showing:
            self._frm_option.pack(side=tk.RIGHT, fill=tk.BOTH)
            self._frm_toolbar.btn_toggle_options.config(text=' Hide Options')
            # self._frm_toolbar.btn_toggle_controls.config(state=tk.DISABLED)
        else:
            self._frm_option.pack_forget()
            self._frm_toolbar.btn_toggle_options.config(text='Show Options')
            # self._frm_toolbar.btn_toggle_controls.config(state=tk.NORMAL)

    def update_controls_state(self, update_title=False) -> None:
        """
        Update the controls and redraw the table.
        :param update_title: whether to update the window title.
        """
        if update_title:
            self.title(gui_g.s.app_title_long)

        if self._frm_toolbar is None:
            return

        data_table = self.editable_table
        max_index = len(data_table.get_data())
        current_row = data_table.get_selected_row_fixed()
        current_row_index = data_table.add_page_offset(current_row) if current_row is not None else -1

        gui_f.update_widgets_in_list(data_table.must_save, 'table_has_changed')
        # gui_f.update_widgets_in_list(data_table.must_save, 'table_has_changed', text_swap={'normal': 'Save *', 'disabled': 'Save  '})
        gui_f.update_widgets_in_list(current_row_index > 0, 'not_first_asset')
        gui_f.update_widgets_in_list(current_row_index < max_index - 1, 'not_last_asset')
        gui_f.update_widgets_in_list(not gui_g.s.offline_mode, 'not_offline')

        if not data_table.pagination_enabled:
            # ! keep the same variable names here !
            total_displayed = len(data_table.get_data(df_type=DataFrameUsed.AUTO))
            first_item_text = 'First Asset'
            last_item_text = 'Last Asset'
            index_displayed = current_row_index
            gui_f.disable_widgets_in_list(gui_g.stated_widgets.get('not_first_page', []))
            gui_f.disable_widgets_in_list(gui_g.stated_widgets.get('not_last_page', []))
            gui_f.update_widgets_in_list(index_displayed > 0, 'not_first_item')
            gui_f.update_widgets_in_list(index_displayed < max_index - 1, 'not_last_item')
        else:
            # ! keep the same variable names here !
            total_displayed = data_table.total_pages
            index_displayed = data_table.current_page
            first_item_text = 'First Page'
            last_item_text = 'Last Page'
            gui_f.update_widgets_in_list(index_displayed > 1, 'not_first_item')
            gui_f.update_widgets_in_list(index_displayed > 1, 'not_first_page')
            gui_f.update_widgets_in_list(index_displayed < total_displayed, 'not_last_item')
            gui_f.update_widgets_in_list(index_displayed < total_displayed, 'not_last_page')

        # conditions based on info about the current asset
        row_is_selected = False
        is_owned = False
        is_added = False
        url = ''

        if current_row is not None:
            row_is_selected = len(data_table.multiplerowlist) > 0
            url = data_table.get_cell(current_row, data_table.get_col_index('Url'))
            is_added = data_table.get_cell(current_row, data_table.get_col_index('Added manually'))
            is_owned = data_table.get_cell(current_row, data_table.get_col_index('Owned'))
        gui_f.update_widgets_in_list(is_owned, 'asset_is_owned')
        gui_f.update_widgets_in_list(is_added, 'asset_added_mannually')
        gui_f.update_widgets_in_list(url != '', 'asset_has_url')
        gui_f.update_widgets_in_list(gui_g.UEVM_cli_ref, 'cli_is_available')
        gui_f.update_widgets_in_list(data_table.is_using_database, 'database_is_used')
        gui_f.update_widgets_in_list(not data_table.is_using_database, 'file_is_used')
        gui_f.update_widgets_in_list(row_is_selected, 'row_is_selected')
        gui_f.update_widgets_in_list(row_is_selected and not gui_g.s.offline_mode, 'row_is_selected_and_not_offline')
        gui_f.update_widgets_in_list(is_owned and not gui_g.s.offline_mode, 'asset_is_owned_and_not_offline')

        self._frm_toolbar.btn_first_item.config(text=first_item_text)
        self._frm_toolbar.btn_last_item.config(text=last_item_text)
        self._frm_toolbar.var_entry_current_item.set('{:04d}'.format(index_displayed))
        self._frm_toolbar.lbl_page_count.config(text=f'/{total_displayed:04d}')

    def update_data_source(self) -> None:
        """
        Update the data source name in the control frame.
        """
        self._frm_control.var_entry_data_source_name.set(self.editable_table.data_source)
        self._frm_control.var_entry_data_source_type.set(self.editable_table.data_source_type.name)

    def update_category_var(self) -> dict:
        """
        Update the category variable with the current categories in the data.
        :return: dict with the new categories list as value and the key is the name of the variable.
        """
        df = self.editable_table.get_data(df_type=DataFrameUsed.UNFILTERED)
        try:
            # if the file is empty or absent or invalid when creating the class, the data is empty, so no categories
            categories = list(df['Category'].cat.categories)
        except (AttributeError, TypeError, KeyError) as error:
            self.add_error(error)
            categories = []
        categories.insert(0, gui_g.s.default_value_for_all)
        try:
            # if the file is empty or absent or invalid when creating the class, the data is empty, so no categories
            grab_results = list(df['Grab result'].cat.categories)
        except (AttributeError, TypeError, KeyError) as error:
            self.add_error(error)
            grab_results = []
        grab_results.insert(0, gui_g.s.default_value_for_all)
        return {'categories': categories, 'grab_results': grab_results}

    def update_preview_info(self, row_number: int = -1):
        """
        Set the text to display in the preview frame about the number of rows.
        :param row_number: row number from a datatable. Will be converted into real row index.
        """

        def _add_text(text: str, tag: str = ''):
            self._frm_control.txt_info.insert(tk.END, text, tag, '\n')

        if self._frm_control is None:
            return
        text_box = self._frm_control.txt_info  # shortcut
        # we use tags to color the text
        text_box.tag_configure('blue', foreground='blue')
        text_box.tag_configure('orange', foreground='orange')
        text_box.delete('1.0', tk.END)

        data_table = self.editable_table  # shortcut
        df = data_table.get_data(df_type=DataFrameUsed.UNFILTERED)
        df_filtered = data_table.get_data(df_type=DataFrameUsed.FILTERED)
        row_count_filtered = len(df_filtered) if df_filtered is not None else 0
        row_count = len(df)
        idx = data_table.get_real_index(row_number)
        if idx >= 0:
            app_name = data_table.get_cell(row_number, data_table.get_col_index('Asset_id'))
            _add_text(f'Asset id: {app_name}')
            size = self.core.uevmlfs.get_asset_size(app_name)
            if size and size > 0:
                _add_text(f'Asset size: {gui_fn.format_size(size)}', 'blue')
            else:
                _add_text(f'Asset size: Clic on "Asset Info"', 'orange')
            downloaded_size = data_table.get_cell(row_number, data_table.get_col_index('Downloaded size'))
            if downloaded_size:
                _add_text('in Vault Cache or Local Folder', 'blue')
            else:
                _add_text('Not downloaded yet')
            _add_text(f'Row Index: {idx}')
        else:
            _add_text('Place the cursor on a row for detail', 'orange')
        _add_text(f'Total rows: {row_count}')
        if row_count_filtered != row_count:
            _add_text(f'Filtered rows: {row_count_filtered} ')

    def _update_after_reload(self):
        data_table = self.editable_table  # shortcut
        if not self.is_using_database:
            df = data_table.get_data()
            # if using FILE
            # ________________
            # update the "installed folders" AFTER loading the data in the datatable (because datatable content = CSV content)
            installed_assets_json = self.core.uevmlfs.get_installed_assets().copy()  # copy because the content could change during the process
            post_update_installed_folders(installed_assets_json, df)
        self.update_controls_state()
        self.update_category_var()
        # data_table.update()

    def reload_data(self) -> None:
        """
        Reload the data from the data source.
        """
        data_table = self.editable_table  # shortcut
        if not data_table.must_save or (
            data_table.must_save and gui_f.box_yesno('Changes have been made, they will be lost. Are you sure you want to continue ?')
        ):
            data_table.update_col_infos(apply_resize_cols=False)
            gui_f.show_progress(self, text=f'Reloading assets data...')
            if data_table.reload_data(self.core.uevmlfs.asset_sizes):
                self._update_after_reload()
                gui_f.box_message(f'Data Reloaded from {data_table.data_source}')
            else:
                gui_f.box_message(f'Failed to reload data from {data_table.data_source}', level='warning')

    def rebuild_data(self) -> None:
        """
        Rebuild the data from the data source. Will ask for confirmation before rebuilding.
        """
        if gui_f.box_yesno(f'The process will change the content of the windows.\nAre you sure you want to continue ?'):
            data_table = self.editable_table  # shortcut
            data_table.update_col_infos(apply_resize_cols=False)
            if gui_g.s.check_asset_folders:
                self.clean_asset_folders()
            gui_f.show_progress(self, text=f'Rebuilding Asset data...')
            if data_table.rebuild_data(self.core.uevmlfs.asset_sizes):
                self._update_after_reload()
                gui_f.box_message(f'Data rebuilt from {data_table.data_source}')
            else:
                gui_f.box_message(f'Failed to rebuild data from {data_table.data_source}', level='warning')

    def run_uevm_command(self, command_name='') -> (int, str):
        """
        Execute a cli command and display the result in DisplayContentWindow.
        :param command_name: name of the command to execute.
        """
        if gui_g.WindowsRef.display_content is not None:
            self.logger.info('A UEVM command is already running, please wait for it to finish.')
            gui_g.WindowsRef.display_content.set_focus()
            return
        if not command_name:
            return
        if gui_g.UEVM_cli_ref is None:
            gui_f.from_cli_only_message()
            return
        row_index = self.editable_table.get_selected_row_fixed()
        app_name = self.editable_table.get_cell(row_index, self.editable_table.get_col_index('Asset_id')) if row_index is not None else ''

        gui_g.UEVM_command_result = None  # clean result before running the command

        if app_name:
            gui_g.UEVM_cli_args['app_name'] = app_name

        # gui_g.UEVM_cli_args['offline'] = True  # speed up some commands DEBUG ONLY
        # set default options for the cli command to execute
        gui_g.UEVM_cli_args['gui'] = True  # mandatory for displaying the result in the DisplayContentWindow

        # arguments for several commands
        gui_g.UEVM_cli_args['csv'] = False  # mandatory for displaying the result in the DisplayContentWindow
        gui_g.UEVM_cli_args['tcsv'] = False  # mandatory for displaying the result in the DisplayContentWindow
        gui_g.UEVM_cli_args['json'] = False  # mandatory for displaying the result in the DisplayContentWindow

        # arguments for auth
        # now set in command options
        # gui_g.UEVM_cli_args['auth_delete'] = True

        # arguments for cleanup command
        choice = (command_name == 'cleanup' and gui_f.box_yesno('Do you want to delete all the data including scraping data and image cache ?'))
        gui_g.UEVM_cli_args['delete_scraping_data'] = choice
        gui_g.UEVM_cli_args['delete_cache_data'] = choice

        # arguments for help command
        gui_g.UEVM_cli_args['full_help'] = True

        # already_displayed = gui_g.WindowsRef.display_content is not None
        # if already_displayed:
        #     # Note: next line will raise an exption if gui_g.WindowsRef.display_content is None
        #     already_displayed = not gui_g.WindowsRef.display_content.winfo_viewable()
        #
        # if not already_displayed:
        #     # we display the window only if it is not already displayed
        #     function_to_call = getattr(gui_g.UEVM_cli_ref, command_name)
        #     function_to_call(gui_g.UEVM_cli_args)
        display_name = command_name
        subparser = gui_g.UEVM_cli_args.get('subparser', '')
        if subparser:
            display_name += ' - ' + gui_g.UEVM_cli_args['subparser']
        display_window = DisplayContentWindow(title=f'UEVM: {display_name} display result')
        gui_g.WindowsRef.display_content = display_window
        display_window.display(f'Running command {command_name}...Please wait')
        function_to_call = getattr(gui_g.UEVM_cli_ref, command_name)
        function_to_call(gui_g.UEVM_cli_args)
        self._wait_for_window(gui_g.WindowsRef.display_content)  # a local variable won't work here
        # make_modal(display_window)
        # usefull to tell the caller what row could have been updated
        return row_index, app_name

    # noinspection PyUnusedLocal
    def open_asset_url(self, event=None) -> None:
        """
        Open the asset URL (Wrapper).
        """
        url, widget = self._check_and_get_widget_value(tag='Url')
        if url:
            self.editable_table.open_asset_url(url=url)

    def open_asset_folder(self) -> None:
        """
        Open the asset URL (Wrapper).
        """
        self.editable_table.open_origin_folder()

    def open_json_file(self) -> None:
        """
        Open the source file (Wrapper).
        """
        asset_id, widget = self._check_and_get_widget_value(tag='Asset_id')
        if asset_id:
            self.editable_table.open_json_file(asset_id)

    def run_install(self):
        """
        Run the ""install_asset" command (Wrapper)
        :return:
        """
        gui_g.UEVM_cli_args['yes'] = True
        gui_g.UEVM_cli_args['no_resume'] = False
        gui_g.UEVM_cli_args['order_opt'] = True
        gui_g.UEVM_cli_args['vault_cache'] = True  # in gui mode, we CHOOSE to always use the vault cache for the download_path
        row_index, asset_id = self.run_uevm_command('install_asset')
        db_handler = self.editable_table.db_handler
        if db_handler:
            # get from db
            installed_folders = db_handler.get_installed_folders(asset_id)
        else:
            # get from data, updated after install
            try:
                installed_folders = gui_g.UEVM_command_result['Installed folders']
            except (TypeError, KeyError):
                installed_folders = ''
        if installed_folders:
            # get the content of the series existing_folders
            df = self.editable_table.get_data()
            result = df.loc[df['Asset_id'] == asset_id, 'Installed folders']
            existing_folders = result.iloc[0]
            installed_folders = gui_fn.merge_lists_or_strings(existing_folders, installed_folders)
            installed_folders_str = gui_fn.check_and_convert_list_to_str(installed_folders)
            row_index = self.editable_table.get_selected_row_fixed()
            self._update_installed_folders_cell(row_index, installed_folders_str)

    def download_asset(self) -> None:
        """
        Open the asset URL (Wrapper).
        """
        gui_g.UEVM_cli_args['subparser_name'] = 'download'
        gui_g.UEVM_cli_args['no_install'] = True  # !important
        self.run_install()

    def install_asset(self) -> None:
        """
        Open the asset URL (Wrapper).
        """
        gui_g.UEVM_cli_args['subparser_name'] = 'install'
        gui_g.UEVM_cli_args['no_install'] = False

        if self.editable_table.data_source_type != DataSourceType.FILE or gui_f.box_yesno(
            'To install an asset, using a database is a better option to avoid incoherent data in the "installed folder" field of the asset.\nThe current datasource type is "FILE", not "DATABASE".\nYou can switch the mode by using the "cli edit --database" instead of "cli edit --input" command.\nAre you sure you want to continue the operation in the current mode ?',
        ):
            self.run_install()

    def show_installed_releases(self) -> None:
        """
        Display the releases of the asset in a choice window.
        """
        release_info = gui_fn.get_and_check_release_info(self.editable_table.get_release_info())
        if release_info is None:
            self.logger.warning(f'Invalid release info: {release_info}')

        releases, latest_id = self.core.uevmlfs.extract_version_from_releases(release_info)
        if not releases or not latest_id:
            gui_f.box_message('There is no releases to install for this asset.\nCommand is aborted.')
            return
        self._releases_choice = releases
        cw = ChoiceFromListWindow(
            window_title='UEVM: select release',
            title='Select the release',
            sub_title='In the list below, Select the release you want to see detail from or to remove from the installed releases',
            json_data=self._releases_choice,
            default_value='',
            show_validate_button=False,
            show_delete_button=False,
            show_content_list=True,
            remove_from_content_func=self.remove_installed_folder,
            show_delete_content_button=True,
            no_content_text='This release has not been installed yet',
        )
        gui_f.make_modal(cw)

    def remove_installed_folder(self, selected_ids: tuple) -> bool:
        """
        Remove an installed folder from an installed release.
        :param selected_ids: tuple (the index of the release, index of the folder).
        :return: True if the release has been deleted, False otherwise.
        """
        folder_selected = ''
        release_selected = {}
        asset_id, folder_id = selected_ids
        if asset_id:
            try:
                release_selected = self._releases_choice[asset_id]
            except IndexError:
                return False
        if folder_id:
            content_data = release_selected.get('content', {})
            try:
                folder_selected = content_data[folder_id]
                folder_selected = folder_selected.get('value', '')
            except IndexError:
                return False
        if not folder_selected:
            return False
        if not self.core.is_installed(asset_id):
            gui_f.box_message(f'The release {asset_id} is not installed. Nothing to remove here.')
        elif gui_f.box_yesno(f'Are you sure you want to remove {folder_selected} from the release {asset_id} ?'):
            asset_installed = self.core.uevmlfs.get_installed_asset(asset_id)
            if asset_installed:
                installed_folders = asset_installed.installed_folders
                installed_folders_cleaned = [folder for folder in installed_folders if folder.lower != folder_selected.lower]
                asset_installed.installed_folders = installed_folders_cleaned
                if len(installed_folders_cleaned) == 0:
                    self.core.uevmlfs.remove_installed_asset(asset_id)
                else:
                    self.core.uevmlfs.set_installed_asset(asset_installed)  # will also set the installed folders without merging values
                    self.core.uevmlfs.save_installed_assets()
                # db_handler = UEAssetDbHandler(database_name=self.editable_table.data_source) # do not create one if the editable table is not a database
                db_handler = self.editable_table.db_handler
                if db_handler:
                    # remove the "installation folder" for the LATEST RELEASE in the db (others are NOT PRESENT !!) , using the calalog_item_id
                    catalog_item_id = asset_installed.catalog_item_id
                    installed_folders_str = db_handler.remove_from_installed_folders(catalog_item_id=catalog_item_id, folders=[folder_selected])
                else:
                    # get the content of the series existing_folders
                    df = self.editable_table.get_data()
                    result = df.loc[df['Asset_id'] == asset_id, 'Installed folders']
                    existing_folders = result.iloc[0]
                    installed_folders = gui_fn.merge_lists_or_strings(existing_folders, installed_folders_cleaned)
                    installed_folders.remove(folder_selected)
                    installed_folders_str = gui_fn.check_and_convert_list_to_str(installed_folders)
                row_index = self.editable_table.get_selected_row_fixed()
                self._update_installed_folders_cell(row_index, installed_folders_str)
                return True
        else:
            return False

    def get_asset_id(self) -> str:
        """
        Get the asset id in the control frame.
        """
        frm_control: UEVMGuiControlFrame = self._frm_control
        if not frm_control:
            return ''
        return frm_control.var_asset_id.get()

    def set_asset_id(self, value: str) -> None:
        """
        Set the asset id in the control frame.
        :param value: value to set.
        """
        frm_control: UEVMGuiControlFrame = self._frm_control
        if not frm_control:
            return
        frm_control.var_asset_id.set(value)

    # noinspection PyUnusedLocal
    def copy_asset_id(self, tag: str, event=None) -> None:  # we keep unused params to match the signature of the callback
        """
        Copy the asset id into the clipboard.
        """
        value = self.get_asset_id()
        self.clipboard_clear()
        self.clipboard_append(value)
        self.logger.info(f'{value} copied to the clipboard.')

    def clean_asset_folders(self) -> int:
        """
        Delete the assets which folder in 'Origin' does not exist.
        :return: number of deleted assets.
        """
        data_table = self.editable_table  # shortcut
        df = data_table.get_data(df_type=DataFrameUsed.UNFILTERED)
        mask = df['Origin'].notnull() & df['Origin'].ne(gui_g.s.origin_marketplace) & df['Origin'].ne('nan')
        df_to_check = df[mask]['Origin']
        indexes_to_delete = []
        for row_index, origin in df_to_check.items():
            if not os.path.exists(origin):
                indexes_to_delete.append(row_index)
        count = len(indexes_to_delete)
        deleted = 0
        if count:
            if gui_f.box_yesno(
                f'{count} assets with a non existing folder have been found.\nDo you want to delete them from the table and the database ?'
            ):
                deleted = data_table.del_rows(row_numbers=indexes_to_delete, convert_to_index=False, confirm_dialog=False)
            if deleted:
                data_table.save_data()
        return deleted

    def json_processing(self) -> None:
        """
        Run the window to update missing data in database from json files.
        """
        if not self.editable_table.is_using_database:
            gui_f.box_message('This command can only be run with a database as data source', level='warning')
            return
        tool_window = JsonToolWindow(
            title='Json Files Data Processing',
            icon=gui_g.s.app_icon_filename,
            db_path=self.editable_table.data_source,
            folder_for_tags_path=gui_g.s.assets_data_folder,
            folder_for_rating_path=gui_g.s.assets_csv_files_folder
        )
        gui_g.WindowsRef.tool = tool_window
        # self._wait_for_window(tool_window)
        gui_f.make_modal(tool_window)

    def database_processing(self) -> None:
        """
        Run the window to import/export database to csv files.
        """
        if not self.editable_table.is_using_database:
            gui_f.box_message('This command can only be run with a database as data source', level='warning')
            return
        tool_window = DbToolWindowClass(
            title='Database Import/Export Window',
            icon=gui_g.s.app_icon_filename,
            db_path=self.editable_table.data_source,
            folder_for_csv_files=gui_g.s.assets_csv_files_folder
        )
        gui_g.WindowsRef.tool = tool_window
        # self._wait_for_window(tool_window)
        gui_f.make_modal(tool_window)
        if tool_window.must_reload and gui_f.box_yesno('Some data has been imported into the database. Do you want to reload the data ?'):
            self.reload_data()

    def open_image_preview(self, _event) -> None:
        """
        Open the image preview window.
        :param _event: event from the widget.
        """
        if gui_g.WindowsRef.image_preview:
            gui_g.WindowsRef.image_preview.close_window()
        ipw = ImagePreviewWindow(
            title='Image Preview',
            screen_index=self.screen_index,
            url=self._image_url,
            width=gui_g.s.preview_max_width,
            height=gui_g.s.preview_max_height
        )
        if not ipw.display(url=self._image_url):
            ipw.close_window()
        else:
            gui_f.make_modal(ipw)  # make the preview window modal
