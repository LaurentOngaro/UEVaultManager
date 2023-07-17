# coding=utf-8
"""
Implementation for:
- UEVMGuiOptionsFrame: an options/settings frame for the UEVMGui Class.
"""
import tkinter as tk
from tkinter import filedialog

import ttkbootstrap as ttk

import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience


class UEVMGuiOptionsFrame(ttk.Frame):
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

        # Command Options frame
        lblf_command_options = ttk.LabelFrame(lblf_options, text='Command Options')
        lblf_command_options.pack(side=tk.TOP, **lblf_def_options)
        # lblf_options row
        cur_col = 0
        cur_row = 0
        force_refresh_var = tk.BooleanVar(value=gui_g.UEVM_cli_args.get('force', False))
        force_refresh_var.trace_add('write', lambda name, index, mode: gui_g.set_args_force_refresh(force_refresh_var.get()))
        ck_force_refresh = ttk.Checkbutton(lblf_command_options, text='Force refresh', variable=force_refresh_var)
        ck_force_refresh.grid(row=cur_row, column=cur_col, **grid_fw_options)
        # lblf_options row
        cur_row += 1
        cur_col = 0
        offline_var = tk.BooleanVar(value=gui_g.UEVM_cli_args.get('offline', False))
        offline_var.trace_add('write', lambda name, index, mode: gui_g.set_args_offline(offline_var.get()))
        ck_offline = ttk.Checkbutton(lblf_command_options, text='Offline Mode', variable=offline_var)
        ck_offline.grid(row=cur_row, column=cur_col, **grid_fw_options)
        # lblf_options row
        cur_row += 1
        cur_col = 0
        debug_var = tk.BooleanVar(value=gui_g.UEVM_cli_args.get('debug', False))
        debug_var.trace_add('write', lambda name, index, mode: gui_g.set_args_debug(debug_var.get()))
        ck_debug = ttk.Checkbutton(lblf_command_options, text='Debug mode', variable=debug_var)
        ck_debug.grid(row=cur_row, column=cur_col, **grid_fw_options)
        # lblf_options row
        # delete_extra_data'] = True
        cur_row += 1
        cur_col = 0
        delete_metadata_var = tk.BooleanVar(value=gui_g.UEVM_cli_args.get('delete_metadata', False))
        delete_metadata_var.trace_add('write', lambda name, index, mode: gui_g.set_args_delete_metadata(delete_metadata_var.get()))
        ck_delete_metadata = ttk.Checkbutton(lblf_command_options, text='Delete metadata (cleanup)', variable=delete_metadata_var)
        ck_delete_metadata.grid(row=cur_row, column=cur_col, **grid_fw_options)
        # lblf_options row
        cur_row += 1
        cur_col = 0
        delete_extra_data_var = tk.BooleanVar(value=gui_g.UEVM_cli_args.get('delete_extra_data', False))
        delete_extra_data_var.trace_add('write', lambda name, index, mode: gui_g.set_args_delete_extra_data(delete_extra_data_var.get()))
        ck_delete_extra_data = ttk.Checkbutton(lblf_command_options, text='Delete metadata (cleanup)', variable=delete_extra_data_var)
        ck_delete_extra_data.grid(row=cur_row, column=cur_col, **grid_fw_options)

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
        cb_folders_to_scan.grid(row=cur_row, column=cur_col, columnspan=2 , **grid_fw_options)
        self._cb_folders_to_scan = cb_folders_to_scan
        # lblf_folders_to_scan row
        cur_row += 1
        cur_col = 0
        btn_add_folder = ttk.Button(lblf_folders_to_scan, text='Add Folder', command=self.add_folder_to_scan)
        btn_add_folder.grid(row=cur_row, column=cur_col, **grid_fw_options)
        cur_col += 1
        btn_remove_folder = ttk.Button(lblf_folders_to_scan, text='Remove Folder', command=self.remove_folder_to_scan)
        btn_remove_folder.grid(row=cur_row, column=cur_col, **grid_fw_options)

    def add_folder_to_scan(self):
        """
        Add a folder to scan.
        """
        # open a file dialog to select a folder
        folder_selected = filedialog.askdirectory(title='Select a folder to scan for UE assets', initialdir='.')
        # add the folder to the list
        if folder_selected and folder_selected not in self._folders_to_scan:
            values = list(self._cb_folders_to_scan['values'])
            values.append(folder_selected)
            self._cb_folders_to_scan['values'] = values
            self._folders_to_scan = values
            self.save_folder_to_scan()

    def remove_folder_to_scan(self):
        """
        Remove a folder to scan.
        """
        cb_selection = self._cb_folders_to_scan.get()
        if cb_selection:
            values = list(self._cb_folders_to_scan['values'])
            values.remove(cb_selection)
            self._cb_folders_to_scan['values'] = values
            self._folders_to_scan = values
            self.save_folder_to_scan()

    def save_folder_to_scan(self):
        """
        Save the folder to scan.
        """
        gui_g.s.folders_to_scan = self._folders_to_scan
        gui_g.s.save_config_file()
