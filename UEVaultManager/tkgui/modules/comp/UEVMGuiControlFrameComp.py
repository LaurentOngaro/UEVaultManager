# coding=utf-8
"""
Implementation for:
- UEVMGuiControlFrame: a control frame for the UEVMGui Class.
"""
import tkinter as tk

import ttkbootstrap as ttk
from ttkbootstrap.constants import WARNING

import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.cls.EditableTableClass import EditableTable
from UEVaultManager.tkgui.modules.comp.FilterFrameComp import FilterFrame
from UEVaultManager.tkgui.modules.comp.TaggedLabelFrameComp import TaggedLabelFrame
from UEVaultManager.tkgui.modules.functions_no_deps import append_no_duplicate
from UEVaultManager.tkgui.modules.types import WidgetType


class UEVMGuiControlFrame(ttk.Frame):
    """
    A control frame for the UEVMGui Class.
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

        pack_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.BOTH, 'expand': True}
        grid_def_options_np = {'ipadx': 0, 'ipady': 0, 'padx': 0, 'pady': 0}  # no padding
        # pack_def_options = {'ipadx': 2, 'ipady': 2, 'fill': tk.BOTH, 'expand': False}
        grid_ew_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'sticky': tk.EW}  # full width
        lblf_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.X, 'expand': False}
        lblf_fw_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.X, 'expand': True}  # full width
        # content frame
        lblf_content = ttk.LabelFrame(self, text='Data Table and content')
        lblf_content.pack(**lblf_def_options)
        max_col = 5
        cur_row = -1
        # new row
        cur_row += 1
        cur_col = 0
        lbl_data_source = ttk.Label(lblf_content, text='Data Source: ')
        lbl_data_source.grid(row=cur_row, column=0, columnspan=3, **grid_ew_options)
        cur_col += 3
        lbl_data_type = ttk.Label(lblf_content, text='Type: ')
        lbl_data_type.grid(row=cur_row, column=cur_col, **grid_def_options_np, sticky=tk.E)
        cur_col += 1
        self.var_entry_data_source_type = tk.StringVar(value=data_table.data_source_type.name)
        # noinspection PyArgumentList
        # (bootstyle is not recognized by PyCharm)
        entry_data_type = ttk.Entry(lblf_content, textvariable=self.var_entry_data_source_type, state='readonly', width=6, bootstyle=WARNING)
        entry_data_type.grid(row=cur_row, column=cur_col, **grid_def_options_np, sticky=tk.W)
        # new row
        cur_row += 1
        cur_col = 0
        self.var_entry_data_source_name = tk.StringVar(value=data_table.data_source)
        self.entry_data_source = ttk.Entry(lblf_content, textvariable=self.var_entry_data_source_name, state='readonly')
        self.entry_data_source.grid(row=cur_row, column=cur_col, columnspan=max_col, **grid_ew_options)
        # new row
        cur_row += 1
        cur_col = 0
        self.buttons = {
            'add_row': {
                'text': 'Add',  # if empty, the key of the dict will be used
                'command': container.add_row
            },  #
            'del_row': {
                'text': 'Del',  # if empty, the key of the dict will be used
                'command': container.del_row
            },  #
            'edit_row': {
                'text': 'Edit',  # if empty, the key of the dict will be used
                'command': container.edit_row
            },  #
            'scrap_row': {
                'text': 'Scrap',  # if empty, the key of the dict will be used
                'command': container.scrap_row
            },  #
            'scan_for_assets': {
                'text': 'Scan Assets',  # if empty, the key of the dict will be used
                'command': container.scan_for_assets
            },  #
            'load_table': {
                'text': 'Load',  # if empty, the key of the dict will be used
                'command': container.open_file
            },  #
            'save_changes': {
                'text': ' Save ',  # if empty, the key of the dict will be used
                'command': container.save_changes
            },  #
            'export_selection': {
                'text': 'Export',  # if empty, the key of the dict will be used
                'command': container.export_selection
            },  #
            'reload_data': {
                'text': 'Reload',  # if empty, the key of the dict will be used
                'command': container.reload_data
            },  #
            'rebuild_data': {
                'text': 'Rebuild',  # if empty, the key of the dict will be used
                'command': container.rebuild_data
            },  #
        }
        for key, values in self.buttons.items():
            text = values['text'] if values['text'] else key
            btn = ttk.Button(lblf_content, text=text, command=values['command'])
            btn.grid(row=cur_row, column=cur_col, **grid_ew_options)
            cur_col += 1
            if cur_col % max_col == 0:
                cur_row += 1
                cur_col = 0
            self.buttons[key]['widget'] = btn
        widget_list = gui_g.stated_widgets.get('row_is_selected', [])
        append_no_duplicate(widget_list, [self.buttons['add_row']['widget'], self.buttons['edit_row']['widget'], self.buttons['scrap_row']['widget']])
        widget_list = gui_g.stated_widgets.get('table_has_changed', [])
        append_no_duplicate(widget_list, [self.buttons['save_changes']['widget']])

        lblf_content.columnconfigure('all', weight=1)  # important to make the buttons expand

        frm_filter = FilterFrame(
            self,
            data_func=data_table.get_data,
            update_func=data_table.update,
            save_filter_func=self.save_filters,
            value_for_all=gui_g.s.default_value_for_all,
            dynamic_filters_func=container.create_dynamic_filters,
        )
        frm_filter.pack(**lblf_def_options)
        container._frm_filter = frm_filter
        data_table.set_frm_filter(frm_filter)

        # Note: the TAG of the child widgets of the lbf_quick_edit will also be used in the editable_table.quick_edit method
        # to get the widgets it needs. So they can't be changed freely
        self.lbtf_quick_edit = TaggedLabelFrame(self, text='Select a row for Quick Editing')
        self.lbtf_quick_edit.pack(**lblf_fw_options, anchor=tk.NW)
        data_table.set_frm_quick_edit(self.lbtf_quick_edit)

        frm_asset_action = ttk.Frame(self.lbtf_quick_edit)
        btn_open_url = ttk.Button(frm_asset_action, text='Open Url', command=container.open_asset_url)
        btn_open_url.pack(**pack_def_options, side=tk.LEFT)
        btn_open_folder = ttk.Button(frm_asset_action, text='Open Folder', command=container.open_asset_folder)
        btn_open_folder.pack(**pack_def_options, side=tk.LEFT)
        btn_download_asset = ttk.Button(frm_asset_action, text='download', command=container.download_asset)
        btn_download_asset.pack(**pack_def_options, side=tk.LEFT)
        btn_install_asset = ttk.Button(frm_asset_action, text='INSTALL', command=container.install_asset)
        btn_install_asset.pack(**pack_def_options, side=tk.LEFT)
        frm_asset_action.pack(**lblf_fw_options)
        widget_list = gui_g.stated_widgets.get('row_is_selected', [])
        append_no_duplicate(widget_list, [btn_open_url, btn_open_folder, btn_download_asset, btn_install_asset])

        ttk_item = ttk.Label(self.lbtf_quick_edit, text='Values bellow will be updated for the selected row on focus lost', foreground='#158CBA')
        ttk_item.pack()
        self.var_asset_id = tk.StringVar(value='')
        self.lbtf_quick_edit.add_child(
            widget_type=WidgetType.ENTRY,
            tag='Asset_id',
            state='readonly',
            label='Asset id (click to copy)',
            width=5,
            click_on_callback=container.copy_asset_id,
            textvariable=self.var_asset_id,
        )
        self.lbtf_quick_edit.add_child(
            widget_type=WidgetType.ENTRY,
            tag='Url',
            focus_out_callback=container.on_quick_edit_focus_out,
            focus_in_callback=container.on_quick_edit_focus_in
        )
        self.lbtf_quick_edit.add_child(
            widget_type=WidgetType.TEXT,
            tag='Comment',
            focus_out_callback=container.on_quick_edit_focus_out,
            focus_in_callback=container.on_quick_edit_focus_in,
            width=10,
            height=4
        )
        self.lbtf_quick_edit.add_child(
            widget_type=WidgetType.ENTRY,
            tag='Stars',
            focus_out_callback=container.on_quick_edit_focus_out,
            focus_in_callback=container.on_quick_edit_focus_in
        )
        self.lbtf_quick_edit.add_child(
            widget_type=WidgetType.ENTRY,
            tag='Test result',
            focus_out_callback=container.on_quick_edit_focus_out,
            focus_in_callback=container.on_quick_edit_focus_in
        )
        self.lbtf_quick_edit.add_child(
            widget_type=WidgetType.ENTRY,
            tag='Installed folders',
            default_content='Installed in',
            focus_out_callback=container.on_quick_edit_focus_out,
            focus_in_callback=container.on_quick_edit_focus_in
        )
        self.lbtf_quick_edit.add_child(
            widget_type=WidgetType.ENTRY,
            tag='Origin',
            focus_out_callback=container.on_quick_edit_focus_out,
            focus_in_callback=container.on_quick_edit_focus_in
        )
        self.lbtf_quick_edit.add_child(
            widget_type=WidgetType.ENTRY,
            tag='Alternative',
            focus_out_callback=container.on_quick_edit_focus_out,
            focus_in_callback=container.on_quick_edit_focus_in
        )

        frm_inner = ttk.Frame(self.lbtf_quick_edit, relief=tk.RIDGE, borderwidth=1)
        inner_pack_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.X, 'expand': False, 'anchor': tk.W}
        frm_inner.pack(**inner_pack_options)
        self.lbtf_quick_edit.add_child(
            widget_type=WidgetType.CHECKBUTTON,
            alternate_container=frm_inner,
            layout_option=inner_pack_options,
            tag='Must buy',
            label='Must buy',
            images_folder=gui_g.s.assets_folder,
            click_on_callback=container.on_switch_edit_flag,
            default_content=False
        )
        self.lbtf_quick_edit.add_child(
            widget_type=WidgetType.CHECKBUTTON,
            alternate_container=frm_inner,
            layout_option=inner_pack_options,
            tag='Added manually',
            label='          Added manually',
            images_folder=gui_g.s.assets_folder,
            click_on_callback=container.on_switch_edit_flag,
            default_content=False
        )

        self.lbf_image_preview = ttk.LabelFrame(self, text='Image Preview')
        self.lbf_image_preview.pack(**lblf_fw_options, anchor=tk.SW)
        self.canvas_image = tk.Canvas(
            self.lbf_image_preview, width=gui_g.s.preview_max_width, height=gui_g.s.preview_max_height, highlightthickness=0
        )
        self.canvas_image.pack(side=tk.BOTTOM, expand=True, anchor=tk.CENTER)
        self.canvas_image.create_rectangle((0, 0), (gui_g.s.preview_max_width, gui_g.s.preview_max_height), fill='black')

        lblf_bottom = ttk.Frame(self)
        lblf_bottom.pack(**lblf_def_options)
        ttk.Sizegrip(lblf_bottom).pack(side=tk.RIGHT)

    @staticmethod
    def save_filters(filters: dict):
        """
        Save the filters to the config file.
        :param filters:.
        :return:
        """
        gui_g.s.data_filters = filters  # will call set_data_filters
        gui_g.s.save_config_file()
