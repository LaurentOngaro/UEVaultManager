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
from UEVaultManager.tkgui.modules.functions import update_loggers_level


class UEVMGuiOptionFrame(ttk.Frame):
    """
    an options/settings frame for the UEVMGui Class.
    :param _container: parent container.
    """

    def __init__(self, _container):
        super().__init__()
        self._container = _container
        self._folders_to_scan = gui_g.s.folders_to_scan if gui_g.s.folders_to_scan else []

        # pack_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.BOTH, 'expand': False}
        lblf_def_options = {'ipadx': 1, 'ipady': 1, 'padx': 1, 'pady': 1, 'fill': tk.X}
        grid_ew_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'sticky': tk.EW}  # full width
        grid_e_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'sticky': tk.E}

        # global options frame (shown/hidden)
        lblf_options = ttk.Frame(self)
        lblf_options.pack(side=tk.TOP, **{'ipadx': 1, 'ipady': 1, 'fill': tk.BOTH, 'expand': True})

        # Options for Commands frame
        lblf_command_options = ttk.LabelFrame(lblf_options, text='Options for CLI Commands')
        lblf_command_options.pack(side=tk.TOP, **lblf_def_options)
        cur_row = -1
        # new row
        cur_row += 1
        cur_col = 0
        var_debug = tk.BooleanVar(value=gui_g.UEVM_cli_args.get('debug', False))
        var_debug.trace_add('write', lambda name, index, mode: gui_g.set_args_debug(var_debug.get()))
        ck_debug = ttk.Checkbutton(lblf_command_options, text='Debug mode (All)', variable=var_debug)
        ck_debug.grid(row=cur_row, column=cur_col, **grid_ew_options)
        # new row
        cur_row += 1
        cur_col = 0
        var_force_refresh = tk.BooleanVar(value=gui_g.UEVM_cli_args.get('force', False))
        var_force_refresh.trace_add('write', lambda name, index, mode: gui_g.set_args_force_refresh(var_force_refresh.get()))
        ck_force_refresh = ttk.Checkbutton(lblf_command_options, text='Force refresh (All)', variable=var_force_refresh)
        ck_force_refresh.grid(row=cur_row, column=cur_col, **grid_ew_options)
        # new row
        cur_row += 1
        cur_col = 0
        var_offline = tk.BooleanVar(value=gui_g.UEVM_cli_args.get('offline', False))
        var_offline.trace_add('write', lambda name, index, mode: gui_g.set_args_offline(var_offline.get()))
        ck_offline = ttk.Checkbutton(lblf_command_options, text='Offline Mode (All)', variable=var_offline)
        ck_offline.grid(row=cur_row, column=cur_col, **grid_ew_options)
        # new row
        cur_row += 1
        cur_col = 0
        var_auth_delete = tk.BooleanVar(value=gui_g.UEVM_cli_args.get('auth_delete', False))
        var_auth_delete.trace_add('write', lambda name, index, mode: gui_g.set_args_auth_delete(var_auth_delete.get()))
        ck_auth_delete = ttk.Checkbutton(lblf_command_options, text='Delete auth (auth/login)', variable=var_auth_delete)
        ck_auth_delete.grid(row=cur_row, column=cur_col, **grid_ew_options)
        # new row
        cur_row += 1
        cur_col = 0
        var_delete_scraping_data = tk.BooleanVar(value=gui_g.UEVM_cli_args.get('delete_scraping_data', False))
        var_delete_scraping_data.trace_add('write', lambda name, index, mode: gui_g.set_args_delete_scraping_data(var_delete_scraping_data.get()))
        ck_delete_scraping_data = ttk.Checkbutton(lblf_command_options, text='Delete scraping data (cleanup)', variable=var_delete_scraping_data)
        ck_delete_scraping_data.grid(row=cur_row, column=cur_col, **grid_ew_options)

        # Settings for GUI frame
        lblf_gui_settings = ttk.LabelFrame(lblf_options, text='Settings for GUI')
        lblf_gui_settings.pack(side=tk.TOP, **lblf_def_options)
        max_col = 2
        cur_row = -1
        # new row
        cur_row += 1
        cur_col = 0
        ttk_item = ttk.Label(lblf_gui_settings, text='Testing switch value')
        ttk_item.grid(row=cur_row, column=cur_col, **grid_e_options)
        cur_col += 1
        self.var_testing_switch = tk.IntVar(value=gui_g.s.testing_switch)
        self.var_testing_switch.trace_add('write', lambda name, index, mode: self.update_gui_options())
        entry_testing_switch = ttk.Entry(lblf_gui_settings, textvariable=self.var_testing_switch, width=2)
        entry_testing_switch.grid(row=cur_row, column=cur_col, **grid_ew_options)
        # new row
        cur_row += 1
        cur_col = 0
        ttk_item = ttk.Label(lblf_gui_settings, text='Timeout for scraping')
        ttk_item.grid(row=cur_row, column=cur_col, **grid_e_options)
        cur_col += 1
        self.var_timeout_for_scraping = tk.IntVar(value=gui_g.s.timeout_for_scraping)
        self.var_timeout_for_scraping.trace_add('write', lambda name, index, mode: self.update_gui_options())
        entry_timeout_for_scraping = ttk.Entry(lblf_gui_settings, textvariable=self.var_timeout_for_scraping, width=2)
        entry_timeout_for_scraping.grid(row=cur_row, column=cur_col, **grid_ew_options)
        # new row
        cur_row += 1
        cur_col = 0
        var_use_threads = tk.BooleanVar(value=gui_g.s.use_threads)
        var_use_threads.trace_add('write', lambda name, index, mode: gui_g.set_use_threads(var_use_threads.get()))
        ck_use_threads = ttk.Checkbutton(lblf_gui_settings, text='Use threads', variable=var_use_threads)
        ck_use_threads.grid(row=cur_row, column=cur_col, columnspan=max_col, **grid_ew_options)
        # new row
        cur_row += 1
        cur_col = 0
        self.var_debug_gui = tk.BooleanVar(value=gui_g.s.debug_mode)
        self.var_debug_gui.trace_add('write', lambda name, index, mode: self.update_gui_options())
        ck_debug_gui = ttk.Checkbutton(lblf_gui_settings, text='Debug mode (GUI)', variable=self.var_debug_gui)
        ck_debug_gui.grid(row=cur_row, column=cur_col, columnspan=max_col, **grid_ew_options)
        # new row
        cur_row += 1
        cur_col = 0
        self.var_offline_mode = tk.BooleanVar(value=gui_g.s.offline_mode)
        self.var_offline_mode.trace_add('write', lambda name, index, mode: self.update_gui_options())
        ck_offline_mode = ttk.Checkbutton(lblf_gui_settings, text='Offline mode (GUI and CLI)', variable=self.var_offline_mode)
        ck_offline_mode.grid(row=cur_row, column=cur_col, columnspan=max_col, **grid_ew_options)
        # new row
        cur_row += 1
        cur_col = 0
        var_use_colors_for_data = tk.BooleanVar(value=gui_g.s.use_colors_for_data)
        var_use_colors_for_data.trace_add('write', lambda name, index, mode: gui_g.set_use_colors_for_data(var_use_colors_for_data.get()))
        ck_use_colors_for_data = ttk.Checkbutton(lblf_gui_settings, text='Use colors in data table', variable=var_use_colors_for_data)
        ck_use_colors_for_data.grid(row=cur_row, column=cur_col, columnspan=max_col, **grid_ew_options)
        # new row
        cur_row += 1
        cur_col = 0
        var_check_asset_folders = tk.BooleanVar(value=gui_g.s.check_asset_folders)
        var_check_asset_folders.trace_add('write', lambda name, index, mode: gui_g.set_check_asset_folders(var_check_asset_folders.get()))
        ck_check_asset_folders = ttk.Checkbutton(lblf_gui_settings, text='Check Asset Folders when needed', variable=var_check_asset_folders)
        ck_check_asset_folders.grid(row=cur_row, column=cur_col, columnspan=max_col, **grid_ew_options)
        # new row
        cur_row += 1
        cur_col = 0
        var_browse_when_add_row = tk.BooleanVar(value=gui_g.s.browse_when_add_row)
        var_browse_when_add_row.trace_add('write', lambda name, index, mode: gui_g.set_browse_when_add_row(var_browse_when_add_row.get()))
        ck_browse_when_add_row = ttk.Checkbutton(lblf_gui_settings, text='Browse folder when adding new row', variable=var_browse_when_add_row)
        ck_browse_when_add_row.grid(row=cur_row, column=cur_col, columnspan=max_col, **grid_ew_options)

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

    def update_gui_options(self):
        """
        Update the GUI options.
        """
        try:
            value = self.var_timeout_for_scraping.get()
            value = int(value)  # tkinter will raise an error is the value can be converted to an int
        except (ValueError, tk.TclError):
            pass
        else:
            gui_g.s.timeout_for_scraping = value

        try:
            value = self.var_testing_switch.get()
            value = int(value)  # tkinter will raise an error is the value can be converted to an int
        except (ValueError, tk.TclError):
            pass
        else:
            gui_g.s.testing_switch = value

        try:
            value = self.var_debug_gui.get()
            value = bool(value)
        except (ValueError, tk.TclError):
            pass
        else:
            gui_g.s.debug_mode = value
            update_loggers_level(debug_value=value)

        try:
            value = self.var_offline_mode.get()
            value = bool(value)
        except (ValueError, tk.TclError):
            pass
        else:
            gui_g.s.offline_mode = value
            gui_g.UEVM_cli_args['offline'] = value

        try:
            self._container.update_controls_state(update_title=True)  # will update the title of the window
        except AttributeError as error:
            # the container is not a UEVMGui instance
            self._container.logger.debug(f'An error occured in update_gui_options: {error!r}')
            pass

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
                if last_folder_lower != '' and folder.lower().startswith(last_folder_lower):
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
