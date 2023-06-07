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
from UEVaultManager.tkgui.modules.EditableTableClass import EditableTable
from UEVaultManager.tkgui.modules.functions_no_deps import set_custom_style
from UEVaultManager.tkgui.modules.TaggedLabelFrameClass import TaggedLabelFrame, WidgetType


class UEVMGui(tk.Tk):
    """
    This class is used to create the main window for the application.
    :param title: The title
    :param icon: The icon
    :param screen_index: The screen index
    :param file: The file where the data is stored or read from
    :param show_open_file_dialog: If True, the open file dialog will be shown at startup
    """

    def __init__(self, title: str, icon='', screen_index=0, file=None, show_open_file_dialog=False, rebuild_data=False,):
        super().__init__()

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
        self.editable_table = None
        self.do_not_launch_search = False
        pack_def_options = {'ipadx': 5, 'ipady': 5, 'padx': 3, 'pady': 3}

        table_frame = self.TableFrame(self)

        # gui_g.UEVM_gui_ref = self  # important ! Must be donne before any use of a ProgressWindow. If not, an UEVMGuiHiddenRootClass will be created and the ProgressWindow still be displayed after the init
        self.editable_table = EditableTable(container_frame=table_frame, file=file, rows_per_page=36, show_statusbar=True)
        self.editable_table.set_preferences(gui_g.s.datatable_default_pref)

        # done in the rebuild_data() method
        self.editable_table.show()
        self.editable_table.show_page(0)

        self.table_frame = table_frame
        toolbar_frame = self.ToolbarFrame(self)
        self.toolbar_frame = toolbar_frame
        control_frame = self.ControlFrame(self)
        self.control_frame = control_frame
        options_frame = self.OptionsFrame(self)
        self.options_frame = options_frame
        self.editable_table.set_colors()

        toolbar_frame.pack(**pack_def_options, fill=tk.X, side=tk.TOP, anchor=tk.NW)
        table_frame.pack(**pack_def_options, fill=tk.BOTH, side=tk.LEFT, anchor=tk.NW, expand=True)
        control_frame.pack(**pack_def_options, fill=tk.BOTH, side=tk.RIGHT, anchor=tk.NW)
        # not displayed at start
        # options_frame.pack(**pack_def_options, fill=tk.BOTH, side=tk.RIGHT, anchor=tk.NW)

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
            elif gui_f.box_yesno('So, do you want to load another file ? If not, the application will be closed'):
                show_open_file_dialog = True
            else:
                self.destroy()  # self.quit() won't work here
                gui_f.log_error('No valid file to read from. Application will be closed',)

        if show_open_file_dialog:
            if self.load_file() == '':
                gui_f.log_error('This application could not run without a file to read data from')
                self.quit()
        # Quick edit the first row
        self.editable_table.update_quick_edit(quick_edit_frame=self.control_frame.lbtf_quick_edit, row=0)
        if gui_g.s.data_filters:
            if self.load_filter(gui_g.s.data_filters):
                self.apply_filters(save=False)

    class ToolbarFrame(ttk.Frame):
        """
        This class is used to create the toolbar frame
        :param container: The parent container
        """

        def __init__(self, container):
            super().__init__()
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
            entry_page_num_var = tk.StringVar(value=container.editable_table.current_page + 1)
            entry_page_num = ttk.Entry(lblf_navigation, width=5, justify=tk.CENTER, textvariable=entry_page_num_var)
            entry_page_num.pack(**pack_def_options, side=tk.LEFT)
            lbl_page_count = ttk.Label(lblf_navigation, text=f' / {container.editable_table.total_pages}')
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
            btn_expand = ttk.Button(lblf_display, text='Expand Cols', command=container.editable_table.expand_columns)
            btn_expand.pack(**pack_def_options, side=tk.LEFT)
            btn_shrink = ttk.Button(lblf_display, text='Shrink Cols', command=container.editable_table.contract_columns)
            btn_shrink.pack(**pack_def_options, side=tk.LEFT)
            btn_autofit = ttk.Button(lblf_display, text='Autofit Cols', command=container.editable_table.autofit_columns)
            btn_autofit.pack(**pack_def_options, side=tk.LEFT)
            btn_zoom_in = ttk.Button(lblf_display, text='Zoom In', command=container.editable_table.zoom_in)
            btn_zoom_in.pack(**pack_def_options, side=tk.LEFT)
            btn_zoom_out = ttk.Button(lblf_display, text='Zoom Out', command=container.editable_table.zoom_out)
            btn_zoom_out.pack(**pack_def_options, side=tk.LEFT)

            lblf_commands = ttk.LabelFrame(self, text='Cli commands')
            lblf_commands.pack(side=tk.LEFT, **lblf_def_options)
            btn_help = ttk.Button(lblf_commands, text='Help', command=lambda: container.run_cli_command('print_help'))
            btn_help.pack(**pack_def_options, side=tk.LEFT)
            btn_status = ttk.Button(lblf_commands, text='Status', command=lambda: container.run_cli_command('status'))
            btn_status.pack(**pack_def_options, side=tk.LEFT)
            btn_info = ttk.Button(lblf_commands, text='Info', command=lambda: container.run_cli_command('info'))
            btn_info.pack(**pack_def_options, side=tk.LEFT)
            btn_list_files = ttk.Button(lblf_commands, text='List Files', command=lambda: container.run_cli_command('list_files'))
            btn_list_files.pack(**pack_def_options, side=tk.LEFT)
            btn_cleanup = ttk.Button(lblf_commands, text='Cleanup', command=lambda: container.run_cli_command('cleanup'))
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
            super().__init__(container)
            self.container = container

    class ControlFrame(ttk.Frame):
        """
        The ControlFrame is a container for the filter controls.
        :param container: The parent container.
        """

        def __init__(self, container):
            super().__init__()

            # grid_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'sticky': tk.NW}
            pack_def_options = {'ipadx': 2, 'ipady': 2, 'fill': tk.BOTH, 'expand': False}
            grid_fw_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'sticky': tk.EW}  # full width
            lblf_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.X, 'expand': False}
            lblf_fw_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.X, 'expand': True}  # full width

            cat_vars = container.update_category_var()
            grab_results = cat_vars['grab_results']
            categories = cat_vars['categories']
            lblf_content = ttk.LabelFrame(self, text='Content')
            lblf_content.pack(**lblf_def_options)
            btn_edit_row = ttk.Button(lblf_content, text='Edit Row', command=container.editable_table.create_edit_record_window)
            btn_edit_row.grid(row=0, column=0, **grid_fw_options)
            btn_reload_data = ttk.Button(lblf_content, text='Reload File Content', command=container.reload_data)
            btn_reload_data.grid(row=0, column=1, **grid_fw_options)
            btn_rebuild_file = ttk.Button(lblf_content, text='Rebuild File Content', command=container.rebuild_data)
            btn_rebuild_file.grid(row=0, column=2, **grid_fw_options)
            lblf_content.columnconfigure('all', weight=1)  # important to make the buttons expand

            lbf_filter_cat = ttk.LabelFrame(self, text='Search and Filter')
            # row 0
            cur_col = 0
            cur_row = 0
            lbf_filter_cat.pack(fill=tk.X, anchor=tk.NW, ipadx=5, ipady=5)
            var_is_owned = tk.BooleanVar(value=False)
            var_is_owned.trace_add('write', container.on_check_change)
            ck_owned = ttk.Checkbutton(lbf_filter_cat, text='Owned', variable=var_is_owned)
            ck_owned.grid(row=cur_row, column=cur_col, **grid_fw_options)
            cur_col += 1
            var_must_buy = tk.BooleanVar(value=False)
            var_must_buy.trace_add('write', container.on_check_change)
            ck_must_buy = ttk.Checkbutton(lbf_filter_cat, text='Must buy', variable=var_must_buy)
            ck_must_buy.grid(row=cur_row, column=cur_col, **grid_fw_options)
            cur_col += 1
            var_discounted = tk.BooleanVar(value=False)
            var_discounted.trace_add('write', container.on_check_change)
            ck_discounted = ttk.Checkbutton(lbf_filter_cat, text='Discounted', variable=var_discounted)
            ck_discounted.grid(row=cur_row, column=cur_col, **grid_fw_options)
            cur_col += 1
            var_is_not_obsolete = tk.BooleanVar(value=False)
            var_is_not_obsolete.trace_add('write', container.on_check_change)
            ck_obsolete = ttk.Checkbutton(lbf_filter_cat, text='Not obsolete', variable=var_is_not_obsolete)
            ck_obsolete.grid(row=cur_row, column=cur_col, **grid_fw_options)
            # row 1
            cur_row += 1
            cur_col = 0
            lbl_category = ttk.Label(lbf_filter_cat, text='Category')
            lbl_category.grid(row=cur_row, column=cur_col, **grid_fw_options)
            cur_col += 1
            var_category = tk.StringVar(value=categories[0])
            opt_category = ttk.Combobox(lbf_filter_cat, textvariable=var_category, values=categories)
            opt_category.grid(row=cur_row, column=cur_col, columnspan=3, **grid_fw_options)
            # row 2
            cur_row += 1
            cur_col = 0
            lbl_grab_results = ttk.Label(lbf_filter_cat, text='Grab result')
            lbl_grab_results.grid(row=cur_row, column=cur_col, **grid_fw_options)
            cur_col += 1
            var_grab_results = tk.StringVar(value=grab_results[0])
            opt_grab_results = ttk.Combobox(lbf_filter_cat, textvariable=var_grab_results, values=grab_results)
            opt_grab_results.grid(row=cur_row, column=cur_col, columnspan=3, **grid_fw_options)
            # row 3
            cur_row += 1
            cur_col = 0
            var_global_search = tk.StringVar(value=gui_g.s.default_global_search)
            entry_search = ttk.Entry(lbf_filter_cat, textvariable=var_global_search)
            entry_search.grid(row=cur_row, column=cur_col, columnspan=2, **grid_fw_options)
            entry_search.bind('<FocusIn>', self.del_entry_search)
            # entry_search.bind('<FocusOut>', container.search)
            cur_col += 2
            btn_filter_by_text = ttk.Button(lbf_filter_cat, text='Apply All', command=container.apply_filters)
            btn_filter_by_text.grid(row=cur_row, column=cur_col, **grid_fw_options)
            cur_col += 1
            btn_reset_search = ttk.Button(lbf_filter_cat, text='Reset All', command=container.reset_filters)
            btn_reset_search.grid(row=cur_row, column=cur_col, **grid_fw_options)
            lbf_filter_cat.columnconfigure('all', weight=1)  # important to make the buttons expand

            lblf_files = ttk.LabelFrame(self, text='Files')
            lblf_files.pack(**lblf_def_options)
            lbl_file_name = ttk.Label(lblf_files, text='Current File: ')
            lbl_file_name.grid(row=0, column=0, columnspan=3, **grid_fw_options)
            var_entry_file_name = tk.StringVar(value=container.editable_table.file)
            entry_file_name = ttk.Entry(lblf_files, textvariable=var_entry_file_name, state='readonly')
            entry_file_name.grid(row=1, column=0, columnspan=3, **grid_fw_options)
            btn_save_file = ttk.Button(lblf_files, text='Save to File', command=container.save_file)
            btn_save_file.grid(row=2, column=0, **grid_fw_options)
            btn_export_button = ttk.Button(lblf_files, text='Export Selection', command=container.export_selection)
            btn_export_button.grid(row=2, column=1, **grid_fw_options)
            btn_load_file = ttk.Button(lblf_files, text='Load a file', command=container.load_file)
            btn_load_file.grid(row=2, column=2, **grid_fw_options)
            lblf_files.columnconfigure('all', weight=1)  # important to make the buttons expand

            # note : the TAG of the child widgets of the lbf_quick_edit will also be used in the editable_table.quick_edit method
            # to get the widgets it needs. So they can't be changed freely
            lbtf_quick_edit = TaggedLabelFrame(self, text='Quick Edit User fields')
            lbtf_quick_edit.pack(**lblf_fw_options, anchor=tk.NW)
            lbl_desc = ttk.Label(lbtf_quick_edit, text='Changing this values will change the values of \nthe selected row when losing focus')
            lbl_desc.pack(**pack_def_options)
            lbtf_quick_edit.add_child(widget_type=WidgetType.ENTRY, tag='Url', focus_out_callback=container.on_quick_edit_focus_out)
            lbtf_quick_edit.add_child(
                widget_type=WidgetType.TEXT, tag='Comment', focus_out_callback=container.on_quick_edit_focus_out, width=10, height=4
            )
            lbtf_quick_edit.add_child(widget_type=WidgetType.ENTRY, tag='Stars', focus_out_callback=container.on_quick_edit_focus_out)
            lbtf_quick_edit.add_child(widget_type=WidgetType.ENTRY, tag='Test result', focus_out_callback=container.on_quick_edit_focus_out)
            lbtf_quick_edit.add_child(
                widget_type=WidgetType.CHECKBUTTON,
                tag='Must buy',
                label='',
                images_folder=gui_g.s.assets_folder,
                click_on_callback=container.on_switch_edit_flag,
                default_content=False
            )
            lbtf_quick_edit.add_child(widget_type=WidgetType.ENTRY, tag='Installed folder', default_content='Installed in')
            lbtf_quick_edit.add_child(widget_type=WidgetType.ENTRY, tag='Origin', focus_out_callback=container.on_quick_edit_focus_out)
            lbtf_quick_edit.add_child(widget_type=WidgetType.ENTRY, tag='Alternative', focus_out_callback=container.on_quick_edit_focus_out)

            lbt_image_preview = ttk.LabelFrame(self, text='Image Preview')
            lbt_image_preview.pack(**lblf_fw_options, anchor=tk.SW)
            canvas_image = tk.Canvas(lbt_image_preview, width=gui_g.s.preview_max_width, height=gui_g.s.preview_max_height, highlightthickness=0)
            canvas_image.pack(side=tk.BOTTOM, expand=True, anchor=tk.CENTER)
            canvas_image.create_rectangle((0, 0), (gui_g.s.preview_max_width, gui_g.s.preview_max_height), fill='black')

            lblf_bottom = ttk.Frame(self)
            lblf_bottom.pack(**lblf_def_options)
            ttk.Sizegrip(lblf_bottom).pack(side=tk.RIGHT)

            # store the controls that need to be accessible outside the class
            self.var_entry_file_name = var_entry_file_name
            self.var_category = var_category
            self.var_global_search = var_global_search
            self.var_is_owned = var_is_owned
            self.var_is_not_obsolete = var_is_not_obsolete
            self.var_must_buy = var_must_buy
            self.var_discounted = var_discounted
            self.var_grab_results = var_grab_results

            self.entry_search = entry_search
            self.lbtf_quick_edit = lbtf_quick_edit
            self.canvas_image = canvas_image

        def reset_entry_search(self, _event=None) -> None:
            """
            Reset the search entry to the default text.
            :param _event:
            """
            self.entry_search.delete(0, 'end')
            self.entry_search.insert(0, gui_g.s.default_global_search)

        def del_entry_search(self, _event=None) -> None:
            """
            Delete the text in the search entry.
            :param _event:
            """
            self.entry_search.delete(0, 'end')

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
            # if the file is empty or absent or invalid when creating the class, the control_frame is not defined
            category = self.control_frame.var_category.get().replace('/', '_')
        except AttributeError:
            category = None
        if category and category != gui_g.s.default_category_for_all:
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
        self.toolbar_frame.btn_first_page.config(state=state)
        self.toolbar_frame.btn_prev_page.config(state=state)
        self.toolbar_frame.btn_next_page.config(state=state)
        self.toolbar_frame.btn_last_page.config(state=state)
        self.toolbar_frame.entry_page_num.config(state=state)

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
        canvas_image = self.control_frame.canvas_image
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
        canvas_image = self.control_frame.canvas_image
        gui_f.show_default_image(canvas_image=canvas_image)

    def on_selection_change(self, event=None) -> None:
        """
        When the selection changes, show the selected row in the quick edit frame
        :param event:
        """
        selected_row = event.widget.currentrow
        self.editable_table.update_quick_edit(quick_edit_frame=self.control_frame.lbtf_quick_edit, row=selected_row)

    def on_entry_page_num_changed(self, _event=None) -> None:
        """
        When the page number changes, show the corresponding page
        :param _event:
        """
        page_num = 0
        try:
            page_num = self.toolbar_frame.entry_page_num.get()
            page_num = int(page_num)
            page_num -= 1
            gui_f.log_debug(f'showing page {page_num}')
            self.editable_table.show_page(page_num)
        except (ValueError, UnboundLocalError) as error:
            gui_f.log_error(f'could not convert page number {page_num} to int. {error!r}')

    # noinspection PyUnusedLocal
    def on_quick_edit_focus_out(self, event=None, tag='') -> None:
        """
        When the focus leaves a quick edit widget, save the value
        :param event:
        :param tag: tag of the widget that triggered the event
        """
        if tag == '':
            return
        widget = self.control_frame.lbtf_quick_edit.get_child_by_tag(tag)
        if widget is None:
            gui_f.log_warning(f'Could not find a widget with tag {tag}')
            return
        col = widget.col
        row = widget.row
        if col is None or row is None or col < 0 or row < 0:
            gui_f.log_debug(f'invalid values for row={row} and col={col}')
            return
        value = widget.get_content()
        self.editable_table.quick_edit_save_value(col=col, row=row, value=value)

    # noinspection PyUnusedLocal
    def on_switch_edit_flag(self, event=None, tag='') -> None:
        """
        When the focus leaves a quick edit widget, save the value
        :param event: event that triggered the call
        :param tag: tag of the widget that triggered the event
        """
        if tag == '':
            return
        widget = self.control_frame.lbtf_quick_edit.get_child_by_tag(tag)
        if widget is None or widget.widget_type != WidgetType.CHECKBUTTON:
            gui_f.log_warning(f'Could not find a CHECKBUTTON widget with tag {tag}')
            return
        col = widget.col
        row = widget.row
        if col is None or row is None or col < 0 or row < 0:
            gui_f.log_debug(f'invalid values for row={row} and col={col}')
            return

        value = widget.switch_state(event=event)
        self.editable_table.quick_edit_save_value(col=col, row=row, value=value)

    # noinspection PyUnusedLocal
    def on_check_change(self, *args) -> None:
        """
        When a checkbutton is changed, launch a search
        :param args:
        """
        if not self.do_not_launch_search:
            self.apply_filters()

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
            gui_g.s.last_opened_file = self.editable_table.file
        # store window geometry in config settings
        gui_g.s.width = self.winfo_width()
        gui_g.s.height = self.winfo_height()
        gui_g.s.x_pos = self.winfo_x()
        gui_g.s.y_pos = self.winfo_y()
        gui_g.s.save_config_file()
        self.quit()

    def load_file(self) -> str:
        """
        Load a file
        :return: the name of the file that was loaded
        """
        filename = self._open_file_dialog(filename=self.editable_table.file)
        if filename and os.path.isfile(filename):
            self.editable_table.file = filename
            self.editable_table.load_data()
            self.editable_table.show_page(0)
            self.update_page_numbers()
            self.update_file_name()
            gui_f.box_message(f'The file {filename} as been read')
        return filename

    def save_file(self, show_dialog=True) -> str:
        """
        Save the data to a file
        :param show_dialog: if True, show a dialog to select the file to save to, if False, use the current file
        """
        if show_dialog:
            filename = self._open_file_dialog(filename=self.editable_table.file, save_mode=True)
            if filename:
                self.editable_table.file = filename
        else:
            filename = self.editable_table.file

        if filename:
            self.editable_table.save_data()
            self.update_file_name()
            gui_f.box_message(f'Data Saved to {self.editable_table.file}')
        return filename

    def export_selection(self) -> None:
        """
        Export the selected rows to a file
        """
        # Get selected row indices
        selected_row_indices = self.editable_table.multiplerowlist
        if selected_row_indices:
            selected_rows = self.editable_table.data_filtered.iloc[selected_row_indices]
            filename = self._open_file_dialog(save_mode=True, filename=self.editable_table.file)
            if filename:
                selected_rows.to_csv(filename, index=False)
                gui_f.box_message(f'Selected rows exported to "{filename}"')
        else:
            gui_f.box_message('Select at least one row first')

    def load_filter(self, filters: dict) -> bool:
        """
        Load the filters from a dictionary
        :param filters: filters
        :return: True if the filters were loaded, False otherwise
        """
        try:
            self.do_not_launch_search = True
            frm = self.control_frame

            category = filters.get('Category', gui_g.s.default_category_for_all)
            search_text = filters.get('Category', gui_g.s.default_global_search)
            obsolete = filters.get('Obsolete', True)
            # note: the "status" filter has no control associated, it's managed by the "obsolete" checkbutton
            frm.var_grab_results.set(filters.get('Grab result', gui_g.s.default_category_for_all))
            frm.var_is_owned.set(filters.get('Owned', False))
            frm.var_is_not_obsolete.set(not obsolete)
            frm.var_must_buy.set(filters.get('Must buy', False))
            frm.var_discounted.set(filters.get('Discounted', False))
            frm.var_category.set(category)
            gui_g.UEVM_filter_category = category
            frm.var_global_search.set(search_text)
            self.do_not_launch_search = False
            return True
        except Exception as error:
            gui_f.log_error(f'Error loading filters: {error!r}')
            return False

    def apply_filters(self, _event=None, save=True) -> None:
        """
        Search for a string in the table
        :param _event: Event
        :param save: if True, save the filters in the config file
        """
        frm = self.control_frame
        search_text = frm.var_global_search.get()
        category = frm.var_category.get()
        grab_results = frm.var_grab_results.get()
        owned = frm.var_is_owned.get()
        not_obsolete = frm.var_is_not_obsolete.get()
        must_buy = frm.var_must_buy.get()
        discounted = frm.var_discounted.get()
        gui_g.UEVM_filter_category = category if category != gui_g.s.default_category_for_all else ''
        self.toggle_pagination(forced_value=False)
        filter_dict = {}
        if category != gui_g.s.default_category_for_all and category != '':
            filter_dict['Category'] = category
        else:
            filter_dict.pop('Category', None)
        if grab_results != gui_g.s.default_category_for_all and grab_results != '':
            filter_dict['Grab result'] = grab_results
        else:
            filter_dict.pop('Grab result', None)
        if owned:
            filter_dict['Owned'] = True
        else:
            filter_dict.pop('Owned', None)
        if not_obsolete:
            filter_dict['Obsolete'] = False
            filter_dict['Status'] = 'active'
        else:
            filter_dict.pop('Obsolete', None)
            filter_dict.pop('Status', None)
        if must_buy:
            filter_dict['Must buy'] = True
        else:
            filter_dict.pop('Must buy', None)
        if discounted:
            filter_dict['Discounted'] = True
        else:
            filter_dict.pop('Discounted', None)
        self.editable_table.apply_filters(filter_dict, global_search=search_text)
        if save:
            gui_g.s.set_data_filters(filter_dict)
            gui_g.s.save_config_file(save_config_var=True)
        # self.control_frame.reset_entry_search()

    def reset_filters(self) -> None:
        """
        Reset the search controls to their default values
        """
        self.control_frame.var_global_search.set(gui_g.s.default_global_search)
        self.control_frame.var_category.set(gui_g.s.default_category_for_all)
        gui_g.UEVM_filter_category = ''
        self.do_not_launch_search = True  # Prevent the search to be launched when the checkbuttons are changed
        self.control_frame.var_is_owned.set(False)
        self.control_frame.var_is_not_obsolete.set(False)
        self.do_not_launch_search = False
        self.editable_table.reset_filters()

    def toggle_pagination(self, forced_value=None) -> None:
        """
        Toggle pagination. Will change the navigation buttons states when pagination is changed
        :param forced_value: if not None, will force the pagination to the given value
        """
        if forced_value is not None:
            self.editable_table.pagination_enabled = forced_value
        else:
            self.editable_table.pagination_enabled = not self.editable_table.pagination_enabled
        self.editable_table.show_page()
        if not self.editable_table.pagination_enabled:
            # Disable prev/next buttons when pagination is disabled
            self._change_navigation_state(tk.DISABLED)
            self.toolbar_frame.btn_toggle_pagination.config(text='Enable  Pagination')
        else:
            self.update_page_numbers()  # will also update buttons status
            self.toolbar_frame.btn_toggle_pagination.config(text='Disable Pagination')

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
        if self.control_frame.winfo_ismapped():
            self.control_frame.pack_forget()
            self.toolbar_frame.btn_toggle_controls.config(text='Show Control')
            self.toolbar_frame.btn_toggle_options.config(state=tk.NORMAL)

        else:
            self.control_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
            self.toolbar_frame.btn_toggle_controls.config(text='Hide Control')
            self.toolbar_frame.btn_toggle_options.config(state=tk.DISABLED)

    # noinspection DuplicatedCode
    def toggle_options_pane(self) -> None:
        """
        Toggle the visibility of the Options pane
        """
        # noinspection DuplicatedCode
        if self.options_frame.winfo_ismapped():
            self.options_frame.pack_forget()
            self.toolbar_frame.btn_toggle_options.config(text='Show Options')
            self.toolbar_frame.btn_toggle_controls.config(state=tk.NORMAL)
        else:
            self.options_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
            self.toolbar_frame.btn_toggle_options.config(text='Hide Options')
            self.toolbar_frame.btn_toggle_controls.config(state=tk.DISABLED)

    def update_page_numbers(self) -> None:
        """
        Update the page numbers in the toolbar
        """
        page_num = self.editable_table.current_page + 1
        self.toolbar_frame.entry_page_num_var.set(page_num)
        self.toolbar_frame.lbl_page_count.config(text=f' / {self.editable_table.total_pages}')
        # enable all buttons by default
        self._change_navigation_state(tk.NORMAL)

        if not self.editable_table.pagination_enabled:
            self.toolbar_frame.entry_page_num.config(state=tk.NORMAL)
        if page_num == 1:
            self.toolbar_frame.btn_first_page.config(state=tk.DISABLED)
            self.toolbar_frame.btn_prev_page.config(state=tk.DISABLED)
        elif page_num == self.editable_table.total_pages:
            self.toolbar_frame.btn_next_page.config(state=tk.DISABLED)
            self.toolbar_frame.btn_last_page.config(state=tk.DISABLED)

    def update_file_name(self) -> None:
        """
        Update the file name in the control frame
        """
        filename = self.editable_table.file
        self.control_frame.var_entry_file_name.set(filename)

    def update_category_var(self) -> dict:
        """
        Update the category variable with the current categories in the data
        :return: a dict with the new categories list as value and the key is the name of the variable.
        """
        try:
            # if the file is empty or absent or invalid when creating the class, the data is empty, so no categories
            categories = list(self.editable_table.data['Category'].cat.categories)
        except (AttributeError, TypeError, KeyError):
            categories = []
        categories.insert(0, gui_g.s.default_category_for_all)
        try:
            # if the file is empty or absent or invalid when creating the class, the data is empty, so no categories
            grab_results = list(self.editable_table.data['Grab result'].cat.categories)
        except (AttributeError, TypeError, KeyError):
            grab_results = []
        grab_results.insert(0, gui_g.s.default_category_for_all)
        return {'categories': categories, 'grab_results': grab_results}

    def reload_data(self) -> None:
        """
        Reload the data from the file
        """
        if not self.editable_table.must_save or (
            self.editable_table.must_save and gui_f.box_yesno('Changes have been made, they will be lost. Are you sure you want to continue ?')
        ):
            self.editable_table.reload_data()
            gui_f.box_message(f'Data Reloaded from {self.editable_table.file}')
            self.update_page_numbers()
            self.update_category_var()

    def rebuild_data(self) -> None:
        """
        Rebuild the data from the file. Will ask for confirmation before rebuilding
        """
        if gui_f.box_yesno(
            f'The process will change the content of the windows and the {self.editable_table.file} file.\nAre you sure you want to continue ?'
        ):
            if self.editable_table.rebuild_data():
                gui_f.box_message(f'Data rebuilt from {self.editable_table.file}')
                self.update_page_numbers()
                self.update_category_var()

    def run_cli_command(self, command_name='') -> None:
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
        col = self.editable_table.model.df.columns.get_loc('App name')
        app_name = self.editable_table.model.getValueAt(row, col)
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
