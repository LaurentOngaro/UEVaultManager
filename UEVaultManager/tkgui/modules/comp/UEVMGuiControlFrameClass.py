# coding=utf-8
"""
Implementation for:
- UEVMGuiControlFrame: a control frame for the UEVMGui Class
"""
import tkinter as tk

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.cls.EditableTableClass import EditableTable
from UEVaultManager.tkgui.modules.comp.FilterFrameClass import FilterFrame
from UEVaultManager.tkgui.modules.comp.TaggedLabelFrameClass import TaggedLabelFrame
from UEVaultManager.tkgui.modules.types import WidgetType


class UEVMGuiControlFrame(ttk.Frame):
    """
    A control frame for the UEVMGui Class
    :param container: The parent container.
    :param data_table: The EditableTable instance
    """

    def __init__(self, container, data_table: EditableTable):
        super().__init__()
        if container is None:
            raise ValueError('container must be None')
        if data_table is None:
            raise ValueError('data_table must be a UEVMGuiTableFrame instance')

        self.data_table: EditableTable = data_table

        grid_def_options = {'ipadx': 1, 'ipady': 1, 'padx': 1, 'pady': 1, 'sticky': tk.SE}
        grid_def_options_np = {'ipadx': 0, 'ipady': 0, 'padx': 0, 'pady': 0, 'sticky': tk.SE}  # no padding
        # pack_def_options = {'ipadx': 2, 'ipady': 2, 'fill': tk.BOTH, 'expand': False}
        grid_fw_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'sticky': tk.EW}  # full width
        lblf_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.X, 'expand': False}
        lblf_fw_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.X, 'expand': True}  # full width

        lblf_content = ttk.LabelFrame(self, text='Content')
        lblf_content.pack(**lblf_def_options)
        btn_edit_row = ttk.Button(lblf_content, text='Edit Row', command=data_table.create_edit_record_window)
        btn_edit_row.grid(row=0, column=0, **grid_fw_options)
        btn_reload_data = ttk.Button(lblf_content, text='Reload Content', command=container.reload_data)
        btn_reload_data.grid(row=0, column=1, **grid_fw_options)
        btn_rebuild_file = ttk.Button(lblf_content, text='Rebuild Content', command=container.rebuild_data)
        btn_rebuild_file.grid(row=0, column=2, **grid_fw_options)
        lblf_content.columnconfigure('all', weight=1)  # important to make the buttons expand

        filter_frame = FilterFrame(self, data_func=data_table.get_data, update_func=data_table.update, value_for_all=gui_g.s.default_value_for_all)
        filter_frame.pack(**lblf_def_options)
        container._filter_frame = filter_frame
        data_table.set_filter_frame(filter_frame)

        lblf_files = ttk.LabelFrame(self, text='Files')
        lblf_files.pack(**lblf_def_options)
        lbl_data_source = ttk.Label(lblf_files, text='Data Source: ')
        lbl_data_source.grid(row=0, column=0, columnspan=2, **grid_fw_options)
        frm_inner = ttk.Frame(lblf_files)
        frm_inner.grid(row=0, column=2, **grid_fw_options)

        lbl_data_type = ttk.Label(frm_inner, text='Type: ')
        lbl_data_type.grid(row=0, column=0, **grid_def_options_np)
        var_entry_data_source_type = tk.StringVar(value=data_table.data_source_type.name)
        # noinspection PyArgumentList
        entry_data_type = ttk.Entry(frm_inner, textvariable=var_entry_data_source_type, state='readonly', width=6, bootstyle=WARNING)
        entry_data_type.grid(row=0, column=1, **grid_def_options_np)

        var_entry_data_source_name = tk.StringVar(value=data_table.data_source)
        entry_data_source = ttk.Entry(lblf_files, textvariable=var_entry_data_source_name, state='readonly')
        entry_data_source.grid(row=1, column=0, columnspan=3, **grid_fw_options)
        btn_save_data = ttk.Button(lblf_files, text='Save Data', command=container.save_data)
        btn_save_data.grid(row=2, column=0, **grid_fw_options)
        btn_export_button = ttk.Button(lblf_files, text='Export Selection', command=container.export_selection)
        btn_export_button.grid(row=2, column=1, **grid_fw_options)
        btn_load_data = ttk.Button(lblf_files, text='Load Data', command=container.load_data)
        btn_load_data.grid(row=2, column=2, **grid_fw_options)
        lblf_files.columnconfigure('all', weight=1)  # important to make the buttons expand

        # Note: the TAG of the child widgets of the lbf_quick_edit will also be used in the editable_table.quick_edit method
        # to get the widgets it needs. So they can't be changed freely
        lbtf_quick_edit = TaggedLabelFrame(self, text='Quick Edit User fields')
        lbtf_quick_edit.pack(**lblf_fw_options, anchor=tk.NW)
        data_table.set_quick_edit_frame(lbtf_quick_edit)

        frm_inner_frame = ttk.Frame(lbtf_quick_edit)
        lbl_desc = ttk.Label(frm_inner_frame, text='Changing this values will change the values of \nthe selected row when losing focus')
        lbl_desc.grid(row=0, column=0, **grid_def_options)
        bt_open_url = ttk.Button(frm_inner_frame, text='Open Url', command=container.open_asset_url)
        bt_open_url.grid(row=0, column=1, **grid_def_options)
        frm_inner_frame.pack()

        lbtf_quick_edit.add_child(
            widget_type=WidgetType.ENTRY,
            tag='Url',
            focus_out_callback=container.on_quick_edit_focus_out,
            focus_in_callback=container.on_quick_edit_focus_in
        )
        lbtf_quick_edit.add_child(
            widget_type=WidgetType.TEXT,
            tag='Comment',
            focus_out_callback=container.on_quick_edit_focus_out,
            focus_in_callback=container.on_quick_edit_focus_in,
            width=10,
            height=4
        )
        lbtf_quick_edit.add_child(
            widget_type=WidgetType.ENTRY,
            tag='Stars',
            focus_out_callback=container.on_quick_edit_focus_out,
            focus_in_callback=container.on_quick_edit_focus_in
        )
        lbtf_quick_edit.add_child(
            widget_type=WidgetType.ENTRY,
            tag='Test result',
            focus_out_callback=container.on_quick_edit_focus_out,
            focus_in_callback=container.on_quick_edit_focus_in
        )

        lbtf_quick_edit.add_child(
            widget_type=WidgetType.ENTRY,
            tag='Installed folder',
            default_content='Installed in',
            focus_out_callback=container.on_quick_edit_focus_out,
            focus_in_callback=container.on_quick_edit_focus_in
        )
        lbtf_quick_edit.add_child(
            widget_type=WidgetType.ENTRY,
            tag='Origin',
            focus_out_callback=container.on_quick_edit_focus_out,
            focus_in_callback=container.on_quick_edit_focus_in
        )
        lbtf_quick_edit.add_child(
            widget_type=WidgetType.ENTRY,
            tag='Alternative',
            focus_out_callback=container.on_quick_edit_focus_out,
            focus_in_callback=container.on_quick_edit_focus_in
        )

        frm_inner_frame = ttk.Frame(lbtf_quick_edit, relief=tk.RIDGE, borderwidth=1)
        inner_pack_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.X, 'expand': False, 'anchor': tk.W}
        frm_inner_frame.pack(**inner_pack_options)
        lbtf_quick_edit.add_child(
            widget_type=WidgetType.CHECKBUTTON,
            alternate_container=frm_inner_frame,
            layout_option=inner_pack_options,
            tag='Must buy',
            label='',
            images_folder=gui_g.s.assets_folder,
            click_on_callback=container.on_switch_edit_flag,
            default_content=False
        )
        lbtf_quick_edit.add_child(
            widget_type=WidgetType.CHECKBUTTON,
            alternate_container=frm_inner_frame,
            layout_option=inner_pack_options,
            tag='Added manually',
            label='',
            images_folder=gui_g.s.assets_folder,
            click_on_callback=container.on_switch_edit_flag,
            default_content=False
        )
        lbt_image_preview = ttk.LabelFrame(self, text='Image Preview')
        lbt_image_preview.pack(**lblf_fw_options, anchor=tk.SW)
        canvas_image = tk.Canvas(lbt_image_preview, width=gui_g.s.preview_max_width, height=gui_g.s.preview_max_height, highlightthickness=0)
        canvas_image.pack(side=tk.BOTTOM, expand=True, anchor=tk.CENTER)
        canvas_image.create_rectangle((0, 0), (gui_g.s.preview_max_width, gui_g.s.preview_max_height), fill='black')

        lblf_bottom = ttk.Frame(self)
        lblf_bottom.pack(**lblf_def_options)
        ttk.Sizegrip(lblf_bottom).pack(side=tk.RIGHT)

        # store the controls that need to be accessible outside the class
        self.var_entry_data_source_name = var_entry_data_source_name
        self.var_entry_data_source_type = var_entry_data_source_type

        self.lbtf_quick_edit = lbtf_quick_edit
        self.canvas_image = canvas_image
