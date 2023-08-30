# coding=utf-8
"""
Implementation for:
- UEVMGui: the main window of the application.
"""
import filecmp
import logging
import os
import re
import shutil
import sys
import tkinter as tk
from datetime import datetime
from time import sleep
from tkinter import filedialog as fd

import pandas as pd
from rapidfuzz import fuzz
from requests import ReadTimeout

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.api.egs import GrabResult
from UEVaultManager.lfs.utils import path_join
from UEVaultManager.models.UEAssetScraperClass import UEAssetScraper
from UEVaultManager.tkgui.modules.cls.DbFilesWindowClass import DbFilesWindowClass
from UEVaultManager.tkgui.modules.cls.DisplayContentWindowClass import DisplayContentWindow
from UEVaultManager.tkgui.modules.cls.EditableTableClass import EditableTable
from UEVaultManager.tkgui.modules.cls.FakeProgressWindowClass import FakeProgressWindow
from UEVaultManager.tkgui.modules.cls.JsonProcessingWindowClass import JsonProcessingWindow
from UEVaultManager.tkgui.modules.comp.FilterFrameComp import FilterFrame
from UEVaultManager.tkgui.modules.comp.UEVMGuiContentFrameComp import UEVMGuiContentFrame
from UEVaultManager.tkgui.modules.comp.UEVMGuiControlFrameComp import UEVMGuiControlFrame
from UEVaultManager.tkgui.modules.comp.UEVMGuiOptionsFrameComp import UEVMGuiOptionsFrame
from UEVaultManager.tkgui.modules.comp.UEVMGuiToolbarFrameComp import UEVMGuiToolbarFrame
from UEVaultManager.tkgui.modules.functions_no_deps import is_an_int, set_custom_style
from UEVaultManager.tkgui.modules.types import DataFrameUsed, DataSourceType, UEAssetType


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
        r'\d+[@]+',  # at least one digit followed by @ ex: '1@' or '1@@'
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
    :param title: The title.
    :param icon: The icon.
    :param screen_index: The screen index where the window will be displayed.
    :param data_source: The source where the data is stored or read from.
    :param data_source_type: The type of data source (DataSourceType.FILE or DataSourceType.SQLITE).
    :param show_open_file_dialog: Whether the open file dialog will be shown at startup.
    """
    editable_table: EditableTable = None
    progress_window: FakeProgressWindow = None
    _toolbar_frame: UEVMGuiToolbarFrame = None
    _control_frame: UEVMGuiControlFrame = None
    _options_frame: UEVMGuiOptionsFrame = None
    _content_frame: UEVMGuiContentFrame = None
    _filter_frame: FilterFrame = None
    logger = logging.getLogger(__name__.split('.')[-1])  # keep only the class name
    gui_f.update_loggers_level(logger)
    egs = None

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
        super().__init__()
        self.data_source_type = data_source_type
        if data_source_type == DataSourceType.SQLITE:
            show_open_file_dialog = False
        self.title(title)
        self.style = set_custom_style(gui_g.s.theme_name, gui_g.s.theme_font)
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

        content_frame = UEVMGuiContentFrame(self)
        self._content_frame = content_frame
        self.core = None if gui_g.UEVM_cli_ref is None else gui_g.UEVM_cli_ref.core

        data_table = EditableTable(
            container=content_frame,
            data_source_type=data_source_type,
            data_source=data_source,
            rows_per_page=37,
            show_statusbar=True,
            update_page_numbers_func=self.update_controls_and_redraw,
            update_rows_text_func=self.update_rows_text,
            set_control_state_func=self.set_control_state
        )
        self.editable_table = data_table
        data_table.set_preferences(gui_g.s.datatable_default_pref)
        data_table.show()

        toolbar_frame = UEVMGuiToolbarFrame(self, data_table)
        self._toolbar_frame = toolbar_frame
        control_frame = UEVMGuiControlFrame(self, data_table)
        self._control_frame = control_frame
        options_frame = UEVMGuiOptionsFrame(self)
        self._options_frame = options_frame

        toolbar_frame.pack(**pack_def_options, fill=tk.X, side=tk.TOP, anchor=tk.NW)
        content_frame.pack(**pack_def_options, fill=tk.BOTH, side=tk.LEFT, anchor=tk.NW, expand=True)
        control_frame.pack(**pack_def_options, fill=tk.BOTH, side=tk.RIGHT, anchor=tk.NW)
        # not displayed at start
        # _options_frame.pack(**pack_def_options, fill=tk.BOTH, side=tk.RIGHT, anchor=tk.NW)

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

        # List of controls for activating/deactivating them when needed
        self.controls = {
            'first_item': self._toolbar_frame.btn_first_item,  #
            'last_item': self._toolbar_frame.btn_last_item,  #
            'prev_page': self._toolbar_frame.btn_prev_page,  #
            'next_page': self._toolbar_frame.btn_next_page,  #
            'prev_asset': self._toolbar_frame.btn_prev_asset,  #
            'next_asset': self._toolbar_frame.btn_next_asset,  #
            'current_item': self._toolbar_frame.entry_current_item,  #
            'scrap': self._control_frame.buttons['Scrap']['widget'],  #
            'del': self._control_frame.buttons['Del']['widget'],  #
            'edit': self._control_frame.buttons['Edit']['widget'],  #
            'save': self._control_frame.buttons['Save']['widget'],  #
        }

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

        gui_f.show_progress(self, text='Initializing Data Table...')
        if gui_g.s.data_filters:
            self.load_filters(gui_g.s.data_filters)
        else:
            data_table.update(update_format=True)
        # Quick edit the first row
        # self.editable_table.update_quick_edit(0)
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
        :param save_mode: Whether the dialog will be in saving mode, else in loading mode.
        :param filename: the default filename to use.
        :return: the chosen filename.
        """
        # adding category to the default filename
        if not filename:
            filename = gui_g.s.default_filename
        initial_dir = os.path.dirname(filename)
        default_filename = os.path.basename(filename)  # remove dir
        default_ext = os.path.splitext(default_filename)[1]  # get extension
        default_filename = os.path.splitext(default_filename)[0]  # get filename without extension
        try:
            # if the file is empty or absent or invalid when creating the class, the filter_frame is not defined
            category = self._filter_frame.category
        except AttributeError:
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
        widget = self._control_frame.lbtf_quick_edit.get_child_by_tag(tag)
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
        try:
            while window.winfo_viewable():
                window.focus_set()
                window.attributes('-topmost', True)  # keep the window on top. Windows only
                sleep(0.5)
                self.update()
                self.update_idletasks()
        except tk.TclError:
            # the window has been closed so an error is raised
            pass

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
        canvas_image = self._control_frame.canvas_image
        try:
            row_number: int = self.editable_table.get_row_clicked(event)
            if row_number < 0 or row_number == '':
                return
            self.update_rows_text(row_number)
            image_url = self.editable_table.get_image_url(row_number)
            gui_f.show_asset_image(image_url=image_url, canvas_image=canvas_image)
        except IndexError:
            gui_f.show_default_image(canvas_image)

    def on_mouse_leave_cell(self, _event=None) -> None:
        """
        Show the default image when the mouse leaves the cell.
        :param _event:
        """
        self.update_rows_text()
        canvas_image = self._control_frame.canvas_image
        gui_f.show_default_image(canvas_image=canvas_image)

    def on_selection_change(self, event=None) -> None:
        """
        When the selection changes, show the selected row in the quick edit frame.
        :param event:
        """
        row_number = event.widget.currentrow
        self.editable_table.update_quick_edit(row_number)
        self.update_controls_and_redraw()

    def on_left_click(self, event=None) -> None:
        """
        When the left mouse button is clicked, show the selected row in the quick edit frame.
        :param event:
        """
        data_table = self.editable_table  # shortcut
        # if the clic is on a frame (i.e. an empty zone), clean the selection in the table
        if event.widget.widgetName == 'ttk::frame':
            data_table.selectNone()
            data_table.clearSelected()
            data_table.delete('rowrect')  # remove the highlight rect
        self.update_controls_and_redraw()

    def on_entry_current_item_changed(self, _event=None) -> None:
        """
        When the item (i.e. row or page) number changes, show the corresponding item.
        :param _event:
        """
        item_num = self._toolbar_frame.entry_current_item.get()
        try:
            item_num = int(item_num)
        except (ValueError, UnboundLocalError) as error:
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
        self.editable_table.on_header_release(event)
        self.enable_control('save')

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
        data_table.update_col_infos(apply_resize_cols=False)
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
        filename = self._open_file_dialog(filename=data_table.data_source)
        if filename and os.path.isfile(filename):
            data_table.data_source = filename
            if data_table.valid_source_type(filename):
                gui_f.show_progress(self, text='Loading Data from file...')
                if not data_table.read_data():
                    gui_f.box_message('Error when loading data', level='warning')
                    gui_f.close_progress(self)
                    return filename
                data_table.current_page = 1
                data_table.update(update_format=True)
                self.update_controls_and_redraw()
                self.update_data_source()
                gui_f.box_message(f'The data source {filename} as been read')
                # gui_f.close_progress(self)  # done in data_table.update(update_format=True)
                return filename
            else:
                gui_f.box_message('Operation cancelled')

    def save_changes(self, show_dialog: bool = True) -> str:
        """
        Save the data to the current data source.
        :param show_dialog: Whether to show a dialog to select the file to save to, if False, use the current file.
        :return: the name of the file that was saved.
        """
        self.save_settings()
        data_table = self.editable_table  # shortcut
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
        selected_row_indices = data_table.multiplerowlist
        if selected_row_indices:
            selected_rows = data_table.get_data().iloc[selected_row_indices]  # iloc checked
        if len(selected_rows):
            filename = self._open_file_dialog(save_mode=True, filename=data_table.data_source)
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
        data_table = self.editable_table  # shortcut
        row, new_index = data_table.create_row(row_data=row_data)
        data_table.update(update_format=True)
        data_table.move_to_row(new_index)
        data_table.must_save = True
        text = f' with asset_id={row["Asset_id"][0]}' if row is not None else ''
        gui_f.box_message(f'A new row{text} has been added at index {new_index} of the datatable')

    def del_row(self) -> None:
        """
        Remove the selected row from the DataFrame.
        """
        self.editable_table.del_row()

    def search_for_url(self, folder: str, parent: str, check_if_valid: bool = False) -> str:
        """
        Search for a marketplace_url file that matches a folder name in a given folder.
        :param folder: name to search for.
        :param parent: parent folder to search in.
        :param check_if_valid: Whether to check if the marketplace_url is valid. Return an empty string if not.
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
                    with open(entry.path, 'r') as f:
                        for line in f:
                            if line.startswith('URL='):
                                returned_urls[0] = line.replace('URL=', '').strip()
                                return True
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

    def scan_folders(self) -> None:
        """
        Scan the folders to find files that can be loaded.
        """

        def _fix_folder_structure(content_folder_name='Content'):
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
        folder_to_scan = gui_g.s.folders_to_scan
        if gui_g.s.testing_switch == 1:
            folder_to_scan = [
                'G:/Assets/pour UE/02 Warez/Environments/Elite_Landscapes_Desert_II',  #
                'G:/Assets/pour UE/00 A trier/Warez/Battle Royale Island Pack',  #
                'G:/Assets/pour UE/00 A trier/Warez/ColoradoNature',  #
                'G:/Assets/pour UE/02 Warez/Characters/Female/FurryS1 Fantasy Warrior',  #
            ]
        if self.core is None:
            gui_f.from_cli_only_message('URL Scraping and scanning features are only accessible')
            return
        if not folder_to_scan:
            gui_f.box_message('No folder to scan. Please add some in the config file', level='warning')
            return
        if not gui_f.box_yesno(
            'Specified Folders to scan saved in the config file will be processed.\nSome assets will be added to the table and the process could take come time.\nDo you want to continue ?'
        ):
            return

        pw = gui_f.show_progress(self, text='Scanning folders for new assets', width=500, height=120, show_progress_l=False, show_stop_button_l=True)
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

                folder_is_valid = folder_name_lower in gui_g.s.ue_valid_folder_content
                parent_could_be_valid = folder_name_lower in gui_g.s.ue_invalid_folder_content or folder_name_lower in gui_g.s.ue_possible_folder_content

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
                        except ReadTimeout:
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
                    _fix_folder_structure('Content')

                try:
                    for entry in os.scandir(full_folder):
                        entry_is_valid = entry.name.lower() not in gui_g.s.ue_invalid_folder_content
                        comment = ''
                        if entry.is_file():
                            asset_type = UEAssetType.Asset
                            extension_lower = os.path.splitext(entry.name)[1].lower()
                            filename_lower = os.path.splitext(entry.name)[0].lower()
                            # check if full_folder contains a "data" sub folder
                            if filename_lower == 'manifest' or extension_lower in gui_g.s.ue_valid_file_content:
                                path = full_folder
                                has_valid_folder_inside = any(
                                    os.path.isdir(path_join(full_folder, folder_inside)) for folder_inside in gui_g.s.ue_valid_manifest_content
                                )
                                if filename_lower == 'manifest':
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
                                    except ReadTimeout:
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
                                    'comment': comment
                                }
                                msg = f'-->Found {folder_name} as a valid project containing a {asset_type.name}' if extension_lower in gui_g.s.ue_valid_file_content else f'-->Found {folder_name} containing a {asset_type.name}'
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
                except FileNotFoundError:
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
            }
            if content['grab_result'] == GrabResult.NO_ERROR.name:
                try:
                    self.scrap_row(
                        marketplace_url=marketplace_url, row_index=row_index, forced_data=forced_data, show_message=False, update_dataframe=False
                    )
                except ReadTimeout:
                    gui_f.box_message(
                        f'Request timeout when accessing {marketplace_url}\n.Operation is stopped, check you internet connection or try again later.',
                        level='warning'
                    )
                    forced_data['grab_result'] = GrabResult.TIMEOUT.name
            else:
                data_table.update_row(row_number=row_index, ue_asset_data=forced_data, convert_row_number_to_row_index=False)
                data_table.add_to_rows_to_save(row_index)  # done inside self.must_save = True
        pw.hide_progress_bar()
        pw.hide_stop_button()
        pw.set_text('Updating the table. Could take a while...')
        pw.update()
        data_table.is_scanning = False
        data_table.update(update_format=True, update_filters=True)
        gui_f.close_progress(self)

        if invalid_folders:
            result = '\n'.join(invalid_folders)
            result = f'The following folders have produce invalid results during the scan:\n{result}'
            if gui_g.display_content_window_ref is None:
                gui_g.display_content_window_ref = DisplayContentWindow(title='UEVM: status command output', quit_on_close=False)
                gui_g.display_content_window_ref.display(result)
            self.logger.warning(result)

    def _scrap_from_url(self, marketplace_url: str, forced_data: {} = None, show_message: bool = False):
        asset_data = None
        # check if the marketplace_url is a marketplace marketplace_url
        ue_marketplace_url = self.core.egs.get_marketplace_product_url()
        if ue_marketplace_url.lower() in marketplace_url.lower():
            # get the data from the marketplace marketplace_url
            asset_data = self.core.egs.get_asset_data_from_marketplace(marketplace_url)
            if asset_data is None or asset_data.get('grab_result', None) != GrabResult.NO_ERROR.name or not asset_data.get('id', ''):
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
                egs=self.core.egs  # VERY IMPORTANT: pass the EGS object to the scraper to keep the same session
            )
            scraper.get_data_from_url(api_product_url)
            asset_data = scraper.pop_last_scrapped_data()  # returns a list of one element
            if forced_data is not None:
                for key, value in forced_data.items():
                    asset_data[0][key] = value
            scraper.asset_db_handler.set_assets(asset_data)
        else:
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
        :param show_message: Whether to show a message if the marketplace_url is not valid
        :param update_dataframe: Whether to update the dataframe after scraping
        """

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
            base_text = 'Scraping assets data. Could take a while...'
            if row_count > 1:
                pw = gui_f.show_progress(
                    self, text=base_text, max_value_l=row_count, width=450, height=150, show_progress_l=True, show_stop_button_l=True
                )
            for row_index in row_indexes:
                row_data = data_table.get_row(row_index, return_as_dict=True)
                marketplace_url = row_data['Url']
                asset_slug_from_url = marketplace_url.split('/')[-1]
                asset_slug_from_row = row_data['Asset slug']
                if asset_slug_from_url != asset_slug_from_row:
                    msg = f'The Asset slug from the given Url {asset_slug_from_url} is different from the existing data {asset_slug_from_row}.'
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

    def load_filters(self, filters: {} = None):
        """
        Load the filters from a dictionary.
        :param filters: filters.
        """
        if filters is None:
            return
        try:
            self._filter_frame.load_filters(filters)
            # self.update_navigation() # done in load_filters and inner calls
        except Exception as error:
            self.logger.error(f'Error loading filters: {error!r}')

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
            self._toolbar_frame.btn_toggle_pagination.config(text='Enable  Pagination')
        else:
            self._toolbar_frame.btn_toggle_pagination.config(text='Disable Pagination')
        self.update_controls_and_redraw()  # will also update buttons status

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
        self.update_controls_and_redraw()

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
        self.update_controls_and_redraw()

    def prev_page(self) -> None:
        """
        Show the previous page of the table.
        """
        self.editable_table.prev_page()
        self.update_controls_and_redraw()

    def next_page(self) -> None:
        """
        Show the next page of the table.
        """
        self.editable_table.next_page()
        self.update_controls_and_redraw()

    def prev_asset(self) -> None:
        """
        Move to the previous asset in the table.
        """
        self.editable_table.prev_row()
        self.update_controls_and_redraw()

    def next_asset(self) -> None:
        """
        Move to the next asset in the table.
        """
        self.editable_table.next_row()
        self.update_controls_and_redraw()

    # noinspection DuplicatedCode
    def toggle_actions_panel(self, force_showing: bool = None) -> None:
        """
        Toggle the visibility of the Actions panel.
        :param force_showing: Whether to will force showing the actions panel, if False, will force hiding it.If None, will toggle the visibility.
        """
        if force_showing is None:
            force_showing = not self._control_frame.winfo_ismapped()
        if force_showing:
            self._control_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
            self._toolbar_frame.btn_toggle_controls.config(text='Hide Actions')
            self._toolbar_frame.btn_toggle_options.config(state=tk.DISABLED)
        else:
            self._control_frame.pack_forget()
            self._toolbar_frame.btn_toggle_controls.config(text='Show Actions')
            self._toolbar_frame.btn_toggle_options.config(state=tk.NORMAL)

    # noinspection DuplicatedCode
    def toggle_options_panel(self, force_showing: bool = None) -> None:
        """
        Toggle the visibility of the Options panel.
        :param force_showing: Whether to will force showing the options panel, if False, will force hiding it.If None, will toggle the visibility.
        """
        # noinspection DuplicatedCode
        if force_showing is None:
            force_showing = not self._options_frame.winfo_ismapped()
        if force_showing:
            self._options_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
            self._toolbar_frame.btn_toggle_options.config(text='Hide Options')
            self._toolbar_frame.btn_toggle_controls.config(state=tk.DISABLED)
        else:
            self._options_frame.pack_forget()
            self._toolbar_frame.btn_toggle_options.config(text='Show Options')
            self._toolbar_frame.btn_toggle_controls.config(state=tk.NORMAL)

    def set_control_state(self, name: str, is_enabled: bool) -> None:
        """
        Enable or disable a control.
        :param name: name of the control.
        :param is_enabled: Whether to enable the control, if False, disable it.
        """
        control = self.controls.get(name, None)
        if control is not None:
            if name == 'save':
                # the save buttons is always on. Only its text change
                text = 'Save *' if is_enabled else 'Save  '
                control.config(text=text)
            else:
                state = tk.NORMAL if is_enabled else tk.DISABLED
                control.config(state=state)

    def enable_control(self, name: str) -> None:
        """
        Enable a control.
        :param name: name of the control.
        """
        self.set_control_state(name, True)

    def disable_control(self, name: str) -> None:
        """
        Disable a control.
        :param name: name of the control.
        """
        self.set_control_state(name, False)

    def update_controls_and_redraw(self) -> None:
        """
        Update some controls in the toolbar.
        """
        self.title(gui_g.s.app_title_long)  # the title can change with live settings

        if self._toolbar_frame is None:
            # toolbar not created yet
            return

        # Enable all controls by default
        for key in self.controls.keys():
            self.enable_control(key)

        data_table = self.editable_table  # shortcut
        # Disable some buttons if needed
        current_index = data_table.getSelectedRow()
        max_index = len(data_table.get_data())
        if len(data_table.multiplerowlist) < 1:
            self.disable_control('scrap')
            self.disable_control('del')
            self.disable_control('edit')

        if not data_table.must_save:
            self.disable_control('save')

        current_index = data_table.add_page_offset(current_index)
        if current_index <= 0:
            self.disable_control('prev_asset')
        elif current_index >= max_index - 1:
            self.disable_control('next_asset')

        if not data_table.pagination_enabled:
            max_displayed = len(data_table.get_data(df_type=DataFrameUsed.AUTO))
            first_item_text = 'First Asset'
            last_item_text = 'Last Asset'
            self.disable_control('prev_page')
            self.disable_control('next_page')
            if current_index <= 0:
                self.disable_control('first_item')
            if current_index >= max_index - 1:
                self.disable_control('last_item')
        else:
            max_displayed = data_table.total_pages
            current_index = data_table.current_page
            first_item_text = 'First Page'
            last_item_text = 'Last Page'
            if current_index <= 1:
                self.disable_control('first_item')
                self.disable_control('prev_page')
            if current_index >= max_index:
                self.disable_control('last_item')
                self.disable_control('next_page')

        # Update btn_first_item and btn_last_item text
        self._toolbar_frame.btn_first_item.config(text=first_item_text)
        self._toolbar_frame.btn_last_item.config(text=last_item_text)
        self._toolbar_frame.entry_current_item_var.set('{:04d}'.format(current_index))
        self._toolbar_frame.lbl_page_count.config(text=f'/{max_displayed:04d}')

    def update_data_source(self) -> None:
        """
        Update the data source name in the control frame.
        """
        self._control_frame.var_entry_data_source_name.set(self.editable_table.data_source)
        self._control_frame.var_entry_data_source_type.set(self.editable_table.data_source_type.name)

    def update_category_var(self) -> dict:
        """
        Update the category variable with the current categories in the data.
        :return: a dict with the new categories list as value and the key is the name of the variable.
        """
        df = self.editable_table.get_data(df_type=DataFrameUsed.UNFILTERED)
        try:
            # if the file is empty or absent or invalid when creating the class, the data is empty, so no categories
            categories = list(df['Category'].cat.categories)
        except (AttributeError, TypeError, KeyError):
            categories = []
        categories.insert(0, gui_g.s.default_value_for_all)
        try:
            # if the file is empty or absent or invalid when creating the class, the data is empty, so no categories
            grab_results = list(df['Grab result'].cat.categories)
        except (AttributeError, TypeError, KeyError):
            grab_results = []
        grab_results.insert(0, gui_g.s.default_value_for_all)
        return {'categories': categories, 'grab_results': grab_results}

    def update_rows_text(self, row_number: int = -1):
        """
        Set the text to display in the preview frame about the number of rows.
        :param row_number: row number from a datatable. Will be converted into real row index.
        """
        if self._control_frame is None:
            return
        data_table = self.editable_table  # shortcut
        df_filtered = data_table.get_data(df_type=DataFrameUsed.FILTERED)
        row_count_filtered = len(df_filtered) if df_filtered is not None else 0
        row_count = len(data_table.get_data(df_type=DataFrameUsed.UNFILTERED))
        row_text = f'| {row_count} rows count' if row_count_filtered == row_count else f'| {row_count_filtered} filtered | {row_count} total'
        if row_number >= 0:
            idx = data_table.get_real_index(row_number)
            self._control_frame.lbt_image_preview.config(text=f'Image Preview - Row Index {idx} {row_text}')
        else:
            self._control_frame.lbt_image_preview.config(text=f'No Image Preview {row_text}')

    def reload_data(self) -> None:
        """
        Reload the data from the data source.
        """
        data_table = self.editable_table  # shortcut
        if not data_table.must_save or (
            data_table.must_save and gui_f.box_yesno('Changes have been made, they will be lost. Are you sure you want to continue ?')
        ):
            self.save_settings()  # save columns order and size
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
            self.save_settings()  # save columns order and size
            if self.editable_table.rebuild_data():
                self.update_controls_and_redraw()
                self.update_category_var()
                gui_f.box_message(f'Data rebuilt from {self.editable_table.data_source}')

    def run_uevm_command(self, command_name='') -> None:
        """
        Execute a cli command and display the result in DisplayContentWindow.
        :param command_name: the name of the command to execute.
        """
        if command_name == '':
            return
        if gui_g.UEVM_cli_ref is None:
            gui_f.from_cli_only_message()
            return
        row_index: int = self.editable_table.getSelectedRow()
        app_name = self.editable_table.get_cell(row_index, self.editable_table.get_col_index('App name'))
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
        if app_name != '':
            gui_g.UEVM_cli_args['app_name'] = app_name

        # already_displayed = gui_g.display_content_window_ref is not None
        # if already_displayed:
        #     # Note: next line will raise an exption if gui_g.display_content_window_ref is None
        #     already_displayed = not gui_g.display_content_window_ref.winfo_viewable()
        #
        # if not already_displayed:
        #     # we display the window only if it is not already displayed
        #     function_to_call = getattr(gui_g.UEVM_cli_ref, command_name)
        #     function_to_call(gui_g.UEVM_cli_args)

        display_window = DisplayContentWindow(title='UEVM: status command output')
        gui_g.display_content_window_ref = display_window
        function_to_call = getattr(gui_g.UEVM_cli_ref, command_name)
        function_to_call(gui_g.UEVM_cli_args)
        self._wait_for_window(display_window)

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

    # noinspection PyUnusedLocal
    def copy_asset_id(self, tag: str, event=None) -> None:  # we keep unused params to match the signature of the callback
        """
        Copy the asset id into the clipboard.
        """
        control_frame: UEVMGuiControlFrame = self._control_frame
        value = control_frame.var_asset_id.get()
        if not value:
            return
        self.clipboard_clear()
        self.clipboard_append(value)
        self.logger.info(f'{value} copied to the clipboard.')

    def set_asset_id(self, value: str) -> None:
        """
        Set the asset id in the control frame.
        :param value: the value to set.
        """
        self._control_frame.var_asset_id.set(value)

    def json_processing(self) -> None:
        """
        Run the window to update missing data in database from json files.
        """
        if self.editable_table.data_source_type != DataSourceType.SQLITE:
            gui_f.box_message('This command can only by run with a database as data source', level='warning')
            return
        tool_window = JsonProcessingWindow(
            title='Json Files Data Processing',
            icon=gui_g.s.app_icon_filename,
            db_path=self.editable_table.data_source,
            folder_for_tags_path=gui_g.s.assets_data_folder,
            folder_for_rating_path=gui_g.s.assets_csv_files_folder
        )
        self._wait_for_window(tool_window)

    def database_processing(self) -> None:
        """
        Run the window to import/export database to csv files.
        """
        if self.editable_table.data_source_type != DataSourceType.SQLITE:
            gui_f.box_message('This command can only by run with a database as data source', level='warning')
            return
        tool_window = DbFilesWindowClass(
            title='Database Import/Export Window',
            icon=gui_g.s.app_icon_filename,
            db_path=self.editable_table.data_source,
            folder_for_csv_files=gui_g.s.assets_csv_files_folder
        )
        self._wait_for_window(tool_window)
        if tool_window.must_reload and gui_f.box_yesno('Some data has been imported into the database. Do you want to reload the data ?'):
            self.reload_data()

    def create_dynamic_filters(self) -> {str: []}:
        """
        Create a dynamic filters list that can be added to the filter frame quick filter list.
        :return: a dict that will be added to the FilterFrame quick filters list.

        Note: it returns a dict where each entry must respect the folowing format: "{'<label>': ['callable': <callable> ]}"
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
        }

    def filter_tags_with_number(self) -> pd.Series:
        """
        Create a mask to filter the data with tags that contains an integer.
        :return: a mask to filter the data.
        """
        df = self.editable_table.get_data(df_type=DataFrameUsed.UNFILTERED)
        mask = df['Tags'].str.split(',').apply(lambda x: any(is_an_int(i, gui_g.s.tag_prefix) for i in x))
        return mask

    def filter_with_comment(self) -> pd.Series:
        """
        Create a mask to filter the data with tags that contains an integer.
        :return: a mask to filter the data.
        """
        df = self.editable_table.get_data(df_type=DataFrameUsed.UNFILTERED)
        mask = df['Comment'].notnull() & df['Comment'].ne('') & df['Comment'].ne('None') & df['Comment'].ne('nan')  # not None and not empty string
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
