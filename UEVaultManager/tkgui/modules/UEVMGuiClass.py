# coding=utf-8
"""
Implementation for:
- UEVMGui: the main window of the application
"""
import os
import tkinter as tk
from tkinter import filedialog as fd

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.EditableTableClass import EditableTable, DataSourceType
from UEVaultManager.tkgui.modules.FilterFrameClass import FilterFrame
from UEVaultManager.tkgui.modules.functions_no_deps import set_custom_style
from UEVaultManager.tkgui.modules.TaggedLabelFrameClass import TaggedLabelFrame, WidgetType


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
    _filter_frame: FilterFrame = None
    editable_table: EditableTable = None

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

        table_frame = self.TableFrame(self)

        # gui_g.UEVM_gui_ref = self  # important ! Must be donne before any use of a ProgressWindow. If not, an UEVMGuiHiddenRootClass will be created and the ProgressWindow still be displayed after the init
        # reading from CSV file version
        # self.editable_table = EditableTable(container_frame=table_frame, data_source=data_source, rows_per_page=36, show_statusbar=True)

        # reading from database file version
        self.editable_table = EditableTable(
            container_frame=table_frame, data_source_type=data_source_type, data_source=data_source, rows_per_page=36, show_statusbar=True
        )

        self.editable_table.set_preferences(gui_g.s.datatable_default_pref)

        self.editable_table.show()
        self.editable_table.update()

        toolbar_frame = self.ToolbarFrame(self, self.editable_table)
        self._toolbar_frame = toolbar_frame
        control_frame = self.ControlFrame(self, self.editable_table)
        self._control_frame = control_frame
        options_frame = self.OptionsFrame(self)
        self._options_frame = options_frame

        toolbar_frame.pack(**pack_def_options, fill=tk.X, side=tk.TOP, anchor=tk.NW)
        table_frame.pack(**pack_def_options, fill=tk.BOTH, side=tk.LEFT, anchor=tk.NW, expand=True)
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
            if self.load_data() == '':
                gui_f.log_error('This application could not run without a file to read data from')
                self.quit()
        # Quick edit the first row
        self.editable_table.update_quick_edit(row=0)
        if gui_g.s.data_filters:
            self._filter_frame.load_filters(gui_g.s.data_filters)

    class ToolbarFrame(ttk.Frame):
        """
        This class is used to create the toolbar frame
        :param container: The parent container.
        :param data_table: The EditableTable instance
        """

        def __init__(self, container, data_table: EditableTable):
            super().__init__()
            if container is None:
                raise ValueError('container must be None')
            if data_table is None:
                raise ValueError('data_table must be a TableFrame instance')

            self.data_table: EditableTable = data_table

            pack_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.BOTH, 'expand': False}
            lblf_def_options = {'ipadx': 1, 'ipady': 1, 'expand': False}

            lblf_navigation = ttk.LabelFrame(self, text='Navigation')
            lblf_navigation.pack(side=tk.LEFT, **lblf_def_options)
            # (bootstyle is not recognized by PyCharm)
            # noinspection PyArgumentList
            btn_toggle_pagination = ttk.Button(lblf_navigation, text='Disable Pagination', command=container.toggle_pagination)
            # noinspection PyArgumentList
            btn_toggle_pagination.pack(**pack_def_options, side=tk.LEFT)
            btn_first_page = ttk.Button(lblf_navigation, text='First Page', command=container.show_first_page)
            btn_first_page.pack(**pack_def_options, side=tk.LEFT)
            btn_first_page.config(state=tk.DISABLED)
            btn_prev_page = ttk.Button(lblf_navigation, text='Prev Page', command=container.show_prev_page)
            btn_prev_page.pack(**pack_def_options, side=tk.LEFT)
            btn_prev_page.config(state=tk.DISABLED)
            entry_page_num_var = tk.StringVar(value=data_table.current_page)
            entry_page_num = ttk.Entry(lblf_navigation, width=5, justify=tk.CENTER, textvariable=entry_page_num_var)
            entry_page_num.pack(**pack_def_options, side=tk.LEFT)
            lbl_page_count = ttk.Label(lblf_navigation, text=f' / {data_table.total_pages}')
            lbl_page_count.pack(**pack_def_options, side=tk.LEFT)
            btn_next_page = ttk.Button(lblf_navigation, text='Next Page', command=container.show_next_page)
            btn_next_page.pack(**pack_def_options, side=tk.LEFT)
            btn_last_page = ttk.Button(lblf_navigation, text='Last Page', command=container.show_last_page)
            btn_last_page.pack(**pack_def_options, side=tk.LEFT)
            btn_prev = ttk.Button(lblf_navigation, text='Prev Asset', command=container.prev_asset)
            btn_prev.pack(**pack_def_options, side=tk.LEFT)
            btn_next = ttk.Button(lblf_navigation, text='Next Asset', command=container.next_asset)
            btn_next.pack(**pack_def_options, side=tk.RIGHT)

            lblf_display = ttk.LabelFrame(self, text='Display')
            lblf_display.pack(side=tk.LEFT, **lblf_def_options)
            btn_expand = ttk.Button(lblf_display, text='Expand Cols', command=data_table.expand_columns)
            btn_expand.pack(**pack_def_options, side=tk.LEFT)
            btn_shrink = ttk.Button(lblf_display, text='Shrink Cols', command=data_table.contract_columns)
            btn_shrink.pack(**pack_def_options, side=tk.LEFT)
            btn_autofit = ttk.Button(lblf_display, text='Autofit Cols', command=data_table.autofit_columns)
            btn_autofit.pack(**pack_def_options, side=tk.LEFT)
            btn_zoom_in = ttk.Button(lblf_display, text='Zoom In', command=data_table.zoom_in)
            btn_zoom_in.pack(**pack_def_options, side=tk.LEFT)
            btn_zoom_out = ttk.Button(lblf_display, text='Zoom Out', command=data_table.zoom_out)
            btn_zoom_out.pack(**pack_def_options, side=tk.LEFT)

            lblf_commands = ttk.LabelFrame(self, text='Cli commands')
            lblf_commands.pack(side=tk.LEFT, **lblf_def_options)
            btn_help = ttk.Button(lblf_commands, text='Help', command=lambda: container.run_uevm_command('print_help'))
            btn_help.pack(**pack_def_options, side=tk.LEFT)
            btn_status = ttk.Button(lblf_commands, text='Status', command=lambda: container.run_uevm_command('status'))
            btn_status.pack(**pack_def_options, side=tk.LEFT)
            btn_info = ttk.Button(lblf_commands, text='Info', command=lambda: container.run_uevm_command('info'))
            btn_info.pack(**pack_def_options, side=tk.LEFT)
            btn_list_files = ttk.Button(lblf_commands, text='List Files', command=lambda: container.run_uevm_command('list_files'))
            btn_list_files.pack(**pack_def_options, side=tk.LEFT)
            btn_cleanup = ttk.Button(lblf_commands, text='Cleanup', command=lambda: container.run_uevm_command('cleanup'))
            btn_cleanup.pack(**pack_def_options, side=tk.LEFT)

            lblf_actions = ttk.LabelFrame(self, text='Actions')
            lblf_actions.pack(side=tk.RIGHT, **lblf_def_options)
            # noinspection PyArgumentList
            btn_toggle_options = ttk.Button(lblf_actions, text='Show Options', command=container.toggle_options_pane, state=tk.DISABLED)
            btn_toggle_options.pack(**pack_def_options, side=tk.LEFT)
            # noinspection PyArgumentList
            btn_toggle_controls = ttk.Button(lblf_actions, text='Hide Controls', command=container.toggle_controls_pane)
            btn_toggle_controls.pack(**pack_def_options, side=tk.LEFT)
            # noinspection PyArgumentList
            btn_on_close = ttk.Button(lblf_actions, text='Quit', command=container.on_close, bootstyle=WARNING)
            btn_on_close.pack(**pack_def_options, side=tk.RIGHT)

            # Bind events for the Entry widget
            entry_page_num.bind('<FocusOut>', container.on_entry_page_num_changed)
            entry_page_num.bind('<Return>', container.on_entry_page_num_changed)

            self.btn_toggle_pagination = btn_toggle_pagination
            self.btn_first_page = btn_first_page
            self.btn_prev_page = btn_prev_page
            self.btn_next_page = btn_next_page
            self.btn_last_page = btn_last_page
            self.btn_toggle_options = btn_toggle_options
            self.btn_toggle_controls = btn_toggle_controls
            self.lbl_page_count = lbl_page_count
            self.entry_page_num = entry_page_num
            self.entry_page_num_var = entry_page_num_var

    class TableFrame(ttk.Frame):
        """
        The TableFrame is a container for the Table widget.
        :param container: The parent container.
        """

        def __init__(self, container):
            if container is None:
                raise ValueError('container must be None')
            super().__init__(container)

            self.container = container

    class ControlFrame(ttk.Frame):
        """
        The ControlFrame is a container for the filter controls.
        :param container: The parent container.
        :param data_table: The EditableTable instance
        """

        def __init__(self, container, data_table: EditableTable):
            super().__init__()
            if container is None:
                raise ValueError('container must be None')
            if data_table is None:
                raise ValueError('data_table must be a TableFrame instance')

            self.data_table: EditableTable = data_table

            grid_def_options = {'ipadx': 1, 'ipady': 1, 'padx': 1, 'pady': 1, 'sticky': tk.SE}
            grid_def_options_np = {'ipadx': 0, 'ipady': 0, 'padx': 0, 'pady': 0, 'sticky': tk.SE}  # no padding
            # pack_def_options = {'ipadx': 2, 'ipady': 2, 'fill': tk.BOTH, 'expand': False}
            grid_fw_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'sticky': tk.EW}  # full width
            lblf_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.X, 'expand': False}
            lblf_fw_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.X, 'expand': True}  # full width

            lblf_content = ttk.LabelFrame(self, text='Content')
            lblf_content.pack(**lblf_def_options)
            btn_edit_row = ttk.Button(lblf_content, text='Edit Row', command=data_table.create_edit_record_window)
            btn_edit_row.grid(row=0, column=0, **grid_fw_options)
            btn_reload_data = ttk.Button(lblf_content, text='Reload Content', command=container.reload_data)
            btn_reload_data.grid(row=0, column=1, **grid_fw_options)
            btn_rebuild_file = ttk.Button(lblf_content, text='Rebuild Content', command=container.rebuild_data)
            btn_rebuild_file.grid(row=0, column=2, **grid_fw_options)
            lblf_content.columnconfigure('all', weight=1)  # important to make the buttons expand

            filter_frame = FilterFrame(
                self, data_func=data_table.get_data, update_func=data_table.update, value_for_all=gui_g.s.default_value_for_all
            )
            filter_frame.pack(**lblf_def_options)
            container._filter_frame = filter_frame
            data_table.set_filter_frame(filter_frame)

            lblf_files = ttk.LabelFrame(self, text='Files')
            lblf_files.pack(**lblf_def_options)
            lbl_data_source = ttk.Label(lblf_files, text='Data Source: ')
            lbl_data_source.grid(row=0, column=0, columnspan=2, **grid_fw_options)
            frm_inner = ttk.Frame(lblf_files)
            frm_inner.grid(row=0, column=2, **grid_fw_options)

            lbl_data_type = ttk.Label(frm_inner, text='Type: ')
            lbl_data_type.grid(row=0, column=0, **grid_def_options_np)
            var_entry_data_source_type = tk.StringVar(value=data_table.data_source_type.name)
            # noinspection PyArgumentList
            entry_data_type = ttk.Entry(frm_inner, textvariable=var_entry_data_source_type, state='readonly', width=6, bootstyle=WARNING)
            entry_data_type.grid(row=0, column=1, **grid_def_options_np)

            var_entry_data_source_name = tk.StringVar(value=data_table.data_source)
            entry_data_source = ttk.Entry(lblf_files, textvariable=var_entry_data_source_name, state='readonly')
            entry_data_source.grid(row=1, column=0, columnspan=3, **grid_fw_options)
            btn_save_data = ttk.Button(lblf_files, text='Save Data', command=container.save_data)
            btn_save_data.grid(row=2, column=0, **grid_fw_options)
            btn_export_button = ttk.Button(lblf_files, text='Export Selection', command=container.export_selection)
            btn_export_button.grid(row=2, column=1, **grid_fw_options)
            btn_load_data = ttk.Button(lblf_files, text='Load Data', command=container.load_data)
            btn_load_data.grid(row=2, column=2, **grid_fw_options)
            lblf_files.columnconfigure('all', weight=1)  # important to make the buttons expand

            # Note: the TAG of the child widgets of the lbf_quick_edit will also be used in the editable_table.quick_edit method
            # to get the widgets it needs. So they can't be changed freely
            lbtf_quick_edit = TaggedLabelFrame(self, text='Quick Edit User fields')
            lbtf_quick_edit.pack(**lblf_fw_options, anchor=tk.NW)
            data_table.set_quick_edit_frame(lbtf_quick_edit)

            frm_inner_frame = ttk.Frame(lbtf_quick_edit)
            lbl_desc = ttk.Label(frm_inner_frame, text='Changing this values will change the values of \nthe selected row when losing focus')
            lbl_desc.grid(row=0, column=0, **grid_def_options)
            bt_open_url = ttk.Button(frm_inner_frame, text='Open Url', command=container.open_asset_url)
            bt_open_url.grid(row=0, column=1, **grid_def_options)
            frm_inner_frame.pack()

            lbtf_quick_edit.add_child(
                widget_type=WidgetType.ENTRY,
                tag='Url',
                focus_out_callback=container.on_quick_edit_focus_out,
                focus_in_callback=container.on_quick_edit_focus_in
            )
            lbtf_quick_edit.add_child(
                widget_type=WidgetType.TEXT,
                tag='Comment',
                focus_out_callback=container.on_quick_edit_focus_out,
                focus_in_callback=container.on_quick_edit_focus_in,
                width=10,
                height=4
            )
            lbtf_quick_edit.add_child(
                widget_type=WidgetType.ENTRY,
                tag='Stars',
                focus_out_callback=container.on_quick_edit_focus_out,
                focus_in_callback=container.on_quick_edit_focus_in
            )
            lbtf_quick_edit.add_child(
                widget_type=WidgetType.ENTRY,
                tag='Test result',
                focus_out_callback=container.on_quick_edit_focus_out,
                focus_in_callback=container.on_quick_edit_focus_in
            )

            lbtf_quick_edit.add_child(
                widget_type=WidgetType.ENTRY,
                tag='Installed folder',
                default_content='Installed in',
                focus_out_callback=container.on_quick_edit_focus_out,
                focus_in_callback=container.on_quick_edit_focus_in
            )
            lbtf_quick_edit.add_child(
                widget_type=WidgetType.ENTRY,
                tag='Origin',
                focus_out_callback=container.on_quick_edit_focus_out,
                focus_in_callback=container.on_quick_edit_focus_in
            )
            lbtf_quick_edit.add_child(
                widget_type=WidgetType.ENTRY,
                tag='Alternative',
                focus_out_callback=container.on_quick_edit_focus_out,
                focus_in_callback=container.on_quick_edit_focus_in
            )

            frm_inner_frame = ttk.Frame(lbtf_quick_edit, relief=tk.RIDGE, borderwidth=1)
            inner_pack_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.X, 'expand': False, 'anchor': tk.W}
            frm_inner_frame.pack(**inner_pack_options)
            lbtf_quick_edit.add_child(
                widget_type=WidgetType.CHECKBUTTON,
                alternate_container=frm_inner_frame,
                layout_option=inner_pack_options,
                tag='Must buy',
                label='',
                images_folder=gui_g.s.assets_folder,
                click_on_callback=container.on_switch_edit_flag,
                default_content=False
            )
            lbtf_quick_edit.add_child(
                widget_type=WidgetType.CHECKBUTTON,
                alternate_container=frm_inner_frame,
                layout_option=inner_pack_options,
                tag='Added manually',
                label='',
                images_folder=gui_g.s.assets_folder,
                click_on_callback=container.on_switch_edit_flag,
                default_content=False
            )
            lbt_image_preview = ttk.LabelFrame(self, text='Image Preview')
            lbt_image_preview.pack(**lblf_fw_options, anchor=tk.SW)
            canvas_image = tk.Canvas(lbt_image_preview, width=gui_g.s.preview_max_width, height=gui_g.s.preview_max_height, highlightthickness=0)
            canvas_image.pack(side=tk.BOTTOM, expand=True, anchor=tk.CENTER)
            canvas_image.create_rectangle((0, 0), (gui_g.s.preview_max_width, gui_g.s.preview_max_height), fill='black')

            lblf_bottom = ttk.Frame(self)
            lblf_bottom.pack(**lblf_def_options)
            ttk.Sizegrip(lblf_bottom).pack(side=tk.RIGHT)

            # store the controls that need to be accessible outside the class
            self.var_entry_data_source_name = var_entry_data_source_name
            self.var_entry_data_source_type = var_entry_data_source_type

            self.lbtf_quick_edit = lbtf_quick_edit
            self.canvas_image = canvas_image

    class OptionsFrame(ttk.Frame):
        """
        This class is used to create the toolbar frame
        :param _container: The parent container
        """

        def __init__(self, _container):
            super().__init__()
            # pack_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.BOTH, 'expand': False}
            lblf_def_options = {'ipadx': 1, 'ipady': 1, 'expand': False}
            grid_fw_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'sticky': tk.EW}  # full width

            lblf_options = ttk.LabelFrame(self, text='Command Options')
            lblf_options.pack(side=tk.TOP, **lblf_def_options)
            # row 0
            cur_col = 0
            cur_row = 0
            force_refresh_var = tk.BooleanVar(value=gui_g.UEVM_cli_args.get('force', False))
            force_refresh_var.trace_add('write', lambda name, index, mode: gui_g.set_args_force_refresh(force_refresh_var.get()))
            ck_force_refresh = ttk.Checkbutton(lblf_options, text='Force refresh', variable=force_refresh_var)
            ck_force_refresh.grid(row=cur_row, column=cur_col, **grid_fw_options)
            # row 1
            cur_row += 1
            cur_col = 0
            offline_var = tk.BooleanVar(value=gui_g.UEVM_cli_args.get('offline', False))
            offline_var.trace_add('write', lambda name, index, mode: gui_g.set_args_offline(offline_var.get()))
            ck_offline = ttk.Checkbutton(lblf_options, text='Offline Mode', variable=offline_var)
            ck_offline.grid(row=cur_row, column=cur_col, **grid_fw_options)
            # row 2
            cur_row += 1
            cur_col = 0
            debug_var = tk.BooleanVar(value=gui_g.UEVM_cli_args.get('debug', False))
            debug_var.trace_add('write', lambda name, index, mode: gui_g.set_args_debug(debug_var.get()))
            ck_debug = ttk.Checkbutton(lblf_options, text='Debug mode', variable=debug_var)
            ck_debug.grid(row=cur_row, column=cur_col, **grid_fw_options)
            # row 3
            # delete_extras_data'] = True
            cur_row += 1
            cur_col = 0
            delete_metadata_var = tk.BooleanVar(value=gui_g.UEVM_cli_args.get('delete_metadata', False))
            delete_metadata_var.trace_add('write', lambda name, index, mode: gui_g.set_args_delete_metadata(delete_metadata_var.get()))
            ck_delete_metadata = ttk.Checkbutton(lblf_options, text='Delete metadata (cleanup)', variable=delete_metadata_var)
            ck_delete_metadata.grid(row=cur_row, column=cur_col, **grid_fw_options)
            # row 4
            cur_row += 1
            cur_col = 0
            delete_extras_data_var = tk.BooleanVar(value=gui_g.UEVM_cli_args.get('delete_extras_data', False))
            delete_extras_data_var.trace_add('write', lambda name, index, mode: gui_g.set_args_delete_extras_data(delete_extras_data_var.get()))
            ck_delete_extras_data = ttk.Checkbutton(lblf_options, text='Delete metadata (cleanup)', variable=delete_extras_data_var)
            ck_delete_extras_data.grid(row=cur_row, column=cur_col, **grid_fw_options)

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
        self._toolbar_frame.entry_page_num.config(state=state)

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

    def on_entry_page_num_changed(self, _event=None) -> None:
        """
        When the page number changes, show the corresponding page
        :param _event:
        """
        page_num = 1
        try:
            page_num = self._toolbar_frame.entry_page_num.get()
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
                self.save_data(show_dialog=False)
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

    def load_data(self) -> str:
        """
        Load data from the current data source
        :return: the name of the file that was loaded
        """
        filename = self._open_file_dialog(filename=self.editable_table.data_source)
        if filename and os.path.isfile(filename):
            self.editable_table.data_source = filename
            file, ext = os.path.splitext(filename)
            old_type = self.editable_table.data_source_type
            self.editable_table.data_source_type = DataSourceType.SQLITE if ext == '.db' else DataSourceType.FILE
            go_on = True
            if old_type != self.editable_table.data_source_type:
                go_on = gui_f.box_yesno(
                    f'The type of data source has changed from the previous one.\nYou should quit and restart the application to avoid any data loss.\nAre you sure you want to continue ?'
                )

            if go_on:
                self.editable_table.load_data()
                self.editable_table.current_page = 1
                self.editable_table.update()
                self.update_page_numbers()
                self.update_data_source()
                gui_f.box_message(f'The data source {filename} as been read')
                return filename
            else:
                gui_f.box_message('Operation cancelled')

    def save_data(self, show_dialog=True) -> str:
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

    def load_filter(self, filters=None):
        """
        Load the filters from a dictionary
        :param filters: filters
        """
        if filters is None:
            return
        try:
            self._filter_frame.load_filters(filters)
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
            self.update_page_numbers()  # will also update buttons status
            self._toolbar_frame.btn_toggle_pagination.config(text='Disable Pagination')

    def show_first_page(self) -> None:
        """
        Show the first page of the table
        """
        self.editable_table.first_page()
        self.update_page_numbers()

    def show_prev_page(self) -> None:
        """
        Show the previous page of the table
        """
        self.editable_table.prev_page()
        self.update_page_numbers()

    def show_next_page(self) -> None:
        """
        Show the next page of the table
        """
        self.editable_table.next_page()
        self.update_page_numbers()

    def show_last_page(self) -> None:
        """
        Show the last page of the table
        """
        self.editable_table.last_page()
        self.update_page_numbers()

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
    def toggle_controls_pane(self) -> None:
        """
        Toggle the visibility of the controls pane
        """
        # noinspection DuplicatedCode
        if self._control_frame.winfo_ismapped():
            self._control_frame.pack_forget()
            self._toolbar_frame.btn_toggle_controls.config(text='Show Control')
            self._toolbar_frame.btn_toggle_options.config(state=tk.NORMAL)

        else:
            self._control_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
            self._toolbar_frame.btn_toggle_controls.config(text='Hide Control')
            self._toolbar_frame.btn_toggle_options.config(state=tk.DISABLED)

    # noinspection DuplicatedCode
    def toggle_options_pane(self) -> None:
        """
        Toggle the visibility of the Options pane
        """
        # noinspection DuplicatedCode
        if self._options_frame.winfo_ismapped():
            self._options_frame.pack_forget()
            self._toolbar_frame.btn_toggle_options.config(text='Show Options')
            self._toolbar_frame.btn_toggle_controls.config(state=tk.NORMAL)
        else:
            self._options_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
            self._toolbar_frame.btn_toggle_options.config(text='Hide Options')
            self._toolbar_frame.btn_toggle_controls.config(state=tk.DISABLED)

    def update_page_numbers(self) -> None:
        """
        Update the page numbers in the toolbar
        """
        page_num = self.editable_table.current_page
        self._toolbar_frame.entry_page_num_var.set(page_num)
        self._toolbar_frame.lbl_page_count.config(text=f' / {self.editable_table.total_pages}')
        # enable all buttons by default
        self._change_navigation_state(tk.NORMAL)

        if not self.editable_table.pagination_enabled:
            self._toolbar_frame.entry_page_num.config(state=tk.NORMAL)
        if page_num <= 1:
            self._toolbar_frame.btn_first_page.config(state=tk.DISABLED)
            self._toolbar_frame.btn_prev_page.config(state=tk.DISABLED)
        elif page_num >= self.editable_table.total_pages:
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
            self.editable_table.reload_data()
            self.update_page_numbers()
            self.update_category_var()
            gui_f.box_message(f'Data Reloaded from {self.editable_table.data_source}')

    def rebuild_data(self) -> None:
        """
        Rebuild the data from the data source. Will ask for confirmation before rebuilding
        """
        if gui_f.box_yesno(f'The process will change the content of the windows.\nAre you sure you want to continue ?'):
            if self.editable_table.rebuild_data():
                self.update_page_numbers()
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
        # arguments for various commands
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
