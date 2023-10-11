# coding=utf-8
"""
Implementation for:
- UEVMGui: the main window of the application.
"""
import filecmp
import json
import logging
import os
import re
import shutil
import sys
import tkinter as tk
from datetime import datetime
from time import sleep
from tkinter import filedialog as fd
from typing import Optional

import pandas as pd
from rapidfuzz import fuzz
from requests import ReadTimeout

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.api.egs import EPCAPI, GrabResult
from UEVaultManager.lfs.utils import get_version_from_path, path_join
from UEVaultManager.models.UEAssetDbHandlerClass import UEAssetDbHandler
from UEVaultManager.models.UEAssetScraperClass import UEAssetScraper
from UEVaultManager.tkgui.modules.cls.ChoiceFromListWindowClass import ChoiceFromListWindow
from UEVaultManager.tkgui.modules.cls.DbFilesWindowClass import DbFilesWindowClass
from UEVaultManager.tkgui.modules.cls.DisplayContentWindowClass import DisplayContentWindow
from UEVaultManager.tkgui.modules.cls.EditableTableClass import EditableTable
from UEVaultManager.tkgui.modules.cls.FakeProgressWindowClass import FakeProgressWindow
from UEVaultManager.tkgui.modules.cls.JsonProcessingWindowClass import JsonProcessingWindow
from UEVaultManager.tkgui.modules.comp.FilterFrameComp import FilterFrame
from UEVaultManager.tkgui.modules.comp.UEVMGuiContentFrameComp import UEVMGuiContentFrame
from UEVaultManager.tkgui.modules.comp.UEVMGuiControlFrameComp import UEVMGuiControlFrame
from UEVaultManager.tkgui.modules.comp.UEVMGuiOptionFrameComp import UEVMGuiOptionFrame
from UEVaultManager.tkgui.modules.comp.UEVMGuiToolbarFrameComp import UEVMGuiToolbarFrame
from UEVaultManager.tkgui.modules.types import DataFrameUsed, DataSourceType, UEAssetType


# not needed here
# warnings.filterwarnings('ignore', category=FutureWarning)  # Avoid the FutureWarning when PANDAS use ser.astype(object).apply()


def clean_ue_asset_name(name_to_clean: str) -> str:
    """
    Clean a name to remove unwanted characters.
    :param name_to_clean: name to clean.
    :return: cleaned name.
    """
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
        name_to_clean = pattern.sub('@', name_to_clean)

    # TWO: remove converted string with relicats
    patterns = [
        r'[@]+\d+',  # a @ followed by at least one digit ex: '@1' or '@11'
        # r'\d+[@]+',  # at least one digit followed by @ ex: '1@' or '1@@'
        r'[@]+',  # any @  ex: '@' or '@@'
    ]
    patterns = [re.compile(p) for p in patterns]
    for pattern in patterns:
        name_to_clean = pattern.sub('', name_to_clean)

    name_to_clean = name_to_clean.replace('_', '-')
    return name_to_clean.strip()  # Remove leading and trailing spaces


