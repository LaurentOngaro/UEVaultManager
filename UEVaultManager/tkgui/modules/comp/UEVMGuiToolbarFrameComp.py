# coding=utf-8
"""
Implementation for:
- UEVMGuiToolbarFrame: a toolbar frame for the UEVMGui Class.
"""
import tkinter as tk

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from UEVaultManager.tkgui.modules.cls.EditableTableClass import EditableTable


class UEVMGuiToolbarFrame(ttk.Frame):
    """
    A toolbar frame for the UEVMGui Class.
    :param container: The parent container.
    :param data_table: The EditableTable instance.
    """

    def __init__(self, container, data_table: EditableTable):
        super().__init__()
        if container is None:
            raise ValueError('container must be None')
        if data_table is None:
            raise ValueError('data_table must be a UEVMGuiContentFrame instance')

        self.data_table: EditableTable = data_table

        pack_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.BOTH, 'expand': False}
        pack_def_options_np = {'ipadx': 0, 'ipady': 0, 'padx': 0, 'pady': 0, 'fill': tk.BOTH, 'expand': False}
        lblf_def_options = {'ipadx': 1, 'ipady': 1, 'expand': False}

        lblf_navigation = ttk.LabelFrame(self, text='Navigation')
        lblf_navigation.pack(side=tk.LEFT, **lblf_def_options)
        # (bootstyle is not recognized by PyCharm)
        # noinspection PyArgumentList
        btn_toggle_pagination = ttk.Button(lblf_navigation, text='Disable Pagination', command=container.toggle_pagination)
        # noinspection PyArgumentList
        btn_toggle_pagination.pack(**pack_def_options, side=tk.LEFT)
        btn_first_item = ttk.Button(lblf_navigation, text='First Page', command=container.first_item)
        btn_first_item.pack(**pack_def_options, side=tk.LEFT)
        btn_first_item.config(state=tk.DISABLED)
        btn_prev_page = ttk.Button(lblf_navigation, text='Prev Page', command=container.prev_page)
        btn_prev_page.pack(**pack_def_options, side=tk.LEFT)
        btn_prev_page.config(state=tk.DISABLED)
        entry_current_item_var = tk.StringVar(value='{:04d}'.format(data_table.current_page))
        entry_current_item = ttk.Entry(lblf_navigation, width=5, justify=tk.CENTER, textvariable=entry_current_item_var)
        entry_current_item.pack(**pack_def_options_np, side=tk.LEFT)
        lbl_page_count = ttk.Label(lblf_navigation, text=f' / {data_table.total_pages:04d}')
        lbl_page_count.pack(**pack_def_options_np, side=tk.LEFT)
        btn_next_page = ttk.Button(lblf_navigation, text='Next Page', command=container.next_page)
        btn_next_page.pack(**pack_def_options, side=tk.LEFT)
        btn_last_item = ttk.Button(lblf_navigation, text='Last Page', command=container.last_item)
        btn_last_item.pack(**pack_def_options, side=tk.LEFT)
        btn_prev_asset = ttk.Button(lblf_navigation, text='Prev Asset', command=container.prev_asset)
        btn_prev_asset.pack(**pack_def_options, side=tk.LEFT)
        btn_next_asset = ttk.Button(lblf_navigation, text='Next Asset', command=container.next_asset)
        btn_next_asset.pack(**pack_def_options, side=tk.RIGHT)

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

        lblf_commands = ttk.LabelFrame(self, text='Other commands')
        lblf_commands.pack(side=tk.LEFT, **lblf_def_options)
        btn_login = ttk.Button(lblf_commands, text='Login', command=lambda: container.run_uevm_command('auth'))
        btn_login.pack(**pack_def_options, side=tk.LEFT)
        btn_help = ttk.Button(lblf_commands, text='Help', command=lambda: container.run_uevm_command('print_help'))
        btn_help.pack(**pack_def_options, side=tk.LEFT)
        btn_status = ttk.Button(lblf_commands, text='Status', command=lambda: container.run_uevm_command('status'))
        btn_status.pack(**pack_def_options, side=tk.LEFT)
        """
        # following commands are messy and not really useful
        btn_info = ttk.Button(lblf_commands, text='Info', command=lambda: container.run_uevm_command('info'))
        btn_info.pack(**pack_def_options, side=tk.LEFT)
        btn_list_files = ttk.Button(lblf_commands, text='List Files', command=lambda: container.run_uevm_command('list_files'))
        btn_list_files.pack(**pack_def_options, side=tk.LEFT)
        """
        btn_cleanup = ttk.Button(lblf_commands, text='Cleanup', command=lambda: container.run_uevm_command('cleanup'))
        btn_cleanup.pack(**pack_def_options, side=tk.LEFT)
        btn_json_processing = ttk.Button(lblf_commands, text='Get Json Data', command=lambda: container.json_processing())
        btn_json_processing.pack(**pack_def_options, side=tk.LEFT)
        btn_database_processing = ttk.Button(lblf_commands, text='Db Import/Export', command=lambda: container.database_processing())
        btn_database_processing.pack(**pack_def_options, side=tk.LEFT)

        lblf_actions = ttk.LabelFrame(self, text='Actions')
        lblf_actions.pack(side=tk.RIGHT, **lblf_def_options)
        # noinspection PyArgumentList
        btn_toggle_options = ttk.Button(lblf_actions, text='Show Options', command=container.toggle_options_panel, state=tk.DISABLED)
        btn_toggle_options.pack(**pack_def_options, side=tk.LEFT)
        # noinspection PyArgumentList
        btn_toggle_controls = ttk.Button(lblf_actions, text='Hide Actions', command=container.toggle_actions_panel)
        btn_toggle_controls.pack(**pack_def_options, side=tk.LEFT)
        # noinspection PyArgumentList
        btn_on_close = ttk.Button(lblf_actions, text='Quit', command=container.on_close, bootstyle=WARNING)
        btn_on_close.pack(**pack_def_options, side=tk.RIGHT)

        # Bind events for the Entry widget
        entry_current_item.bind('<FocusOut>', container.on_entry_current_item_changed)
        entry_current_item.bind('<Return>', container.on_entry_current_item_changed)

        self.btn_toggle_pagination = btn_toggle_pagination
        self.btn_prev_asset = btn_prev_asset
        self.btn_next_asset = btn_next_asset
        self.btn_first_item = btn_first_item
        self.btn_prev_page = btn_prev_page
        self.btn_next_page = btn_next_page
        self.btn_last_item = btn_last_item
        self.btn_login = btn_login
        self.btn_toggle_options = btn_toggle_options
        self.btn_toggle_controls = btn_toggle_controls
        self.lbl_page_count = lbl_page_count
        self.entry_current_item = entry_current_item
        self.entry_current_item_var = entry_current_item_var
