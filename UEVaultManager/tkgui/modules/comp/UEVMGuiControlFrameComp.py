# coding=utf-8
"""
Implementation for:
- UEVMGuiControlFrame: control frame for the UEVMGui Class.
"""
import os
import tkinter as tk
from tkinter import filedialog as fd, messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import WARNING

import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.models.csv_sql_fields import get_label_for_field
from UEVaultManager.tkgui.modules.cls.EditableTableClass import EditableTable
from UEVaultManager.tkgui.modules.comp.FilterFrameComp import FilterFrame
from UEVaultManager.tkgui.modules.comp.TaggedLabelFrameComp import TaggedLabelFrame
from UEVaultManager.tkgui.modules.functions_no_deps import append_no_duplicate
from UEVaultManager.tkgui.modules.types import WidgetType


class UEVMGuiControlFrame(ttk.Frame):
    """
    A control frame for the UEVMGui Class.
    :param container: parent self._container.
    :param data_table: EditableTable instance.
    """

    def __init__(self, container, data_table: EditableTable):
        super().__init__()
        if container is None:
            raise ValueError('container must be None')
        if data_table is None:
            raise ValueError('data_table must be a UEVMGuiContentFrame instance')

        self._data_table: EditableTable = data_table
        self._container = container

        pack_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.BOTH, 'expand': True}
        grid_def_options_np = {'ipadx': 0, 'ipady': 0, 'padx': 0, 'pady': 0}  # no padding
        # pack_def_options = {'ipadx': 2, 'ipady': 2, 'fill': tk.BOTH, 'expand': False}
        grid_ew_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'sticky': tk.EW}  # full width
        lblf_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.X, 'expand': False}
        lblf_fw_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.X, 'expand': True}  # full width
        # content frame
        lblf_content = ttk.LabelFrame(self, text='Data Table and content')
        lblf_content.pack(**lblf_def_options)
        max_col = 6
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
        entry_data_type = ttk.Entry(lblf_content, textvariable=self.var_entry_data_source_type, state='readonly', width=10, bootstyle=WARNING)
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
                'command': self._container.add_row
            },  #
            'del_row': {
                'text': 'Del',  # if empty, the key of the dict will be used
                'command': self._container.del_row
            },  #
            'edit_row': {
                'text': 'Edit',  # if empty, the key of the dict will be used
                'command': self._container.edit_row
            },  #
            'scrap_asset': {
                'text': 'Scrap',  # if empty, the key of the dict will be used
                'command': self._container.scrap_asset
            },  #
            'scrap_range': {
                'text': 'Scrap range',  # if empty, the key of the dict will be used
                'command': self._container.scrap_range
            },  #
            'scan_for_assets': {
                'text': 'Scan assets',  # if empty, the key of the dict will be used
                'command': self._container.scan_for_assets
            },  #
            'load_table': {
                'text': 'Load',  # if empty, the key of the dict will be used
                'command': self._container.open_file
            },  #
            'save_changes': {
                'text': ' Save ',  # if empty, the key of the dict will be used
                'command': self._container.save_changes
            },  #
            'save_changes_as': {
                'text': ' Save As',  # if empty, the key of the dict will be used
                'command': self._container.save_changes_as
            },  #
            'export_selection': {
                'text': 'Export',  # if empty, the key of the dict will be used
                'command': self._container.export_selection
            },  #
            'reload_data': {
                'text': 'Reload',  # if empty, the key of the dict will be used
                'command': self._container.reload_data
            },  #
            'rebuild_data': {
                'text': 'Rebuild',  # if empty, the key of the dict will be used
                'command': self._container.rebuild_data
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

        lblf_content.columnconfigure('all', weight=1)  # important to make the buttons expand

        frm_filter = FilterFrame(
            self,
            data_func=data_table.get_data,
            update_func=data_table.update,
            save_filter_func=self.save_filters,
            load_filter_func=self.load_filters,
            value_for_all=gui_g.s.default_value_for_all,
            quick_filters=self._container.create_dynamic_filters(),
        )
        frm_filter.pack(**lblf_def_options)
        self._container._frm_filter = frm_filter
        data_table.set_frm_filter(frm_filter)

        # Note: TAG of the child widgets of the lbf_quick_edit will also be used in the editable_table.quick_edit method
        # to get the widgets it needs. So they can't be changed freely
        self.lbtf_quick_edit = TaggedLabelFrame(self, text='Select a row for Quick Editing its USER FIELDS')
        self.lbtf_quick_edit.pack(**lblf_fw_options, anchor=tk.NW)
        data_table.set_frm_quick_edit(self.lbtf_quick_edit)

        frm_asset_action = ttk.Frame(self.lbtf_quick_edit)
        btn_open_url = ttk.Button(frm_asset_action, text='Open Url', command=self._container.open_asset_url)
        btn_open_url.pack(**pack_def_options, side=tk.LEFT)
        btn_open_folder = ttk.Button(frm_asset_action, text='Open Folder', command=self._container.open_asset_folder)
        btn_open_folder.pack(**pack_def_options, side=tk.LEFT)
        btn_show_installed_releases = ttk.Button(frm_asset_action, text='Releases', command=self._container.show_installed_releases)
        btn_show_installed_releases.pack(**pack_def_options, side=tk.LEFT)
        btn_download_asset = ttk.Button(frm_asset_action, text='Download', command=self._container.download_asset)
        btn_download_asset.pack(**pack_def_options, side=tk.LEFT)
        btn_install_asset = ttk.Button(frm_asset_action, text='INSTALL', command=self._container.install_asset)
        btn_install_asset.pack(**pack_def_options, side=tk.LEFT)
        frm_asset_action.pack(**lblf_fw_options)

        ttk_item = ttk.Label(self.lbtf_quick_edit, text='The selected row values are updated when focus changes', foreground='#158CBA')
        ttk_item.pack()
        self.var_asset_id = tk.StringVar(value='')
        tag = 'Asset_id'
        self.lbtf_quick_edit.add_child(
            widget_type=WidgetType.ENTRY,
            tag=tag,
            state='readonly',
            label=get_label_for_field(tag) + ' (click to copy)',
            width=5,
            click_on_callback=self._container.copy_asset_id,
            textvariable=self.var_asset_id,
        )
        tag = 'Url'
        self.lbtf_quick_edit.add_child(
            widget_type=WidgetType.ENTRY,
            tag=tag,
            focus_out_callback=self._container.on_quick_edit_focus_out,
            focus_in_callback=self._container.on_quick_edit_focus_in
        )
        tag = 'Comment'
        self.lbtf_quick_edit.add_child(
            widget_type=WidgetType.TEXT,
            tag=tag,
            focus_out_callback=self._container.on_quick_edit_focus_out,
            focus_in_callback=self._container.on_quick_edit_focus_in,
            width=10,
            height=4
        )
        tag = 'Stars'
        self.lbtf_quick_edit.add_child(
            widget_type=WidgetType.ENTRY,
            tag=tag,
            focus_out_callback=self._container.on_quick_edit_focus_out,
            focus_in_callback=self._container.on_quick_edit_focus_in
        )
        tag = 'Test result'
        self.lbtf_quick_edit.add_child(
            widget_type=WidgetType.ENTRY,
            tag=tag,
            focus_out_callback=self._container.on_quick_edit_focus_out,
            focus_in_callback=self._container.on_quick_edit_focus_in
        )
        tag = 'Installed folders'
        self.lbtf_quick_edit.add_child(
            widget_type=WidgetType.ENTRY,
            tag=tag,
            label=get_label_for_field(tag),
            default_content='Installed in',
            focus_out_callback=self._container.on_quick_edit_focus_out,
            focus_in_callback=self._container.on_quick_edit_focus_in
        )
        tag = 'Origin'
        self.lbtf_quick_edit.add_child(
            widget_type=WidgetType.ENTRY,
            tag=tag,
            focus_out_callback=self._container.on_quick_edit_focus_out,
            focus_in_callback=self._container.on_quick_edit_focus_in
        )
        tag = 'Alternative'
        self.lbtf_quick_edit.add_child(
            widget_type=WidgetType.ENTRY,
            tag=tag,
            focus_out_callback=self._container.on_quick_edit_focus_out,
            focus_in_callback=self._container.on_quick_edit_focus_in
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
            click_on_callback=self._container.on_switch_edit_flag,
            default_content=False
        )
        self.lbtf_quick_edit.add_child(
            widget_type=WidgetType.CHECKBUTTON,
            alternate_container=frm_inner,
            layout_option=inner_pack_options,
            tag='Added manually',
            label='          Added manually',  # add spaces to align with the "Must buy" checkbutton
            images_folder=gui_g.s.assets_folder,
            click_on_callback=self._container.on_switch_edit_flag,
            default_content=False
        )

        self.asset_infos = ttk.LabelFrame(self, text='Asset Preview')
        self.asset_infos.pack(**lblf_fw_options, anchor=tk.SW)
        self.canvas_image = tk.Canvas(self.asset_infos, width=gui_g.s.preview_max_width, height=gui_g.s.preview_max_height, highlightthickness=0)
        self.canvas_image.pack(side=tk.RIGHT, expand=True, anchor=tk.CENTER)
        self.canvas_image.create_rectangle((0, 0), (gui_g.s.preview_max_width, gui_g.s.preview_max_height), fill='black')
        asset_info = 'No info'
        self.txt_info = ttk.Text(self.asset_infos, height=5, width=34)
        self.txt_info.pack(side=tk.LEFT, expand=True, anchor=tk.CENTER)
        self.txt_info.insert(tk.END, asset_info)

        lblf_bottom = ttk.Frame(self)
        lblf_bottom.pack(**lblf_def_options)
        ttk.Sizegrip(lblf_bottom).pack(side=tk.RIGHT)

        widget_list = gui_g.stated_widgets.get('row_is_selected', [])
        append_no_duplicate(widget_list, [self.buttons['edit_row']['widget'], btn_show_installed_releases])
        widget_list = gui_g.stated_widgets.get('table_has_changed', [])
        append_no_duplicate(widget_list, [self.buttons['save_changes']['widget']])
        widget_list = gui_g.stated_widgets.get('not_offline', [])
        append_no_duplicate(widget_list, [self.buttons['scrap_range']['widget'], self.buttons['scan_for_assets']['widget']])
        widget_list = gui_g.stated_widgets.get('asset_is_owned_and_not_offline', [])
        append_no_duplicate(widget_list, [btn_download_asset, btn_install_asset])
        widget_list = gui_g.stated_widgets.get('asset_has_url', [])
        append_no_duplicate(widget_list, [btn_open_url])
        widget_list = gui_g.stated_widgets.get('asset_added_mannually', [])
        append_no_duplicate(widget_list, [btn_open_folder])
        widget_list = gui_g.stated_widgets.get('row_is_selected_and_not_offline', [])
        append_no_duplicate(widget_list, [self.buttons['scrap_asset']['widget']])
        widget_list = gui_g.stated_widgets.get('file_is_used', [])
        append_no_duplicate(widget_list, [self.buttons['save_changes_as']['widget']])

    def save_filters(self, filters: dict) -> None:
        """
        Save the filters to a file (Wrapper)
        :param filters: filters to save.
        """
        json_ext = '.json'
        if not filters:
            return
        folder = gui_g.s.filters_folder if gui_g.s.filters_folder else gui_g.s.path
        folder = os.path.abspath(folder)
        if folder and not os.path.isdir(folder):
            os.mkdir(folder)
        filename = fd.asksaveasfilename(
            title='Choose a file to save filters to', initialdir=folder, filetypes=[('json file', '*.json')], initialfile=gui_g.s.last_opened_filter
        )
        if not filename:
            return
        filename = os.path.normpath(filename)
        fd_folder = os.path.dirname(filename)
        filename = os.path.basename(filename)  # remove the folder from the filename
        filename, ext = os.path.splitext(filename)
        if not ext:
            filename += json_ext
        elif ext.lower() != json_ext:
            messagebox.showwarning('Warning', f'Filters can only be save to a json file. Do not forget to add the extension to the filename.')
            return
        if folder != fd_folder:
            messagebox.showwarning('Warning', f'The folder to save filters into can not be changed. The file will be saved in {folder}')
        try:
            self._container.core.uevmlfs.save_filter_list(filters, filename)
        except AttributeError:
            pass

    def load_filters(self) -> dict:
        """
        Load the filters from a file (Wrapper)
        """
        folder = gui_g.s.filters_folder if gui_g.s.filters_folder else gui_g.s.path
        folder = os.path.abspath(folder)
        if folder and not os.path.isdir(folder):
            os.mkdir(folder)
        filename = fd.askopenfilename(
            title='Choose a file to load filters from',
            initialdir=gui_g.s.filters_folder,
            filetypes=[('json file', '*.json')],
            initialfile=gui_g.s.last_opened_filter
        )
        if not filename:
            return {}
        filename = os.path.normpath(filename)
        fd_folder = os.path.dirname(filename)
        if folder != fd_folder:
            messagebox.showwarning(
                'Warning', f'Only files in the folder {folder} can be loaded as filters. Please try again without changing the folder.'
            )
            return {}
        filename = os.path.basename(filename)  # remove the folder from the filename
        _, ext = os.path.splitext(filename)
        if ext != '.json':
            messagebox.showwarning('Warning', f'Filters can only be read from a json file.')
            return {}
        try:
            filters = self._container.core.uevmlfs.load_filter_list(filename)
            gui_g.s.last_opened_filter = filename
            gui_g.s.save_config_file()
        except AttributeError:
            filters = None
        if filters is None:
            messagebox.showwarning('Warning', f'An error occurs when opening the filter file. Check its content')
            filters = {}
        return filters
