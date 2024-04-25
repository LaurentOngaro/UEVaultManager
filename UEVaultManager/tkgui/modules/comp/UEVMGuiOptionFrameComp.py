# coding=utf-8
"""
Implementation for:
- UEVMGuiOptionFrame: options/settings frame for the UEVMGui Class.
"""
import os
import tkinter as tk
from tkinter import filedialog

import ttkbootstrap as ttk

import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.cls.OptionWidgetClass import OptionWidget
from UEVaultManager.tkgui.modules.functions_no_deps import open_folder_in_file_explorer


class UEVMGuiOptionFrame(ttk.Frame):
    """
    an options/settings frame for the UEVMGui Class.
    :param _container: parent container.
    """

    def __init__(self, _container):
        super().__init__()
        self._container = _container
        self._folders_to_scan = gui_g.s.folders_to_scan if gui_g.s.folders_to_scan else []
        self._widgets = {}

        # pack_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.BOTH, 'expand': False}
        lblf_def_options = {'ipadx': 1, 'ipady': 1, 'padx': 1, 'pady': 1, 'fill': tk.X}
        grid_ew_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'sticky': tk.EW}  # full width

        # global options frame (shown/hidden)
        lblf_options = ttk.Frame(self)
        lblf_options.pack(side=tk.TOP, **{'ipadx': 1, 'ipady': 1, 'fill': tk.BOTH, 'expand': True})

        # Quick Files Access
        lblf_quick_files = ttk.LabelFrame(lblf_options, text='Quick Files Access')
        lblf_quick_files.pack(side=tk.TOP, **lblf_def_options)
        max_col = 2
        cur_row = -1
        # new row
        cur_row += 1
        cur_col = 0
        self.quick_files_list = {
            'CLI Config File': gui_g.s.config_file,
            'GUI Config File': gui_g.s.config_file_gui,
            'Last Opened File': gui_g.s.config_vars['last_opened_file'],
        }
        try:
            # get any folder name from the log files in the core object
            core = gui_g.UEVM_cli_ref.core
            self.quick_files_list['scan assets log'] = core.scan_assets_filename_log
            self.quick_files_list['scrap assets log'] = core.scrap_assets_filename_log
            self.quick_files_list['ignored assets log'] = core.ignored_assets_filename_log
            self.quick_files_list['not found assets log'] = core.notfound_assets_filename_log
            uevmlfs = core.uevmlfs
            self.quick_files_list['installed assets file'] = uevmlfs.installed_asset_filename
            self.quick_files_list['asset sizes file'] = uevmlfs.asset_sizes_filename
        except (Exception, ):
            pass

        cb_quick_files = ttk.Combobox(lblf_quick_files, values=list(self.quick_files_list.keys()), state='readonly', width=35)
        cb_quick_files.grid(row=cur_row, column=cur_col, columnspan=max_col, **grid_ew_options)
        self._cb_quick_files = cb_quick_files
        # new row
        cur_row += 1
        cur_col = 0
        ttk_item = ttk.Button(lblf_quick_files, text='Open File', command=self.quick_file_open)
        ttk_item.grid(row=cur_row, column=cur_col, columnspan=2, **grid_ew_options)

        # Quick Folders Access
        lblf_quick_folders = ttk.LabelFrame(lblf_options, text='Quick Folders Access')
        lblf_quick_folders.pack(side=tk.TOP, **lblf_def_options)
        max_col = 2
        cur_row = -1
        # new row
        cur_row += 1
        cur_col = 0
        self.quick_folders_list = {
            'Config Folder': gui_g.s.path,
            'Last Opened Folder': gui_g.s.last_opened_folder,
            'Last Opened Project': gui_g.s.last_opened_project,
            'Last Opened Engine': gui_g.s.last_opened_engine,
            'Filters Folder': gui_g.s.filters_folder,
            'Backup Folder': gui_g.s.backups_folder,
            'Scraping Folder': gui_g.s.scraping_folder,
            'Results Files Folder': gui_g.s.results_folder,
            'Assets Images Folder': gui_g.s.asset_images_folder,
            'Assets Json Files Folder': gui_g.s.assets_data_folder,
            'Assets CSV Files Folder': gui_g.s.assets_csv_files_folder,
        }
        try:
            # get any folder name from the log files in the core object
            core = gui_g.UEVM_cli_ref.core
            any_core_log_file = core.scrap_assets_filename_log or core.scan_assets_filename_log or core.ignored_assets_filename_log or core.notfound_assets_filename_log
            log_folder = os.path.dirname(any_core_log_file)
            log_folder = os.path.normpath(log_folder)
            if os.path.isdir(log_folder):
                self.quick_folders_list['Log Folder'] = log_folder
        except (Exception, ):
            pass
        cb_quick_folders = ttk.Combobox(lblf_quick_folders, values=list(self.quick_folders_list.keys()), state='readonly', width=35)
        cb_quick_folders.grid(row=cur_row, column=cur_col, columnspan=max_col, **grid_ew_options)
        self._cb_quick_folders = cb_quick_folders
        # new row
        cur_row += 1
        cur_col = 0
        ttk_item = ttk.Button(lblf_quick_folders, text='Browse Folder', command=self.quick_folders_browse)
        ttk_item.grid(row=cur_row, column=cur_col, columnspan=2, **grid_ew_options)

        # Options for Commands frame
        lblf_command_options = ttk.LabelFrame(lblf_options, text='Options for CLI Commands')
        lblf_command_options.pack(side=tk.TOP, **lblf_def_options)
        cur_row = -1
        # new row
        cur_row += 1
        cur_col = 0
        self.add_widget('debug', 'bool', 'Debug mode (All)', lblf_command_options, cur_row, cur_col, grid_ew_options, is_cli=True)
        # new row
        cur_row += 1
        cur_col = 0
        self.add_widget('force_refresh', 'bool', 'Force refresh (All)', lblf_command_options, cur_row, cur_col, grid_ew_options, is_cli=True)
        # new row
        cur_row += 1
        cur_col = 0
        self.add_widget('offline', 'bool', 'Offline Mode (All)', lblf_command_options, cur_row, cur_col, grid_ew_options, is_cli=True)
        # new row
        cur_row += 1
        cur_col = 0
        self.add_widget('auth_delete', 'bool', 'Delete auth (auth/login)', lblf_command_options, cur_row, cur_col, grid_ew_options, is_cli=True)
        # new row
        cur_row += 1
        cur_col = 0
        self.add_widget(
            'delete_scraping_data', 'bool', 'Delete scraping data (cleanup)', lblf_command_options, cur_row, cur_col, grid_ew_options, is_cli=True
        )

        # Settings for GUI frame
        lblf_gui_settings = ttk.LabelFrame(lblf_options, text='Settings for GUI')
        lblf_gui_settings.pack(side=tk.TOP, **lblf_def_options)
        cur_row = -1
        # new row
        cur_row += 1
        cur_col = 0
        self.add_widget('testing_switch', 'int', 'Testing switch value', lblf_gui_settings, cur_row, cur_col, grid_ew_options)
        # new row
        cur_row += 1
        cur_col = 0
        self.add_widget('timeout_for_scraping', 'int', 'Timeout for scraping', lblf_gui_settings, cur_row, cur_col, grid_ew_options)
        # new row
        cur_row += 1
        cur_col = 0
        self.add_widget('use_threads', 'bool', 'Use threads', lblf_gui_settings, cur_row, cur_col, grid_ew_options, colspan=max_col)
        # new row
        cur_row += 1
        cur_col = 0
        self.add_widget('debug_mode', 'bool', 'Debug mode (GUI)', lblf_gui_settings, cur_row, cur_col, grid_ew_options, colspan=max_col)
        # new row
        cur_row += 1
        cur_col = 0
        self.add_widget('offline_mode', 'bool', 'Offline mode (GUI and CLI)', lblf_gui_settings, cur_row, cur_col, grid_ew_options, colspan=max_col)
        # new row
        cur_row += 1
        cur_col = 0
        self.add_widget(
            'use_colors_for_data', 'bool', 'Use colors in data table', lblf_gui_settings, cur_row, cur_col, grid_ew_options, colspan=max_col
        )
        # new row
        cur_row += 1
        cur_col = 0
        self.add_widget(
            'check_asset_folders', 'bool', 'Check Asset Folders when needed', lblf_gui_settings, cur_row, cur_col, grid_ew_options, colspan=max_col
        )
        # new row
        cur_row += 1
        cur_col = 0
        self.add_widget(
            'browse_when_add_row', 'bool', 'Browse folder when adding new row', lblf_gui_settings, cur_row, cur_col, grid_ew_options, colspan=max_col
        )

        # Folders To scan frame
        lblf_folders_to_scan = ttk.LabelFrame(lblf_options, text='Folders to scan (add/remove)')
        lblf_folders_to_scan.pack(side=tk.TOP, **lblf_def_options)
        max_col = 2
        cur_row = -1
        # new row
        cur_row += 1
        cur_col = 0
        cb_folders_to_scan = ttk.Combobox(lblf_folders_to_scan, values=self._folders_to_scan, state='readonly', width=35)
        cb_folders_to_scan.grid(row=cur_row, column=cur_col, columnspan=max_col, **grid_ew_options)
        self._cb_folders_to_scan = cb_folders_to_scan
        # new row
        cur_row += 1
        cur_col = 0
        ttk_item = ttk.Button(lblf_folders_to_scan, text='Add Folder', command=self.add_folder_to_scan)
        ttk_item.grid(row=cur_row, column=cur_col, **grid_ew_options)
        cur_col += 1
        ttk_item = ttk.Button(lblf_folders_to_scan, text='Remove Folder', command=self.remove_folder_to_scan)
        ttk_item.grid(row=cur_row, column=cur_col, **grid_ew_options)
        # new row
        cur_row += 1
        cur_col = 0
        self.add_widget(
            'keep_invalid_scans',
            'bool',
            'Keep non marketplace assets after a scan',
            lblf_folders_to_scan,
            cur_row,
            cur_col,
            grid_ew_options,
            is_cli=False
        )

    def add_widget(
        self,
        name: str,
        vtype: str,
        label: str,
        container,
        cur_row: int,
        cur_col: int,
        grid_options: dict,
        is_cli: bool = False,
        colspan: int = 2,
        callback: callable = None,
    ) -> OptionWidget:
        """
        Add a widget.
        :param name: name of the setting.
        :param vtype: type of the setting.
        :param label: label of the widget.
        :param container: parent container.
        :param cur_row: current row.
        :param cur_col: current column.
        :param grid_options: grid options.
        :param is_cli: is the setting for the CLI.
        :param colspan: column span.
        :param callback: callback function to call when the widget value changes.
        :return: an OptionWidget object.
        """
        callback = self.update_on_changes if not callback else callback
        widget = OptionWidget(name, vtype, label, container, cur_row, cur_col, grid_options, is_cli, colspan, callback)
        widget.setup()
        self._widgets[name] = widget
        return widget

    def refresh_widgets(self):
        """
        Refresh the widgets values by reading the associated settings.
        """
        for widget in self._widgets.values():
            setting = widget.get_setting()
            if setting is None:
                continue
            # temporarily remove the trace to avoid a loop
            widget.trace_off()
            try:
                widget.set_value(setting)
            except (Exception, ) as error:
                print(f'Error when setting the value of the widget "{widget.name}" to "{setting}": {error}')
            # restore the trace
            widget.trace_on()

    def add_folder_to_scan(self):
        """
        Add a folder to scan.
        """
        cb_selection = self._cb_folders_to_scan.get()
        initial_dir = cb_selection if cb_selection else gui_g.s.last_opened_folder
        # open a file dialog to select a folder
        folder_selected = filedialog.askdirectory(title='Select a folder to scan for UE assets', initialdir=initial_dir)
        folder_selected = os.path.normpath(folder_selected) if folder_selected else ''
        gui_g.s.last_opened_folder = folder_selected

        # add the folder to the list
        if folder_selected and folder_selected not in self._folders_to_scan:
            values = list(self._cb_folders_to_scan['values'])
            values.append(folder_selected)
            # remove a folder if its parent is already in the list
            folders = sorted(values)  # shorter paths are first, as it, parent folders are before their children
            last_folder_lower = ''
            for folder in folders:
                if last_folder_lower and folder.lower().startswith(last_folder_lower):
                    values.remove(folder)
                last_folder_lower = folder.lower()
            self._cb_folders_to_scan['values'] = values
            self._cb_folders_to_scan.current(len(values) - 1)  # select the last item
            self._folders_to_scan = values
            self.save_folder_to_scan()

    def remove_folder_to_scan(self):
        """
        Remove a folder to scan.
        """
        cb_selection = self._cb_folders_to_scan.get()
        if cb_selection:
            values = list(self._cb_folders_to_scan['values'])
            try:
                values.remove(cb_selection)
            except ValueError:
                pass
            else:
                self._cb_folders_to_scan['values'] = values
                self._cb_folders_to_scan.current(len(values) - 1)  # select the last item
                self._folders_to_scan = values
                self.save_folder_to_scan()

    def save_folder_to_scan(self):
        """
        Save the folder to scan.
        """
        gui_g.s.folders_to_scan = self._folders_to_scan
        gui_g.s.save_config_file()

    def quick_folders_browse(self):
        """
        Browse a quick folder.
        """
        cb_selection = self._cb_quick_folders.get()
        if cb_selection:
            folder = self.quick_folders_list.get(cb_selection, '')
            open_folder_in_file_explorer(folder)

    def quick_file_open(self):
        """
        Open a file.
        """
        cb_selection = self._cb_quick_files.get()
        if cb_selection:
            file_name = self.quick_files_list.get(cb_selection, '')
            if os.path.isfile(file_name):
                os.system(f'start {file_name}')

    def update_on_changes(self) -> None:
        """
        Called when a widget value changes (Callback).
        """
        self._container.update_controls_state(update_title=True)  # will update the title of the window
