# coding=utf-8
"""
Implementation for:
- UEVMGuiOptionFrame: an options/settings frame for the UEVMGui Class.
"""
import tkinter as tk
from tkinter import filedialog

import ttkbootstrap as ttk

import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience


class UEVMGuiOptionFrame(ttk.Frame):
    """
    an options/settings frame for the UEVMGui Class.
    :param _container: The parent container.
    """
    _folders_to_scan = []
    _container = None
    _cb_folders_to_scan = None

    def __init__(self, _container):
        super().__init__()
        self._container = _container
        self._folders_to_scan = gui_g.s.folders_to_scan if gui_g.s.folders_to_scan else []

        # pack_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.BOTH, 'expand': False}
        lblf_def_options = {'ipadx': 1, 'ipady': 1, 'padx': 1, 'pady': 1, 'fill': tk.X}
        grid_fw_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'sticky': tk.EW}  # full width

        # global options frame (shown/hidden
        lblf_options = ttk.Frame(self)
        lblf_options.pack(side=tk.TOP, **{'ipadx': 1, 'ipady': 1, 'fill': tk.BOTH, 'expand': True})

        # Options for Commands frame
        lblf_command_options = ttk.LabelFrame(lblf_options, text='Options for Commands')
        lblf_command_options.pack(side=tk.TOP, **lblf_def_options)
        # lblf_command_options row
        cur_col = 0
        cur_row = 0
        var_force_refresh = tk.BooleanVar(value=gui_g.UEVM_cli_args.get('force', False))
        var_force_refresh.trace_add('write', lambda name, index, mode: gui_g.set_args_force_refresh(var_force_refresh.get()))
        ck_force_refresh = ttk.Checkbutton(lblf_command_options, text='Force refresh', variable=var_force_refresh)
        ck_force_refresh.grid(row=cur_row, column=cur_col, **grid_fw_options)
        # lblf_command_options row
        cur_row += 1
        cur_col = 0
        var_offline = tk.BooleanVar(value=gui_g.UEVM_cli_args.get('offline', False))
        var_offline.trace_add('write', lambda name, index, mode: gui_g.set_args_offline(var_offline.get()))
        ck_offline = ttk.Checkbutton(lblf_command_options, text='Offline Mode', variable=var_offline)
        ck_offline.grid(row=cur_row, column=cur_col, **grid_fw_options)
        # lblf_command_options row
        cur_row += 1
        cur_col = 0
        var_debug = tk.BooleanVar(value=gui_g.UEVM_cli_args.get('debug', False))
        var_debug.trace_add('write', lambda name, index, mode: gui_g.set_args_debug(var_debug.get()))
        ck_debug = ttk.Checkbutton(lblf_command_options, text='Debug mode (CLI)', variable=var_debug)
        ck_debug.grid(row=cur_row, column=cur_col, **grid_fw_options)
        # lblf_command_options row
        cur_row += 1
        cur_col = 0
        var_auth_delete = tk.BooleanVar(value=gui_g.UEVM_cli_args.get('auth_delete', False))
        var_auth_delete.trace_add('write', lambda name, index, mode: gui_g.set_args_auth_delete(var_auth_delete.get()))
        ck_auth_delete = ttk.Checkbutton(lblf_command_options, text='Delete auth (login)', variable=var_auth_delete)
        ck_auth_delete.grid(row=cur_row, column=cur_col, **grid_fw_options)
        # lblf_command_options row
        cur_row += 1
        cur_col = 0
        var_delete_metadata = tk.BooleanVar(value=gui_g.UEVM_cli_args.get('delete_metadata', False))
        var_delete_metadata.trace_add('write', lambda name, index, mode: gui_g.set_args_delete_metadata(var_delete_metadata.get()))
        ck_delete_metadata = ttk.Checkbutton(lblf_command_options, text='Delete metadata (cleanup)', variable=var_delete_metadata)
        ck_delete_metadata.grid(row=cur_row, column=cur_col, **grid_fw_options)
        # lblf_command_options row
        cur_row += 1
        cur_col = 0
        var_delete_extra_data = tk.BooleanVar(value=gui_g.UEVM_cli_args.get('delete_extra_data', False))
        var_delete_extra_data.trace_add('write', lambda name, index, mode: gui_g.set_args_delete_extra_data(var_delete_extra_data.get()))
        ck_delete_extra_data = ttk.Checkbutton(lblf_command_options, text='Delete extra data (cleanup)', variable=var_delete_extra_data)
        ck_delete_extra_data.grid(row=cur_row, column=cur_col, **grid_fw_options)
        # lblf_command_options row
        cur_row += 1
        cur_col = 0
        var_delete_scraping_data = tk.BooleanVar(value=gui_g.UEVM_cli_args.get('delete_scraping_data', False))
        var_delete_scraping_data.trace_add('write', lambda name, index, mode: gui_g.set_args_delete_scraping_data(var_delete_scraping_data.get()))
        ck_delete_scraping_data = ttk.Checkbutton(lblf_command_options, text='Delete scraping data (cleanup)', variable=var_delete_scraping_data)
        ck_delete_scraping_data.grid(row=cur_row, column=cur_col, **grid_fw_options)
        # Settings for GUI frame
        lblf_gui_settings = ttk.LabelFrame(lblf_options, text='Settings for GUI')
        lblf_gui_settings.pack(side=tk.TOP, **lblf_def_options)
        # lblf_gui_settings row
        cur_row = 0
        cur_col = 0
        var_use_threads = tk.BooleanVar(value=gui_g.s.use_threads)
        var_use_threads.trace_add('write', lambda name, index, mode: gui_g.set_use_threads(var_use_threads.get()))
        ck_use_threads = ttk.Checkbutton(lblf_gui_settings, text='Use threads', variable=var_use_threads)
        ck_use_threads.grid(row=cur_row, column=cur_col, **grid_fw_options)
        # lblf_gui_settings row
        cur_row += 1
        cur_col = 0
        self.var_debug_gui = tk.BooleanVar(value=gui_g.s.debug_mode)
        self.var_debug_gui.trace_add('write', lambda name, index, mode: self.update_gui_options())
        ck_debug_gui = ttk.Checkbutton(lblf_gui_settings, text='Debug mode (GUI)', variable=self.var_debug_gui)
        ck_debug_gui.grid(row=cur_row, column=cur_col, **grid_fw_options)
        # lblf_gui_settings row
        cur_row += 1
        cur_col = 0
        lbl_testing_switch = ttk.Label(lblf_gui_settings, text='Testing switch:')
        lbl_testing_switch.grid(row=cur_row, column=cur_col, **grid_fw_options)
        cur_col += 1
        self.var_testing_switch = tk.IntVar(value=gui_g.s.testing_switch)
        self.var_testing_switch.trace_add('write', lambda name, index, mode: self.update_gui_options())
        entry_testing_switch = ttk.Entry(lblf_gui_settings, textvariable=self.var_testing_switch, width=2)
        entry_testing_switch.grid(row=cur_row, column=cur_col, **grid_fw_options)
        # Folders To scan frame
        lblf_folders_to_scan = ttk.LabelFrame(lblf_options, text='Folders To scan (add/remove)')
        lblf_folders_to_scan.pack(side=tk.TOP, **lblf_def_options)
        # lblf_folders_to_scan row
        cur_row = 0
        cur_col = 0
        # lbl_folders_to_scan = ttk.Label(lblf_folders_to_scan, text='Folders:')
        # lbl_folders_to_scan.grid(row=cur_row, column=cur_col, **grid_fw_options)
        # cur_col += 1
        cb_folders_to_scan = ttk.Combobox(lblf_folders_to_scan, values=self._folders_to_scan, state='readonly', width=35)
        cb_folders_to_scan.grid(row=cur_row, column=cur_col, columnspan=2, **grid_fw_options)
        self._cb_folders_to_scan = cb_folders_to_scan
        # lblf_folders_to_scan row
        cur_row += 1
        cur_col = 0
        btn_add_folder = ttk.Button(lblf_folders_to_scan, text='Add Folder', command=self.add_folder_to_scan)
        btn_add_folder.grid(row=cur_row, column=cur_col, **grid_fw_options)
        cur_col += 1
        btn_remove_folder = ttk.Button(lblf_folders_to_scan, text='Remove Folder', command=self.remove_folder_to_scan)
        btn_remove_folder.grid(row=cur_row, column=cur_col, **grid_fw_options)
        # lblf_folders_to_scan row
        cur_row += 1
        cur_col = 0
        var_check_asset_folders = tk.BooleanVar(value=gui_g.s.check_asset_folders)
        var_check_asset_folders.trace_add('write', lambda name, index, mode: gui_g.set_check_asset_folders(var_check_asset_folders.get()))
        ck_check_asset_folders = ttk.Checkbutton(lblf_folders_to_scan, text='Check Asset Folders', variable=var_check_asset_folders)
        ck_check_asset_folders.grid(row=cur_row, column=cur_col, **grid_fw_options)

    def update_gui_options(self):
        """
        Update the GUI options.
        """
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
            gui_g.s.set_debug_mode(value)

        try:
            self._container.update_controls_and_redraw()  # will update the title of the window
        except AttributeError:
            # the container is not a UEVMGui instance,
            pass

    def add_folder_to_scan(self):
        """
        Add a folder to scan.
        """
        cb_selection = self._cb_folders_to_scan.get()
        # open a file dialog to select a folder
        folder_selected = filedialog.askdirectory(title='Select a folder to scan for UE assets', initialdir=cb_selection)
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