class UEVMGui(tk.Tk):
    """
    This class is used to create the main window for the application.
    :param title: the title.
    :param icon: the icon.
    :param screen_index: the screen index where the window will be displayed.
    :param data_source: the source where the data is stored or read from.
    :param data_source_type: the type of data source (DataSourceType.FILE or DataSourceType.SQLITE).
    :param show_open_file_dialog: whether the open file dialog will be shown at startup.
    """
    logger = logging.getLogger(__name__.split('.')[-1])  # keep only the class name
    gui_f.update_loggers_level(logger)
    _errors: [Exception] = []

    def __init__(
        self,
        title: str = 'UVMEGUI',
        icon='',
        screen_index: int = 0,
        data_source_type: DataSourceType = DataSourceType.FILE,
        data_source=None,
        show_open_file_dialog: bool = False,
        rebuild_data: bool = False,
    ):
        self._frm_toolbar: Optional[UEVMGuiToolbarFrame] = None
        self._frm_control: Optional[UEVMGuiControlFrame] = None
        self._frm_option: Optional[UEVMGuiOptionFrame] = None
        self._frm_content: Optional[UEVMGuiContentFrame] = None
        self._frm_filter: Optional[FilterFrame] = None
        self.editable_table: Optional[EditableTable] = None
        self.progress_window: Optional[FakeProgressWindow] = None
        self.egs: Optional[EPCAPI] = None
        super().__init__()
        self.data_source_type = data_source_type
        if data_source_type == DataSourceType.SQLITE:
            show_open_file_dialog = False
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
        self.resizable(True, True)
        pack_def_options = {'ipadx': 5, 'ipady': 5, 'padx': 3, 'pady': 3}

        frm_content = UEVMGuiContentFrame(self)
        self._frm_content = frm_content
        self.core = None if gui_g.UEVM_cli_ref is None else gui_g.UEVM_cli_ref.core
        self.releases_choice = {}

        # update the content of the database BEFORE loading the data in the datatable
        # as it, all the formatting and filtering could be done at start with good values
        if data_source_type == DataSourceType.SQLITE:
            # update the installed folder field in database from the installed_assets json file
            installed_assets_json = self.core.uevmlfs.get_installed_assets().copy()  # copy because the content could change during the process
            db_handler = UEAssetDbHandler(database_name=data_source)
            if db_handler is not None:
                merged_installed_folders = {}
                # get all installed folders for a given catalog_item_id
                for app_name, asset in installed_assets_json.items():
                    installed_folders_ori = asset.get('installed_folders', None)
                    # WE USE A COPY to avoid modifying the original list and merging all the installation folders for all releases
                    installed_folders = installed_folders_ori.copy() if installed_folders_ori is not None else None
                    if installed_folders is not None and len(installed_folders) > 0:
                        catalog_item_id = asset.get('catalog_item_id', None)
                        if merged_installed_folders.get(catalog_item_id, None) is None:
                            merged_installed_folders[catalog_item_id] = installed_folders
                        else:
                            merged_installed_folders[catalog_item_id].extend(installed_folders)
                    else:
                        # the installed_folders field is empty for the installed_assets, we remove it from the json file
                        self.core.uevmlfs.remove_installed_asset(app_name)
                # update the database using catalog_item_id instead as asset_id to merge installed_folders for ALL the releases
                for catalog_item_id, folders_to_add in merged_installed_folders.items():
                    db_handler.add_to_installed_folders(catalog_item_id=catalog_item_id, folders=folders_to_add)
            # update the installed_assets json file from the database info
            # NO TO DO because the in installed_folders have not the same content (for one asset in the json file, for all releases in the database)
            # installed_assets_db = db_handler.get_rows_with_installed_folders()
            # for app_name, asset_data in installed_assets_db.items():
            #     self.core.uevmlfs.update_installed_asset(app_name, asset_data)

        data_table = EditableTable(
            container=frm_content,
            data_source_type=data_source_type,
            data_source=data_source,
            rows_per_page=37,
            show_statusbar=True,
            update_page_numbers_func=self.update_controls_state,
            update_preview_info_func=self.update_preview_info,
            set_widget_state_func=gui_f.set_widget_state
        )

        # get the data AFTER updating the installed folder field in database
        if data_table.get_data() is None:
            self.logger.error('No valid source to read data from. Application will be closed')
            self.quit()
            self.core.clean_exit(1)  # previous line could not quit

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

        if not show_open_file_dialog and (rebuild_data or data_table.must_rebuild):
            if gui_f.box_yesno('Data file is invalid or empty. Do you want to rebuild data from sources files ?'):
                if not data_table.rebuild_data():
                    self.logger.error('Rebuild data error. This application could not run without a file to read from or some data to build from it')
                    self.destroy()  # self.quit() won't work here
                    return
            elif data_source_type == DataSourceType.FILE and gui_f.box_yesno(
                'So, do you want to load another file ? If not, the application will be closed'
            ):
                show_open_file_dialog = True
            else:
                # self.logger.error('No valid source to read data from. Application will be closed', )
                # self.close_window(True)
                msg = 'No valid source to read data from. The datatable will contain fake data. You should rebuild ou import real data from a file or a database.'
                gui_f.box_message(msg, level='warning')

        if show_open_file_dialog:
            if self.open_file() == '':
                self.logger.error('This application could not run without a file to read data from')
                self.close_window(True)

        gui_f.show_progress(self, text=f'Scanning downloaded assets in {self.core.egl.vault_cache_folder}...')
        downloaded_data = self.core.uevmlfs.get_downloaded_assets_data(self.core.egl.vault_cache_folder, max_depth=2)
        if downloaded_data is not None and len(downloaded_data) > 0:
            df = data_table.get_data(df_type=DataFrameUsed.UNFILTERED)
            # update the downloaded_size field in the datatable using asset_id as key
            s_format = gui_g.s.format_size
            s_yes = gui_g.s.unknown_size
            for asset_id, asset_data in downloaded_data.items():
                try:
                    size = int(asset_data['size'])
                    size = s_format.format(size / 1024 / 1024) if size > 1 else s_yes  # convert size to readable text
                    df.loc[df['Asset_id'] == asset_id, 'Downloaded size'] = size
                except KeyError:
                    pass
        if gui_g.s.last_opened_filter != '':
            filters = self.core.uevmlfs.load_filter_list(gui_g.s.last_opened_filter)
            if filters is not None:
                gui_f.show_progress(self, text=f'Loading filters from {gui_g.s.last_opened_filter}...')
                try:
                    self._frm_filter.set_filters(filters)
                    # data_table.update(update_format=True) # done in load_filters and inner calls
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
        Overrided to add logging function for debugging
        """
        self.logger.info(f'starting mainloop in {__name__}')
        self.tk.mainloop(n)
        # check is a child window is still open
        # child_windows = self.progress_window or gui_g.edit_cell_window_ref or gui_g.edit_row_window_ref
        # print('root loop')
        # if child_windows:
        #     self._wait_for_window(child_windows)
        self.logger.info(f'ending mainloop in {__name__}')

    @staticmethod
    def _focus_next_widget(event):
        event.widget.tk_focusNext().focus()
        return 'break'

    @staticmethod
    def _focus_prev_widget(event):
        event.widget.tk_focusPrev().focus()
        return 'break'

    def _open_file_dialog(self, save_mode: bool = False, filename: str = None) -> str:
        """
        Open a file dialog to choose a file to save or load data to/from.
        :param save_mode: whether the dialog will be in saving mode, else in loading mode.
        :param filename: the default filename to use.
        :return: the chosen filename.
        """
        # adding category to the default filename
        if not filename:
            filename = gui_g.s.default_filename
            initial_dir = gui_g.s.last_opened_folder
        else:
            initial_dir = os.path.dirname(filename)
        default_filename = os.path.basename(filename)  # remove dir
        default_ext = os.path.splitext(default_filename)[1]  # get extension
        default_filename = os.path.splitext(default_filename)[0]  # get filename without extension
        try:
            # if the file is empty or absent or invalid when creating the class, the frm_filter is not defined
            category = self._frm_filter.category
        except AttributeError as error:
            self.add_error(error)
            category = None
        if category and category != gui_g.s.default_value_for_all:
            default_filename = default_filename + '_' + category + default_ext
        else:
            default_filename = default_filename + default_ext
        if save_mode:
            filename = fd.asksaveasfilename(
                title='Choose a file to save data to', initialdir=initial_dir, filetypes=gui_g.s.data_filetypes, initialfile=default_filename
            )
        else:
            filename = fd.askopenfilename(
                title='Choose a file to read data from', initialdir=initial_dir, filetypes=gui_g.s.data_filetypes, initialfile=default_filename
            )
        return filename

    def _check_and_get_widget_value(self, tag: str):
        """
        Check if the widget with the given tags exists and return its value and itself.
        :param tag: tag of the widget that triggered the event.
        :return: value,widget.
        """
        if tag == '':
            return None, None
        widget = self._frm_control.lbtf_quick_edit.get_child_by_tag(tag)
        if widget is None:
            self.logger.warning(f'Could not find a widget with tag {tag}')
            return None, None
        col = widget.col
        row = widget.row
        if col is None or row is None or col < 0 or row < 0:
            self.logger.debug(f'invalid values for row={row} and col={col}')
            return None, widget
        value = widget.get_content()
        return value, widget

    def _wait_for_window(self, window: tk.Toplevel) -> None:
        """
        Wait for a window to be closed.
        :param window: the window to wait for.
        """
        if window is None:
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

    def _update_installed_folders(self, row_index: int, asset_id: str = '') -> None:
        """
        update the content of the 'Installed folders' cell of the row and the quick edit window.
        :param row_index: the index of the row to update.
        :param asset_id: the asset id to update.
        """
        asset_id = asset_id or self.get_asset_id()
        data_table = self.editable_table
        db_handler = data_table.db_handler
        installed_folders = db_handler.get_installed_folders(asset_id)
        col_index = data_table.get_col_index('Installed folders')
        if data_table.update_cell(row_index, col_index, installed_folders):
            data_table.update()  # because the "installed folder" field changed
        data_table.update_quick_edit(data_table.get_selected_row_fixed())

    def on_key_press(self, event):
        """
        Handle key press events.
        :param event:
        """
        # Note: this event will be triggered AFTER the event in the editabletable
        # print(event.keysym)
        # shift_pressed = event.state == 1 or event.state & 0x00001 != 0
        # alt_pressed = event.state == 8 or event.state & 0x20000 != 0
        # 4th keys of (FRENCH) keyboard: ampersand eacute quotedbl apostrophe
        control_pressed = event.state == 4 or event.state & 0x00004 != 0
        if event.keysym == 'Escape':
            if gui_g.edit_cell_window_ref:
                gui_g.edit_cell_window_ref.on_close()
                gui_g.edit_cell_window_ref = None
            elif gui_g.edit_row_window_ref:
                gui_g.edit_row_window_ref.on_close()
                gui_g.edit_row_window_ref = None
            else:
                self.on_close()
        elif control_pressed and (event.keysym == 's' or event.keysym == 'S'):
            self.save_changes()
        elif control_pressed and (event.keysym == '1' or event.keysym == 'ampersand'):
            self.editable_table.create_edit_cell_window(event)
        elif control_pressed and (event.keysym == '2' or event.keysym == 'eacute'):
            self.editable_table.create_edit_row_window(event)
        elif control_pressed and (event.keysym == '3' or event.keysym == 'quotedbl'):
            self.scrap_row()
        return 'break'

        # return 'break'  # stop event propagation

    def on_mouse_over_cell(self, event=None) -> None:
        """
        Show the image of the asset when the mouse is over the cell.
        :param event:
        """
        if event is None:
            return
        canvas_image = self._frm_control.canvas_image
        try:
            row_number: int = self.editable_table.get_row_clicked(event)
            if row_number < 0 or row_number == '':
                return
            self.update_preview_info(row_number)
            image_url = self.editable_table.get_image_url(row_number)
            if not gui_f.show_asset_image(image_url=image_url, canvas_image=canvas_image):
                # the image could not be loaded and the offline mode could have been enabled
                self.update_controls_state(update_title=True)
        except IndexError:
            gui_f.show_default_image(canvas_image)

    def on_mouse_leave_cell(self, _event=None) -> None:
        """
        Show the default image when the mouse leaves the cell.
        :param _event:
        """
        self.update_preview_info()
        canvas_image = self._frm_control.canvas_image
        gui_f.show_default_image(canvas_image=canvas_image)

    def on_selection_change(self, event=None) -> None:
        """
        When the selection changes, show the selected row in the quick edit frame.
        :param event:
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
        :param _event:
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
        if widget and widget.row >= 0 and widget.col >= 0:
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
        self.editable_table.on_header_release(event)
        # TODO: check if the column order has changed before enabling the widget
        widget_list = gui_g.stated_widgets.get('table_has_changed', [])
        gui_f.enable_widgets_in_list(widget_list)
        # update the column infos
        columns = self.editable_table.model.df.columns  # df. model checked
        old_columns_infos = gui_g.s.column_infos
        # reorder column_infos using columns keys
        new_columns_infos = {}
        for i, col in enumerate(columns):
            try:
                new_columns_infos[col] = old_columns_infos[col]
                new_columns_infos[col]['pos'] = i
            except KeyError:
                pass
        gui_g.s.column_infos = new_columns_infos
        gui_g.s.save_config_file()

    def on_close(self, _event=None) -> None:
        """
        When the window is closed, check if there are unsaved changes and ask the user if he wants to save them.
        :param _event: the event that triggered the call of this function.
        """
        if self.editable_table is not None and self.editable_table.must_save:
            if gui_f.box_yesno('Changes have been made. Do you want to save them in the source file ?'):
                self.save_changes(show_dialog=False)  # will save the settings too
        self.close_window()  # will save the settings too

    def close_window(self, force_quit=False) -> None:
        """
        Close the window.
        """
        self.save_settings()
        self.quit()
        if force_quit:
            sys.exit(0)

    def add_error(self, error: Exception) -> None:
        """
        Add an error to the list of errors.
        :param error: the error to add.
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
        :return: the name of the file that was loaded.
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

    def save_changes(self, show_dialog: bool = True) -> str:
        """
        Save the data to the current data source.
        :param show_dialog: whether to show a dialog to select the file to save to, if False, use the current file.
        :return: the name of the file that was saved.
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
        selected_rows = []
        row_numbers = data_table.multiplerowlist
        if row_numbers:
            # convert row numbers to row indexes
            row_indexes = [data_table.get_real_index(row_number) for row_number in row_numbers]
            selected_rows = data_table.get_data().iloc[row_indexes]  # iloc checked
        if len(selected_rows):
            filename = self._open_file_dialog(save_mode=True)
            if filename:
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
                gui_g.s.last_opened_folder = folder
                add_new_row = False
                self.scan_for_assets([folder])
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
        :return: the marketplace_url found in the file or an empty string if not found.
        """

        def read_from_url_file(entry, folder_name: str, returned_urls: [str]) -> bool:
            """
            Read an url from a .url file and add it to the list of urls to return.
            :param entry: the entry to process.
            :param folder_name: the name of the folder to search for.
            :param returned_urls: a list of urls to return. We use a list instead of a str because we need to modify it from the inner function.
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
        if check_if_valid and egs is not None and not egs.is_valid_url(found_url):
            found_url = ''

        return found_url

    def scan_for_assets(self, folder_list: list = None) -> None:
        """
        Scan the folders to find files that can be loaded.
        :param folder_list: the list of folders to scan. If empty, use the folders in the config file.
        """

        def _fix_folder_structure(content_folder_name: str = gui_g.s.ue_asset_content_subfolder):
            """
            Fix the folder structure by moving all the subfolders inside a "Content" subfolder.
            :param content_folder_name: the name of the subfolder to create.
            """
            if gui_f.box_yesno(
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

        valid_folders = {}
        invalid_folders = []
        folder_to_scan = folder_list if (folder_list is not None and len(folder_list) > 0) else gui_g.s.folders_to_scan
        if gui_g.s.testing_switch == 1:
            folder_to_scan = [
                'G:/Assets/pour UE/02 Warez/Environments/Elite_Landscapes_Desert_II',  #
                'G:/Assets/pour UE/00 A trier/Warez/Battle Royale Island Pack',  #
                'G:/Assets/pour UE/00 A trier/Warez/ColoradoNature',  #
                'G:/Assets/pour UE/02 Warez/Characters/Female/FurryS1 Fantasy Warrior',  #
            ]
        if gui_g.s.offline_mode:
            gui_f.box_message('You are in offline mode, Scraping and scanning features are not available')
            return
        if self.core is None:
            gui_f.from_cli_only_message('URL Scraping and scanning features are only accessible')
            return
        if not folder_to_scan:
            gui_f.box_message('No folder to scan. Please add some in the config file', level='warning')
            return
        if gui_g.s.check_asset_folders:
            self.clean_asset_folders()
        if len(folder_to_scan) > 1 and not gui_f.box_yesno(
            'Specified Folders to scan saved in the config file will be processed.\nSome assets will be added to the table and the process could take come time.\nDo you want to continue ?'
        ):
            return

        pw = gui_f.show_progress(self, text='Scanning folders for new assets', width=500, height=120, show_progress_l=False, show_btn_stop_l=True)
        data_table = self.editable_table  # shortcut
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

                if folder_is_valid:
                    folder_name = os.path.basename(parent_folder)
                    parent_folder = os.path.dirname(parent_folder)
                    path = os.path.dirname(full_folder)
                    pw.set_text(f'{folder_name} as a valid folder.\nChecking asset url...')
                    pw.update()
                    msg = f'-->Found {folder_name} as a valid project'
                    self.logger.info(msg)
                    marketplace_url = self.search_for_url(folder=folder_name, parent=parent_folder, check_if_valid=False)
                    grab_result = ''
                    comment = ''
                    if marketplace_url:
                        try:
                            grab_result = GrabResult.NO_ERROR.name if self.core.egs.is_valid_url(marketplace_url) else GrabResult.NO_RESPONSE.name
                        except ReadTimeout as error:
                            self.add_error(error)
                            gui_f.box_message(
                                f'Request timeout when accessing {marketplace_url}\n.Operation is stopped, check you internet connection or try again later.',
                                level='warning'
                            )
                            gui_f.close_progress(self)
                            # grab_result = GrabResult.TIMEOUT.name
                            return
                    valid_folders[folder_name] = {
                        'path': path,
                        'asset_type': UEAssetType.Asset,
                        'marketplace_url': marketplace_url,
                        'grab_result': grab_result,
                        'comment': comment
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
                                supported_versions = 'UE_' + get_version_from_path(full_folder)
                                marketplace_url = self.search_for_url(folder=folder_name, parent=parent_folder, check_if_valid=False)
                                grab_result = ''
                                if marketplace_url:
                                    try:
                                        grab_result = GrabResult.NO_ERROR.name if self.core.egs.is_valid_url(
                                            marketplace_url
                                        ) else GrabResult.TIMEOUT.name
                                    except ReadTimeout as error:
                                        self.add_error(error)
                                        gui_f.box_message(
                                            f'Request timeout when accessing {marketplace_url}\n.Operation is stopped, check you internet connection or try again later.',
                                            level='warning'
                                        )
                                        grab_result = GrabResult.TIMEOUT.name
                                valid_folders[folder_name] = {
                                    'path': path,
                                    'asset_type': asset_type,
                                    'marketplace_url': marketplace_url,
                                    'grab_result': grab_result,
                                    'comment': comment,
                                    'Supported versions': supported_versions,
                                }
                                msg = f'-->Found {folder_name} as a valid project containing a {asset_type.name}' if extension_lower in gui_g.s.ue_valid_file_ext else f'-->Found {folder_name} containing a {asset_type.name}'
                                self.logger.debug(msg)
                                if self.core.scan_assets_logger:
                                    self.core.scan_assets_logger.info(msg)
                                if grab_result != GrabResult.NO_ERROR.name or not marketplace_url:
                                    invalid_folders.append(full_folder)
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
        date_added = datetime.now().strftime(gui_g.s.csv_datetime_format)
        row_data = {'Date added': date_added, 'Creation date': date_added, 'Update date': date_added, 'Added manually': True}
        data = data_table.get_data(df_type=DataFrameUsed.UNFILTERED)
        count = len(valid_folders.items())
        pw.reset(new_text='Scraping data and updating assets', new_max_value=count)
        pw.show_progress_bar()
        pw.update()
        row_added = 0
        data_table.is_scanning = True
        # copy_col_index = data_table.get_col_index(gui_g.s.index_copy_col_name)
        for name, content in valid_folders.items():
            marketplace_url = content['marketplace_url']
            self.logger.info(f'{name} : a {content["asset_type"].name} at {content["path"]} with marketplace_url {marketplace_url} ')
            # set default values for the row, some will be replaced by Scraping
            row_data.update(
                {
                    'App name': name,
                    'Origin': content['path'],
                    'Url': content['marketplace_url'],
                    'Grab result': content['grab_result'],
                    'Added manually': True,
                    'Category': content['asset_type'].category_name,
                    'Comment': content['comment'],
                    'Supported versions': content['Supported versions'],
                }
            )
            row_index = -1
            text = f'Checking {name}'
            try:
                # get the indexes if value already exists in column 'Origin' for a pandastable
                rows_serie = data.loc[lambda x: x['Origin'].str.lower() == content['path'].lower()]
                row_indexes = rows_serie.index  # returns a list of indexes. It should contain only 1 value
                if not row_indexes.empty:
                    row_index = row_indexes[0]
                    text = f'Updating {name} at row {row_index}. Old name is {data.loc[row_index, "App name"]}'
                    self.logger.info(f"{text} with path {content['path']}")
            except (IndexError, ValueError) as error:
                self.add_error(error)
                self.logger.warning(f'Error when checking the existence for {name} at {content["path"]}: error {error!r}')
                invalid_folders.append(content["path"])
                text = f'An Error occured when cheking {name}'
                pw.set_text(text)
                continue
            if row_index == -1:
                # row_index = 0  # added at the start of the table. As it, the index is always known
                _, row_index = data_table.create_row(row_data=row_data, do_not_save=True)
                text = f'Adding {name} at row {row_index}'
                self.logger.info(f"{text} with path {content['path']}")
                row_added += 1
            if not pw.update_and_continue(increment=1, text=text):
                break
            forced_data = {
                # 'category': content['asset_type'].category_name,
                'origin': content['path'],
                'asset_url': content['marketplace_url'],
                'grab_result': content['grab_result'],
                'added_manually': True,
                'category': content['asset_type'].category_name,
                'comment': content['comment'],
                'Supported versions': content['Supported versions'],
            }
            if content['grab_result'] == GrabResult.NO_ERROR.name:
                try:
                    self.scrap_row(
                        marketplace_url=marketplace_url, row_index=row_index, forced_data=forced_data, show_message=False, update_dataframe=False
                    )
                except ReadTimeout as error:
                    self.add_error(error)
                    gui_f.box_message(
                        f'Request timeout when accessing {marketplace_url}\n.Operation is stopped, check you internet connection or try again later.',
                        level='warning'
                    )
                    forced_data['grab_result'] = GrabResult.TIMEOUT.name
            else:
                data_table.update_row(row_number=row_index, ue_asset_data=forced_data, convert_row_number_to_row_index=False)
                data_table.add_to_rows_to_save(row_index)  # done inside self.must_save = True
        pw.hide_progress_bar()
        pw.hide_btn_stop()
        pw.set_text('Updating the table. Could take a while...')
        pw.update()
        data_table.is_scanning = False
        data_table.update(update_format=True, update_filters=True)
        gui_f.close_progress(self)

        if invalid_folders:
            result = '\n'.join(invalid_folders)
            result = f'The following folders have produce invalid results during the scan:\n{result}'
            if gui_g.display_content_window_ref is None:
                file_name = f'scan_folder_results_{datetime.now().strftime("%y-%m-%d")}.txt'
                gui_g.display_content_window_ref = DisplayContentWindow(
                    title='UEVM: status command output', quit_on_close=False, result_filename=file_name
                )
                gui_g.display_content_window_ref.display(result)
                gui_f.make_modal(gui_g.display_content_window_ref)
            self.logger.warning(result)

    def _scrap_from_url(self, marketplace_url: str, forced_data: {} = None, show_message: bool = False):
        is_ok = False
        asset_data = None
        # check if the marketplace_url is a marketplace marketplace_url
        ue_marketplace_url = self.core.egs.get_marketplace_product_url()
        if ue_marketplace_url.lower() in marketplace_url.lower():
            # get the data from the marketplace marketplace_url
            asset_data = self.core.egs.get_asset_data_from_marketplace(marketplace_url)
            if asset_data is None or asset_data == [] or asset_data.get('grab_result',
                                                                        None) != GrabResult.NO_ERROR.name or not asset_data.get('id', ''):
                msg = f'Failed to grab data from {marketplace_url}'
                if show_message:
                    gui_f.box_message(msg, level='warning')
                else:
                    self.logger.warning(msg)
                return None
            api_product_url = self.core.egs.get_api_product_url(asset_data['id'])
            scraper = UEAssetScraper(
                start=0,
                assets_per_page=1,
                max_threads=1,
                store_in_db=True,
                store_in_files=True,
                store_ids=False,  # useless for now
                load_from_files=False,
                engine_version_for_obsolete_assets=self.core.engine_version_for_obsolete_assets,
                core=self.core  # VERY IMPORTANT: pass the core object to the scraper to keep the same session
            )
            scraper.get_data_from_url(api_product_url)
            asset_data = scraper.pop_last_scrapped_data()  # returns a list of one element
            if asset_data is not None and len(asset_data) > 0:
                if forced_data is not None:
                    for key, value in forced_data.items():
                        asset_data[0][key] = value
                scraper.asset_db_handler.set_assets(asset_data)
                is_ok = True
        if not is_ok:
            asset_data = None
            msg = f'The asset url {marketplace_url} is invalid and could not be scrapped for this row'
            if show_message:
                gui_f.box_message(msg, level='warning')
            else:
                self.logger.warning(msg)
        return asset_data

    def scrap_row(
        self, marketplace_url: str = None, row_index: int = -1, forced_data: {} = None, show_message: bool = True, update_dataframe: bool = True
    ):
        """
        Scrap the data for the current row or a given marketplace_url.
        :param marketplace_url: marketplace_url to scrap.
        :param row_index: the (real) index of the row to scrap.
        :param forced_data: if not None, all the key in forced_data will replace the scrapped data
        :param show_message: whether to show a message if the marketplace_url is not valid
        :param update_dataframe: whether to update the dataframe after scraping
        """

        if gui_g.s.offline_mode:
            gui_f.box_message('You are in offline mode, Scraping and scanning features are not available')
            return
        if self.core is None:
            gui_f.from_cli_only_message('URL Scraping and scanning features are only accessible')
            return
        data_table = self.editable_table  # shortcut
        row_numbers = data_table.multiplerowlist
        if row_index < 0 and marketplace_url is None and row_numbers is None and len(row_numbers) < 1:
            if show_message:
                gui_f.box_message('You must select a row first', level='warning')
            return
        if row_index >= 0:
            # a row index has been given, we scrap only this row
            row_indexes = [row_index]
        else:
            # convert row numbers to row indexes
            row_indexes = [data_table.get_real_index(row_number) for row_number in row_numbers]
        pw = None
        row_count = len(row_indexes)
        if marketplace_url is None:
            base_text = "Scraping asset's data. Could take a while..."
            if row_count > 1:
                pw = gui_f.show_progress(
                    self, text=base_text, max_value_l=row_count, width=450, height=150, show_progress_l=True, show_btn_stop_l=True
                )
            for row_index in row_indexes:
                row_data = data_table.get_row(row_index, return_as_dict=True)
                marketplace_url = row_data['Url']
                asset_slug_from_url = marketplace_url.split('/')[-1]
                asset_slug_from_row = row_data['Asset slug']
                if asset_slug_from_url != asset_slug_from_row:
                    msg = f'The Url slug from the given Url {asset_slug_from_url} is different from the existing data {asset_slug_from_row}.'
                    self.logger.warning(msg)
                    # we use existing_url and not asset_data['asset_url'] because it could have been corrected by the user
                    if gui_f.box_yesno(
                        f'{msg}.\nDo you wan to create a new Url with {asset_slug_from_row} and use it for scraping ?\nIf no, the given url with {asset_slug_from_url} will be used'
                    ):
                        marketplace_url = self.core.egs.get_marketplace_product_url(asset_slug_from_row)
                        col_index = data_table.get_col_index('Url')
                        data_table.update_cell(row_index, col_index, marketplace_url, convert_row_number_to_row_index=False)
                text = base_text + f'\n Row {row_index}: scraping {gui_fn.shorten_text(marketplace_url)}'
                if pw and not pw.update_and_continue(increment=1, text=text):
                    gui_f.close_progress(self)
                    return
                asset_data = self._scrap_from_url(marketplace_url, forced_data=forced_data, show_message=show_message)
                if asset_data is not None:
                    data_table.update_row(row_index, ue_asset_data=asset_data, convert_row_number_to_row_index=False)
                    if show_message and row_count == 1:
                        gui_f.box_message(f'Data for row {row_index} have been updated from the marketplace')

            gui_f.close_progress(self)
            if show_message and row_count > 1:
                gui_f.box_message(f'All Datas for {row_count} rows have been updated from the marketplace')
        else:
            asset_data = self._scrap_from_url(marketplace_url, forced_data=forced_data, show_message=show_message)
            if asset_data is not None:
                data_table.update_row(row_index, ue_asset_data=asset_data, convert_row_number_to_row_index=False)
        if update_dataframe:
            data_table.update()

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
            self._frm_toolbar.btn_toggle_controls.config(text='Hide Actions')
            self._frm_toolbar.btn_toggle_options.config(state=tk.DISABLED)
        else:
            self._frm_control.pack_forget()
            self._frm_toolbar.btn_toggle_controls.config(text='Show Actions')
            self._frm_toolbar.btn_toggle_options.config(state=tk.NORMAL)

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
            self._frm_toolbar.btn_toggle_options.config(text='Hide Options')
            self._frm_toolbar.btn_toggle_controls.config(state=tk.DISABLED)
        else:
            self._frm_option.pack_forget()
            self._frm_toolbar.btn_toggle_options.config(text='Show Options')
            self._frm_toolbar.btn_toggle_controls.config(state=tk.NORMAL)

    def update_controls_state(self, update_title=False) -> None:
        """
        Update the controls and redraw the table.
        :return: 
        """
        if update_title:
            self.title(gui_g.s.app_title_long)

        if self._frm_toolbar is None:
            return

        data_table = self.editable_table
        max_index = len(data_table.get_data())
        current_row = data_table.get_selected_row_fixed()
        current_row_index = data_table.add_page_offset(current_row) if current_row is not None else -1

        gui_f.update_widgets_in_list(len(data_table.multiplerowlist) > 0, 'row_is_selected')
        gui_f.update_widgets_in_list(data_table.must_save, 'table_has_changed', text_swap={'normal': 'Save *', 'disabled': 'Save  '})
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
        is_owned = False
        is_added = False
        url = ''
        if current_row is not None:
            url = data_table.get_cell(current_row, data_table.get_col_index('Url'))
            is_added = data_table.get_cell(current_row, data_table.get_col_index('Added manually'))
            is_owned = data_table.get_cell(current_row, data_table.get_col_index('Owned'))
        gui_f.update_widgets_in_list(is_owned, 'asset_is_owned')
        gui_f.update_widgets_in_list(is_added, 'asset_added_mannually')
        gui_f.update_widgets_in_list(url != '', 'asset_has_url')

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
        :return: a dict with the new categories list as value and the key is the name of the variable.
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
        if self._frm_control is None:
            return
        data_table = self.editable_table  # shortcut
        df = data_table.get_data(df_type=DataFrameUsed.UNFILTERED)
        df_filtered = data_table.get_data(df_type=DataFrameUsed.FILTERED)
        row_count_filtered = len(df_filtered) if df_filtered is not None else 0
        row_count = len(df)
        asset_info = []
        idx = data_table.get_real_index(row_number)
        asset_info.append(f'Total rows: {row_count}')
        if row_count_filtered != row_count:
            asset_info.append(f'Filtered rows: {row_count_filtered} ')
        if idx >= 0:
            app_name = data_table.get_cell(row_number, data_table.get_col_index('Asset_id'))
            asset_info.append(f'Asset id: {app_name}')
            asset_info.append(f'Row Index: {idx}')
            size = self.core.uevmlfs.get_asset_size(app_name)
            if size is not None and size > 0:
                size_formatted = '{:.02f} GiB'.format(size / 1024 / 1024 /
                                                      1024) if size > 1024 * 1024 * 1024 else '{:.02f} MiB'.format(size / 1024 / 1024)
                asset_info.append(f'Asset size: {size_formatted}')
            else:
                asset_info.append(f'Asset size: Not Get Yet')
        else:
            asset_info.append('No Row selected')
        self._frm_control.txt_info.delete('1.0', tk.END)
        self._frm_control.txt_info.insert('1.0', '\n'.join(asset_info))

    def reload_data(self) -> None:
        """
        Reload the data from the data source.
        """
        data_table = self.editable_table  # shortcut
        if not data_table.must_save or (
            data_table.must_save and gui_f.box_yesno('Changes have been made, they will be lost. Are you sure you want to continue ?')
        ):
            data_table.update_col_infos(apply_resize_cols=False)
            if data_table.reload_data():
                # self.update_page_numbers() done in reload_data
                self.update_category_var()
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
            if data_table.rebuild_data():
                self.update_controls_state()
                self.update_category_var()
                gui_f.box_message(f'Data rebuilt from {data_table.data_source}')

    def run_uevm_command(self, command_name='') -> (int, str):
        """
        Execute a cli command and display the result in DisplayContentWindow.
        :param command_name: the name of the command to execute.
        """
        if gui_g.display_content_window_ref is not None:
            self.logger.info('A UEVM command is already running, please wait for it to finish.')
            gui_g.display_content_window_ref.set_focus()
            return
        if command_name == '':
            return
        if gui_g.UEVM_cli_ref is None:
            gui_f.from_cli_only_message()
            return
        row_index = self.editable_table.get_selected_row_fixed()
        app_name = self.editable_table.get_cell(row_index, self.editable_table.get_col_index('Asset_id')) if row_index is not None else ''
        if app_name != '':
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
        # now set in command options
        # gui_g.UEVM_cli_args['delete_extra_data'] = True
        # gui_g.UEVM_cli_args['delete_metadata'] = True
        # gui_g.UEVM_cli_args['delete_scraping_data'] = True

        # arguments for help command
        gui_g.UEVM_cli_args['full_help'] = True

        # already_displayed = gui_g.display_content_window_ref is not None
        # if already_displayed:
        #     # Note: next line will raise an exption if gui_g.display_content_window_ref is None
        #     already_displayed = not gui_g.display_content_window_ref.winfo_viewable()
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
        gui_g.display_content_window_ref = display_window
        display_window.display(f'Running command {command_name}...Please wait')
        function_to_call = getattr(gui_g.UEVM_cli_ref, command_name)
        function_to_call(gui_g.UEVM_cli_args)
        self._wait_for_window(gui_g.display_content_window_ref)  # a local variable won't work here
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
        self._update_installed_folders(row_index, asset_id)

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
        self.run_install()

    def remove_installed_release(self, release_index: int) -> bool:
        """
        Delete the release from the installed releases.
        :param release_index: the index of the release to delete.
        :return: True if the release has been deleted, False otherwise.
        """
        asset_id = ''
        if release_index >= 0:
            try:
                release_selected = self.releases_choice[release_index]
                asset_id = release_selected['id']
            except IndexError:
                return False
        if not asset_id:
            return False
        if not self.core.is_installed(asset_id):
            gui_f.box_message(f'The release {asset_id} is not installed. Nothing to remove here.')
        elif gui_f.box_yesno(f'Are you sure you want to remove the release {asset_id} from the installed asset list ?'):
            asset_installed = self.core.uevmlfs.get_installed_asset(asset_id)
            if asset_installed:
                folders_to_remove = asset_installed.installed_folders
                self.core.uevmlfs.remove_installed_asset(asset_id)
                db_handler = UEAssetDbHandler(database_name=self.editable_table.data_source)
                if db_handler is not None:
                    # remove the "installation folder" for the LATEST RELEASE in the db (others are NOT PRESENT !!) , using the calalog_item_id
                    catalog_item_id = asset_installed.catalog_item_id
                    db_handler.remove_from_installed_folders(catalog_item_id=catalog_item_id, folders=folders_to_remove)
                return True
        else:
            return False

    def show_installed_releases(self) -> None:
        """
        Display the releases of the asset in a choice window.
        """
        data_table = self.editable_table  # shortcut
        release_info_json = data_table.get_release_info()
        if not release_info_json:
            return
        release_info = json.loads(release_info_json)
        self.releases_choice, _ = self.core.uevmlfs.extract_version_from_releases(release_info)
        cw = ChoiceFromListWindow(
            window_title='UEVM: select release',
            title='Select the release',
            sub_title='In the list below, Select the release you want to see detail from or to remove from the installed releases',
            json_data=self.releases_choice,
            default_value='',
            show_validate_button=False,
            show_delete_button=True,
            list_remove_func=self.remove_installed_release,
            show_content_list=True,
            remove_from_content_func=self.remove_installed_folder,
            show_delete_content_button=True,
            no_content_text='This release has not been installed yet',
        )
        gui_f.make_modal(cw)
        row_index = data_table.get_selected_row_fixed()
        self._update_installed_folders(row_index)

    def remove_installed_folder(self, selected_ids: tuple) -> bool:
        """
        Remove an installed folder from an installed release.
        :param selected_ids: tuple (the index of the release, index of the folder)
        :return: True if the release has been deleted, False otherwise.
        """
        folder_selected = ''
        release_selected = {}
        asset_id, folder_id = selected_ids
        if asset_id:
            try:
                release_selected = self.releases_choice[asset_id]
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

                db_handler = UEAssetDbHandler(database_name=self.editable_table.data_source)
                if db_handler is not None:
                    # remove the "installation folder" for the LATEST RELEASE in the db (others are NOT PRESENT !!) , using the calalog_item_id
                    catalog_item_id = asset_installed.catalog_item_id
                    db_handler.remove_from_installed_folders(catalog_item_id=catalog_item_id, folders=[folder_selected])
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
        :param value: the value to set.
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
        :return: the number of deleted assets.
        """
        data_table = self.editable_table  # shortcut
        df = data_table.get_data(df_type=DataFrameUsed.UNFILTERED)
        mask = df['Origin'].notnull() & df['Origin'].ne('Marketplace') & df['Origin'].ne('nan')
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
        if self.editable_table.data_source_type != DataSourceType.SQLITE:
            gui_f.box_message('This command can only be run with a database as data source', level='warning')
            return
        tool_window = JsonProcessingWindow(
            title='Json Files Data Processing',
            icon=gui_g.s.app_icon_filename,
            db_path=self.editable_table.data_source,
            folder_for_tags_path=gui_g.s.assets_data_folder,
            folder_for_rating_path=gui_g.s.assets_csv_files_folder
        )
        gui_g.tool_window_ref = tool_window
        # self._wait_for_window(tool_window)
        gui_f.make_modal(tool_window)

    def database_processing(self) -> None:
        """
        Run the window to import/export database to csv files.
        """
        if self.editable_table.data_source_type != DataSourceType.SQLITE:
            gui_f.box_message('This command can only be run with a database as data source', level='warning')
            return
        tool_window = DbFilesWindowClass(
            title='Database Import/Export Window',
            icon=gui_g.s.app_icon_filename,
            db_path=self.editable_table.data_source,
            folder_for_csv_files=gui_g.s.assets_csv_files_folder
        )
        gui_g.tool_window_ref = tool_window
        # self._wait_for_window(tool_window)
        gui_f.make_modal(tool_window)
        if tool_window.must_reload and gui_f.box_yesno('Some data has been imported into the database. Do you want to reload the data ?'):
            self.reload_data()

    def create_dynamic_filters(self) -> {str: []}:
        """
        Create a dynamic filters list that can be added to the filter frame quick filter list.
        :return: a dict that will be added to the FilterFrame quick filters list.

        Notes:
            It returns a dict where each entry must respect the folowing format: "{'<label>': ['callable': <callable> ]}"
            where:
             <label> is the label to display in the quick filter list
             <callable> is the function to call to get the mask.
        """
        return {
            # add ^ to the beginning of the value to search for the INVERSE the result
            'Owned': ['Owned', True],  #
            'Not Owned': ['Owned', False],  #
            'Obsolete': ['Obsolete', True],  #
            'Not Obsolete': ['Obsolete', False],  #
            'Must buy': ['Must buy', True],  #
            'Added manually': ['Added manually', True],  #
            'Result OK': ['Grab result', 'NO_ERROR'],  #
            'Result Not OK': ['Grab result', '^NO_ERROR'],  #
            'Plugins only': ['Category', 'plugins'],  #
            'Free': ['Price', 0],  #
            'Dummy rows': ['Asset_id', gui_g.s.empty_row_prefix],  #
            'Not Marketplace': ['Origin', '^Marketplace'],  # asset with origin that does NOT contain marketplace
            'Tags with number': ['callable', self.filter_tags_with_number],  #
            'With comment': ['callable', self.filter_with_comment],  #
            'Free and not owned': ['callable', self.filter_free_and_not_owned],  #
            'Installed in folder': ['callable', self.filter_with_installed_folders],  #
            'Downloaded': ['callable', self.filter_is_downloaded],  #
        }

    def filter_tags_with_number(self) -> pd.Series:
        """
        Create a mask to filter the data with tags that contains an integer.
        :return: a mask to filter the data.
        """
        df = self.editable_table.get_data(df_type=DataFrameUsed.UNFILTERED)
        mask = df['Tags'].str.split(',').apply(lambda x: any(gui_fn.is_an_int(i, gui_g.s.tag_prefix) for i in x))
        return mask

    def filter_free_and_not_owned(self) -> pd.Series:
        """
        Create a mask to filter the data that are not owned and with a price <=0.5 or free.
        Assets that custom attributes contains external_link are also filtered.
        :return: a mask to filter the data.
        """
        df = self.editable_table.get_data(df_type=DataFrameUsed.UNFILTERED)
        # Ensure 'Discount price' and 'Price' are float type
        df['Discount price'] = df['Discount price'].astype(float)
        df['Price'] = df['Price'].astype(float)
        mask = df['Owned'].ne(True) & ~df['Custom attributes'].str.contains('external_link') & (
            df['Free'].eq(True) | df['Discount price'].le(0.5) | df['Price'].le(0.5)
        )
        return mask

    def filter_not_empty(self, col_name: str) -> pd.Series:
        """
        Create a mask to filter the data with a non-empty value for a column.
        :param col_name: the name of the column to check.
        :return: a mask to filter the data.
        """
        df = self.editable_table.get_data(df_type=DataFrameUsed.UNFILTERED)
        mask = df[col_name].notnull() & df[col_name].ne('') & df[col_name].ne('None') & df[col_name].ne('nan') & df[col_name].ne('NA')
        return mask

    def filter_with_comment(self) -> pd.Series:
        """
        Create a mask to filter the data with a non-empty comment value.
        :return: a mask to filter the data.
        """
        return self.filter_not_empty('Comment')

    def filter_with_installed_folders(self) -> pd.Series:
        """
        Create a mask to filter the data with a non-empty installed_folders value.
        :return: a mask to filter the data.
        """
        return self.filter_not_empty('Installed folders')

    def filter_is_downloaded(self) -> pd.Series:
        """
        Create a mask to filter the data with a non-empty downloaded size.
        :return: a mask to filter the data.
        """
        return self.filter_not_empty('Downloaded size')
