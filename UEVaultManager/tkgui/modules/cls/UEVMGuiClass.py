# coding=utf-8
"""
Implementation for:
- UEVMGui: the main window of the application
"""
import os
import tkinter as tk
from tkinter import filedialog as fd

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.cls.EditableTableClass import EditableTable
from UEVaultManager.tkgui.modules.comp.FilterFrameComp import FilterFrame
from UEVaultManager.tkgui.modules.comp.UEVMGuiContentFrameComp import UEVMGuiContentFrame
from UEVaultManager.tkgui.modules.comp.UEVMGuiControlFrameComp import UEVMGuiControlFrame
from UEVaultManager.tkgui.modules.comp.UEVMGuiOptionsFrameComp import UEVMGuiOptionsFrame
from UEVaultManager.tkgui.modules.comp.UEVMGuiToolbarFrameComp import UEVMGuiToolbarFrame
from UEVaultManager.tkgui.modules.functions_no_deps import set_custom_style
from UEVaultManager.tkgui.modules.types import DataSourceType


class UEVMGui(tk.Tk):
    """
    This class is used to create the main window for the application.
    :param title: The title
    :param icon: The icon
    :param screen_index: The screen index where the window will be displayed
    :param data_source: The source where the data is stored or read from
    :param data_source_type: The type of data source (DataSourceType.FILE or DataSourceType.SQLITE).
    :param show_open_file_dialog: If True, the open file dialog will be shown at startup
    """
    editable_table: EditableTable = None
    _toolbar_frame: UEVMGuiToolbarFrame = None
    _control_frame: UEVMGuiControlFrame = None
    _options_frame: UEVMGuiOptionsFrame = None
    _content_frame: UEVMGuiContentFrame = None
    _filter_frame: FilterFrame = None

    def __init__(
        self,
        title: str,
        icon='',
        screen_index=0,
        data_source_type=DataSourceType.FILE,
        data_source=None,
        show_open_file_dialog=False,
        rebuild_data=False,
    ):
        super().__init__()
        self.data_source_type = data_source_type
        if data_source_type == DataSourceType.SQLITE:
            show_open_file_dialog = False

        self.title(title)
        style = set_custom_style(gui_g.s.theme_name, gui_g.s.theme_font)
        self.style = style
        width = gui_g.s.width
        height = gui_g.s.height
        x_pos = gui_g.s.x_pos
        y_pos = gui_g.s.y_pos
        if not (x_pos and y_pos):
            x_pos, y_pos = gui_fn.get_center_screen_positions(screen_index, width, height)
        geometry: str = f'{width}x{height}+{x_pos}+{y_pos}'
        self.geometry(geometry)
        gui_fn.set_icon_and_minmax(self, icon)
        self.resizable(True, True)
        pack_def_options = {'ipadx': 5, 'ipady': 5, 'padx': 3, 'pady': 3}

        content_frame = UEVMGuiContentFrame(self)
        self._content_frame = content_frame

        # gui_g.UEVM_gui_ref = self  # important ! Must be donne before any use of a ProgressWindow. If not, an UEVMGuiHiddenRootClass will be created and the ProgressWindow still be displayed after the init
        # reading from CSV file version
        # self.editable_table = EditableTable(container=content_frame, data_source=data_source, rows_per_page=36, show_statusbar=True)

        # reading from database file version
        self.editable_table = EditableTable(
            container=content_frame,
            data_source_type=data_source_type,
            data_source=data_source,
            rows_per_page=36,
            show_statusbar=True,
            update_page_numbers_func=self.update_navigation
        )

        self.editable_table.set_preferences(gui_g.s.datatable_default_pref)

        self.editable_table.show()
        self.editable_table.update()

        toolbar_frame = UEVMGuiToolbarFrame(self, self.editable_table)
        self._toolbar_frame = toolbar_frame
        control_frame = UEVMGuiControlFrame(self, self.editable_table)
        self._control_frame = control_frame
        options_frame = UEVMGuiOptionsFrame(self)
        self._options_frame = options_frame

        toolbar_frame.pack(**pack_def_options, fill=tk.X, side=tk.TOP, anchor=tk.NW)
        content_frame.pack(**pack_def_options, fill=tk.BOTH, side=tk.LEFT, anchor=tk.NW, expand=True)
        control_frame.pack(**pack_def_options, fill=tk.BOTH, side=tk.RIGHT, anchor=tk.NW)
        # not displayed at start
        # _options_frame.pack(**pack_def_options, fill=tk.BOTH, side=tk.RIGHT, anchor=tk.NW)

        self.bind('<Key>', self.on_key_press)
        # Bind the table to the mouse motion event
        self.editable_table.bind('<Motion>', self.on_mouse_over_cell)
        self.editable_table.bind('<Leave>', self.on_mouse_leave_cell)
        self.editable_table.bind('<<CellSelectionChanged>>', self.on_selection_change)
        self.protocol('WM_DELETE_WINDOW', self.on_close)

        if not show_open_file_dialog and (rebuild_data or self.editable_table.must_rebuild):
            if gui_f.box_yesno('Data file is invalid or empty. Do you want to rebuild data from sources files ?'):
                if not self.editable_table.rebuild_data():
                    gui_f.log_error('Rebuild data error. This application could not run without a file to read from or some data to build from it')
                    self.destroy()  # self.quit() won't work here
                    return
            elif data_source_type == DataSourceType.FILE and gui_f.box_yesno(
                'So, do you want to load another file ? If not, the application will be closed'
            ):
                show_open_file_dialog = True
            else:
                self.destroy()  # self.quit() won't work here
                gui_f.log_error('No valid source to read data from. Application will be closed',)

        if show_open_file_dialog:
            if self.open_file() == '':
                gui_f.log_error('This application could not run without a file to read data from')
                self.quit()
        # Quick edit the first row
        self.editable_table.update_quick_edit(row=0)
        if gui_g.s.data_filters:
            self.load_filters(gui_g.s.data_filters)

        show_option_fist = False  # debug_only
        if show_option_fist:
            self.toggle_options_pane(True)
            self.toggle_controls_pane(False)

    def _open_file_dialog(self, save_mode=False, filename=None) -> str:
        """
        Open a file dialog to choose a file to save or load data to/from
        :param save_mode: if True, the dialog will be in saving mode, else in loading mode
        :param filename: the default filename to use
        :return: the chosen filename
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

    def _change_navigation_state(self, state: str) -> None:
        """
        Change the state of the navigation buttons
        :param state: 'normal' or 'disabled'
        """
        self._toolbar_frame.btn_first_page.config(state=state)
        self._toolbar_frame.btn_prev_page.config(state=state)
        self._toolbar_frame.btn_next_page.config(state=state)
        self._toolbar_frame.btn_last_page.config(state=state)
        self._toolbar_frame.entry_current_page.config(state=state)

    def mainloop(self, n=0):
        """ Override of mainloop method with loggin function (for debugging)"""
        gui_f.log_info(f'starting mainloop in {__name__}')
        self.tk.mainloop(n)
        gui_f.log_info(f'ending mainloop in {__name__}')

    def on_key_press(self, event) -> None:
        """
        Handle key press events
        :param event:
        """
        if event.keysym == 'Escape':
            if gui_g.edit_cell_window_ref:
                gui_g.edit_cell_window_ref.quit()
                gui_g.edit_cell_window_ref = None
            elif gui_g.edit_row_window_ref:
                gui_g.edit_row_window_ref.quit()
                gui_g.edit_row_window_ref = None
            else:
                self.on_close()
        # elif event.keysym == 'Return':
        #    self.editable_table.create_edit_record_window()

    def on_mouse_over_cell(self, event=None) -> None:
        """
        Show the image of the asset when the mouse is over the cell
        :param event:
        """
        if event is None:
            return
        canvas_image = self._control_frame.canvas_image
        try:
            image_url = self.editable_table.get_image_url(row=self.editable_table.get_row_clicked(event))
            gui_f.show_asset_image(image_url=image_url, canvas_image=canvas_image)
        except IndexError:
            gui_f.show_default_image(canvas_image)

    def on_mouse_leave_cell(self, _event=None) -> None:
        """
        Show the default image when the mouse leaves the cell
        :param _event:
        """
        canvas_image = self._control_frame.canvas_image
        gui_f.show_default_image(canvas_image=canvas_image)

    def on_selection_change(self, event=None) -> None:
        """
        When the selection changes, show the selected row in the quick edit frame
        :param event:
        """
        selected_row = event.widget.currentrow
        self.editable_table.update_quick_edit(row=selected_row)

    def on_entry_current_page_changed(self, _event=None) -> None:
        """
        When the page number changes, show the corresponding page
        :param _event:
        """
        page_num = 1
        try:
            page_num = self._toolbar_frame.entry_current_page.get()
            page_num = int(page_num)
            gui_f.log_debug(f'showing page {page_num}')
            self.editable_table.current_page = page_num
            self.editable_table.update()
        except (ValueError, UnboundLocalError) as error:
            gui_f.log_error(f'could not convert page number {page_num} to int. {error!r}')

    # noinspection PyUnusedLocal
    def on_quick_edit_focus_out(self, event=None, tag='') -> None:
        """
        When the focus leaves a quick edit widget, save the value
        :param event: ignored but required for an event handler
        :param tag: tag of the widget that triggered the event
        """
        value, widget = self._check_and_get_widget_value(tag=tag)
        if widget:
            self.editable_table.quick_edit_save_value(col=widget.col, row=widget.row, value=value, tag=tag)

    # noinspection PyUnusedLocal
    def on_quick_edit_focus_in(self, event=None, tag='') -> None:
        """
        When the focus enter a quick edit widget, check (and clean) the value
        :param event: ignored but required for an event handler
        :param tag: tag of the widget that triggered the event
        """
        value, widget = self._check_and_get_widget_value(tag=tag)
        # empty the widget if the value is the default value or none
        if widget and (value == 'None' or value == widget.default_content or value == gui_g.s.empty_cell):
            value = ''
            widget.set_content(value)

    def _check_and_get_widget_value(self, tag):
        """
        Check if the widget with the given tags exists and return its value and itself
        :param tag: tag of the widget that triggered the event
        :return: value,widget
        """
        if tag == '':
            return None, None
        widget = self._control_frame.lbtf_quick_edit.get_child_by_tag(tag)
        if widget is None:
            gui_f.log_warning(f'Could not find a widget with tag {tag}')
            return None, None
        col = widget.col
        row = widget.row
        if col is None or row is None or col < 0 or row < 0:
            gui_f.log_debug(f'invalid values for row={row} and col={col}')
            return None, widget
        value = widget.get_content()
        return value, widget

    # noinspection PyUnusedLocal
    def on_switch_edit_flag(self, event=None, tag='') -> None:
        """
        When the focus leaves a quick edit widget, save the value
        :param event: event that triggered the call
        :param tag: tag of the widget that triggered the event
        """
        _, widget = self._check_and_get_widget_value(tag=tag)
        if widget:
            value = widget.switch_state(event=event)
            self.editable_table.quick_edit_save_value(col=widget.col, row=widget.row, value=value, tag=tag)

    def on_close(self, _event=None) -> None:
        """
        When the window is closed, check if there are unsaved changes and ask the user if he wants to save them
        :param _event: the event that triggered the call of this function
        """
        if self.editable_table is not None and self.editable_table.must_save:
            if gui_f.box_yesno('Changes have been made. Do you want to save them in the source file ?'):
                self.save_file(show_dialog=False)
        self.close_window()

    def close_window(self) -> None:
        """
        Close the window
        """
        if gui_g.s.reopen_last_file:
            gui_g.s.last_opened_file = self.editable_table.data_source
        # store window geometry in config settings
        gui_g.s.width = self.winfo_width()
        gui_g.s.height = self.winfo_height()
        gui_g.s.x_pos = self.winfo_x()
        gui_g.s.y_pos = self.winfo_y()
        gui_g.s.save_config_file()
        self.quit()

    def open_file(self) -> str:
        """
        Open a file and Load data from it
        :return: the name of the file that was loaded
        """
        data_table = self.editable_table
        filename = self._open_file_dialog(filename=data_table.data_source)
        if filename and os.path.isfile(filename):
            data_table.data_source = filename
            if data_table.valid_source_type(filename):
                if not data_table.load_data():
                    gui_f.box_message('Error when loading data')
                    return filename
                data_table.current_page = 1
                data_table.update()
                self.update_navigation()
                self.update_data_source()
                gui_f.box_message(f'The data source {filename} as been read')
                return filename
            else:
                gui_f.box_message('Operation cancelled')

    def save_file(self, show_dialog=True) -> str:
        """
        Save the data to the current data source
        :param show_dialog: if True, show a dialog to select the file to save to, if False, use the current file
        """
        if self.editable_table.data_source_type == DataSourceType.FILE:
            if show_dialog:
                filename = self._open_file_dialog(filename=self.editable_table.data_source, save_mode=True)
                if filename:
                    self.editable_table.data_source = filename
            else:
                filename = self.editable_table.data_source
            if filename:
                self.editable_table.save_data()
                self.update_data_source()
                # gui_f.box_message(f'Data Saved to {self.editable_table.data_source}')
            return filename
        else:
            self.editable_table.save_data()
            return ''

    def export_selection(self) -> None:
        """
        Export the selected rows to a file
        """
        # Get selected row indices
        selected_rows = self.editable_table.get_selected_rows()
        if selected_rows:
            filename = self._open_file_dialog(save_mode=True, filename=self.editable_table.data_source)
            if filename:
                selected_rows.to_csv(filename, index=False)
                gui_f.box_message(f'Selected rows exported to "{filename}"')
            else:
                gui_f.box_message('Select at least one row first')

    def load_filters(self, filters=None):
        """
        Load the filters from a dictionary
        :param filters: filters
        """
        if filters is None:
            return
        try:
            self._filter_frame.load_filters(filters)
            # self.update_navigation() # done in load_filters and inner calls
        except Exception as error:
            gui_f.log_error(f'Error loading filters: {error!r}')

    def toggle_pagination(self, forced_value=None) -> None:
        """
        Toggle pagination. Will change the navigation buttons states when pagination is changed
        :param forced_value: if not None, will force the pagination to the given value
        """
        if forced_value is not None:
            self.editable_table.pagination_enabled = forced_value
        else:
            self.editable_table.pagination_enabled = not self.editable_table.pagination_enabled
        self.editable_table.update()
        if not self.editable_table.pagination_enabled:
            # Disable prev/next buttons when pagination is disabled
            self._change_navigation_state(tk.DISABLED)
            self._toolbar_frame.btn_toggle_pagination.config(text='Enable  Pagination')
        else:
            self.update_navigation()  # will also update buttons status
            self._toolbar_frame.btn_toggle_pagination.config(text='Disable Pagination')

    def show_first_page(self) -> None:
        """
        Show the first page of the table
        """
        self.editable_table.first_page()
        self.update_navigation()

    def show_prev_page(self) -> None:
        """
        Show the previous page of the table
        """
        self.editable_table.prev_page()
        self.update_navigation()

    def show_next_page(self) -> None:
        """
        Show the next page of the table
        """
        self.editable_table.next_page()
        self.update_navigation()

    def show_last_page(self) -> None:
        """
        Show the last page of the table
        """
        self.editable_table.last_page()
        self.update_navigation()

    def prev_asset(self) -> None:
        """
        Move to the previous asset in the table
        """
        self.editable_table.move_to_prev_record()

    def next_asset(self) -> None:
        """
        Move to the next asset in the table
        """
        self.editable_table.move_to_next_record()

    # noinspection DuplicatedCode
    def toggle_controls_pane(self, force_showing=None) -> None:
        """
        Toggle the visibility of the controls pane
        :param force_showing: if True, will force showing the options pane, if False, will force hiding it.If None, will toggle the visibility
        """
        if force_showing is None:
            force_showing = not self._control_frame.winfo_ismapped()
        if force_showing:
            self._control_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
            self._toolbar_frame.btn_toggle_controls.config(text='Hide Control')
            self._toolbar_frame.btn_toggle_options.config(state=tk.DISABLED)
        else:
            self._control_frame.pack_forget()
            self._toolbar_frame.btn_toggle_controls.config(text='Show Control')
            self._toolbar_frame.btn_toggle_options.config(state=tk.NORMAL)

    # noinspection DuplicatedCode
    def toggle_options_pane(self, force_showing=None) -> None:
        """
        Toggle the visibility of the Options pane
        :param force_showing: if True, will force showing the options pane, if False, will force hiding it.If None, will toggle the visibility
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

    def update_navigation(self) -> None:
        """
        Update the page numbers in the toolbar
        """
        if self._toolbar_frame is None:
            # toolbar not created yet
            return
        current_page = self.editable_table.current_page
        total_pages = self.editable_table.total_pages
        self._toolbar_frame.entry_current_page_var.set(current_page)
        self._toolbar_frame.lbl_page_count.config(text=f' / {total_pages}')
        # enable all buttons by default
        self._change_navigation_state(tk.NORMAL)

        if not self.editable_table.pagination_enabled:
            self._toolbar_frame.entry_current_page.config(state=tk.NORMAL)
        if current_page <= 1:
            self._toolbar_frame.btn_first_page.config(state=tk.DISABLED)
            self._toolbar_frame.btn_prev_page.config(state=tk.DISABLED)
        if current_page >= total_pages:
            self._toolbar_frame.btn_next_page.config(state=tk.DISABLED)
            self._toolbar_frame.btn_last_page.config(state=tk.DISABLED)

    def update_data_source(self) -> None:
        """
        Update the data source name in the control frame
        """
        self._control_frame.var_entry_data_source_name.set(self.editable_table.data_source)
        self._control_frame.var_entry_data_source_type.set(self.editable_table.data_source_type.name)

    def update_category_var(self) -> dict:
        """
        Update the category variable with the current categories in the data
        :return: a dict with the new categories list as value and the key is the name of the variable.
        """
        try:
            # if the file is empty or absent or invalid when creating the class, the data is empty, so no categories
            categories = list(self.editable_table.get_data()['Category'].cat.categories)
        except (AttributeError, TypeError, KeyError):
            categories = []
        categories.insert(0, gui_g.s.default_value_for_all)
        try:
            # if the file is empty or absent or invalid when creating the class, the data is empty, so no categories
            grab_results = list(self.editable_table.get_data()['Grab result'].cat.categories)
        except (AttributeError, TypeError, KeyError):
            grab_results = []
        grab_results.insert(0, gui_g.s.default_value_for_all)
        return {'categories': categories, 'grab_results': grab_results}

    def reload_data(self) -> None:
        """
        Reload the data from the data source
        """
        if not self.editable_table.must_save or (
            self.editable_table.must_save and gui_f.box_yesno('Changes have been made, they will be lost. Are you sure you want to continue ?')
        ):
            if self.editable_table.reload_data():
                # self.update_page_numbers() done in reload_data
                self.update_category_var()
                gui_f.box_message(f'Data Reloaded from {self.editable_table.data_source}')
            else:
                gui_f.box_message(f'Failed to reload data from {self.editable_table.data_source}')

    def rebuild_data(self) -> None:
        """
        Rebuild the data from the data source. Will ask for confirmation before rebuilding
        """
        if gui_f.box_yesno(f'The process will change the content of the windows.\nAre you sure you want to continue ?'):
            if self.editable_table.rebuild_data():
                self.update_navigation()
                self.update_category_var()
                gui_f.box_message(f'Data rebuilt from {self.editable_table.data_source}')

    def run_uevm_command(self, command_name='') -> None:
        """
        Execute a cli command and display the result in DisplayContentWindow
        :param command_name: the name of the command to execute
        """
        if command_name == '':
            return
        if gui_g.UEVM_cli_ref is None:
            gui_f.from_cli_only_message()
            return
        row = self.editable_table.getSelectedRow()
        col = self.editable_table.get_data().columns.get_loc('App name')
        app_name = self.editable_table.get_cell(row, col)
        # gui_g.UEVM_cli_args['offline'] = True  # speed up some commands DEBUG ONLY
        # set default options for the cli command to execute
        gui_g.UEVM_cli_args['gui'] = True  # mandatory for displaying the result in the DisplayContentWindow

        # arguments for several commands
        gui_g.UEVM_cli_args['csv'] = False  # mandatory for displaying the result in the DisplayContentWindow
        gui_g.UEVM_cli_args['tcsv'] = False  # mandatory for displaying the result in the DisplayContentWindow
        gui_g.UEVM_cli_args['json'] = False  # mandatory for displaying the result in the DisplayContentWindow

        # arguments for cleanup command
        # now set in command options
        # gui_g.UEVM_cli_args['delete_extras_data'] = True
        # gui_g.UEVM_cli_args['delete_metadata'] = True

        # arguments for help command
        gui_g.UEVM_cli_args['full_help'] = True
        if app_name != '':
            gui_g.UEVM_cli_args['app_name'] = app_name

        if gui_g.display_content_window_ref is None or not gui_g.display_content_window_ref.winfo_viewable():
            # we display the window only if it is not already displayed
            function_to_call = getattr(gui_g.UEVM_cli_ref, command_name)
            function_to_call(gui_g.UEVM_cli_args)

    # noinspection PyUnusedLocal
    def open_asset_url(self, event=None) -> None:
        """
        Open the asset URL (Wrapper)
        """
        url, widget = self._check_and_get_widget_value(tag='Url')
        if url:
            self.editable_table.open_asset_url(url=url)
