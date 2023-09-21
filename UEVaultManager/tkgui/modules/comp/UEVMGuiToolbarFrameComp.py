# coding=utf-8
"""
Implementation for:
- UEVMGuiToolbarFrame: a toolbar frame for the UEVMGui Class.
"""
import tkinter as tk

import ttkbootstrap as ttk
from ttkbootstrap.constants import WARNING

import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.cls.EditableTableClass import EditableTable
from UEVaultManager.tkgui.modules.functions_no_deps import append_no_duplicate


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
        self.btn_toggle_pagination = ttk.Button(lblf_navigation, text='Disable Pagination', command=container.toggle_pagination)
        self.btn_toggle_pagination.pack(**pack_def_options, side=tk.LEFT)
        btn_first_item = ttk.Button(lblf_navigation, text='First Page', command=container.first_item)
        btn_first_item.pack(**pack_def_options, side=tk.LEFT)
        btn_first_item.config(state=tk.DISABLED)
        btn_prev_page = ttk.Button(lblf_navigation, text='Prev Page', command=container.prev_page)
        btn_prev_page.pack(**pack_def_options, side=tk.LEFT)
        btn_prev_page.config(state=tk.DISABLED)
        self.var_entry_current_item = tk.StringVar(value='{:04d}'.format(data_table.current_page))
        self.entry_current_item = ttk.Entry(lblf_navigation, width=5, justify=tk.CENTER, textvariable=self.var_entry_current_item)
        self.entry_current_item.pack(**pack_def_options_np, side=tk.LEFT)
        self.lbl_page_count = ttk.Label(lblf_navigation, text=f' / {data_table.total_pages:04d}')
        self.lbl_page_count.pack(**pack_def_options_np, side=tk.LEFT)
        btn_next_page = ttk.Button(lblf_navigation, text='Next Page', command=container.next_page)
        btn_next_page.pack(**pack_def_options, side=tk.LEFT)
        btn_last_item = ttk.Button(lblf_navigation, text='Last Page', command=container.last_item)
        btn_last_item.pack(**pack_def_options, side=tk.LEFT)
        btn_prev_asset = ttk.Button(lblf_navigation, text='Prev Asset', command=container.prev_asset)
        btn_prev_asset.pack(**pack_def_options, side=tk.LEFT)
        btn_next_asset = ttk.Button(lblf_navigation, text='Next Asset', command=container.next_asset)
        btn_next_asset.pack(**pack_def_options, side=tk.LEFT)
        self.btn_first_item = btn_first_item  # need for text change
        self.btn_last_item = btn_last_item  # need for text change

        lblf_display = ttk.LabelFrame(self, text='Display')
        lblf_display.pack(side=tk.LEFT, **lblf_def_options)
        ttk_item = ttk.Button(lblf_display, text='Expand Cols', command=data_table.expand_columns)
        ttk_item.pack(**pack_def_options, side=tk.LEFT)
        ttk_item = ttk.Button(lblf_display, text='Shrink Cols', command=data_table.contract_columns)
        ttk_item.pack(**pack_def_options, side=tk.LEFT)
        ttk_item = ttk.Button(lblf_display, text='Autofit Cols', command=data_table.autofit_columns)
        ttk_item.pack(**pack_def_options, side=tk.LEFT)
        ttk_item = ttk.Button(lblf_display, text='Zoom In', command=data_table.zoom_in)
        ttk_item.pack(**pack_def_options, side=tk.LEFT)
        ttk_item = ttk.Button(lblf_display, text='Zoom Out', command=data_table.zoom_out)
        ttk_item.pack(**pack_def_options, side=tk.LEFT)

        lblf_commands = ttk.LabelFrame(self, text='Other commands')
        lblf_commands.pack(side=tk.LEFT, **lblf_def_options)
        btn_login = ttk.Button(lblf_commands, text='Login', command=lambda: container.run_uevm_command('auth'))
        btn_login.pack(**pack_def_options, side=tk.LEFT)
        ttk_item = ttk.Button(lblf_commands, text='Help', command=lambda: container.run_uevm_command('print_help'))
        ttk_item.pack(**pack_def_options, side=tk.LEFT)
        ttk_item = ttk.Button(lblf_commands, text='Status', command=lambda: container.run_uevm_command('status'))
        ttk_item.pack(**pack_def_options, side=tk.LEFT)
        ttk_item = ttk.Button(lblf_commands, text='Cleanup', command=lambda: container.run_uevm_command('cleanup'))
        ttk_item.pack(**pack_def_options, side=tk.LEFT)
        ttk_item = ttk.Button(lblf_commands, text='Get Json Data', command=lambda: container.json_processing())
        ttk_item.pack(**pack_def_options, side=tk.LEFT)
        ttk_item = ttk.Button(lblf_commands, text='Db Import/Export', command=lambda: container.database_processing())
        ttk_item.pack(**pack_def_options, side=tk.LEFT)

        lblf_actions = ttk.LabelFrame(self, text='Actions')
        lblf_actions.pack(side=tk.RIGHT, **lblf_def_options)
        self.btn_toggle_options = ttk.Button(lblf_actions, text='Show Options', command=container.toggle_options_panel, state=tk.DISABLED)
        self.btn_toggle_options.pack(**pack_def_options, side=tk.LEFT)
        self.btn_toggle_controls = ttk.Button(lblf_actions, text='Hide Actions', command=container.toggle_actions_panel)
        self.btn_toggle_controls.pack(**pack_def_options, side=tk.LEFT)
        # noinspection PyArgumentList
        # (bootstyle is not recognized by PyCharm)
        ttk_item = ttk.Button(lblf_actions, text='Quit', command=container.on_close, bootstyle=WARNING)
        ttk_item.pack(**pack_def_options, side=tk.RIGHT)

        # Bind events for the Entry widget
        self.entry_current_item.bind('<FocusOut>', container.on_entry_current_item_changed)
        self.entry_current_item.bind('<Return>', container.on_entry_current_item_changed)

        widget_list = gui_g.stated_widgets.get('not_first_item', [])
        append_no_duplicate(widget_list, [btn_first_item])
        widget_list = gui_g.stated_widgets.get('not_last_item', [])
        append_no_duplicate(widget_list, [btn_last_item])
        widget_list = gui_g.stated_widgets.get('not_first_page', [])
        append_no_duplicate(widget_list, [btn_prev_page])
        widget_list = gui_g.stated_widgets.get('not_last_page', [])
        append_no_duplicate(widget_list, [btn_next_page])
        widget_list = gui_g.stated_widgets.get('not_first_asset', [])
        append_no_duplicate(widget_list, [btn_prev_asset])
        widget_list = gui_g.stated_widgets.get('not_last_asset', [])
        append_no_duplicate(widget_list, [btn_next_asset])
        widget_list = gui_g.stated_widgets.get('not_offline', [])
        append_no_duplicate(widget_list, [btn_login])
