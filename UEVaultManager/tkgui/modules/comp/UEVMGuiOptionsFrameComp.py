# coding=utf-8
"""
Implementation for:
- UEVMGuiOptionsFrame: an options/settings frame for the UEVMGui Class
"""
import tkinter as tk

import ttkbootstrap as ttk

import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience


class UEVMGuiOptionsFrame(ttk.Frame):
    """
    an options/settings frame for the UEVMGui Class
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
