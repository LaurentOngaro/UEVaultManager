import os
import tkinter as tk
from tkinter import filedialog as fd

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.EditableTableClass import EditableTable
from UEVaultManager.tkgui.modules.functions import set_custom_style
from UEVaultManager.tkgui.modules.TaggedLabelFrameClass import TaggedLabelFrame, WidgetType


class UEVMGuiHiddenRoot(ttk.Window):
    """
    This class is used to create a hidden root window for the application.
    Usefull for creating a window that is not visible to the user, but still has the ability to child windows
    """

    def __init__(self):
        super().__init__()
        self.title('UEVMGui Hidden window')
        self.geometry('100x150')
        self.withdraw()


class UEVMGui(tk.Tk):
    """
    This class is used to create the main window for the application.
    :param title: The title
    :param width: The width
    :param height: The height
    :param icon: The icon
    :param screen_index: The screen index
    :param file: The file where the data is stored or read from
    :param show_open_file_dialog: If True, the open file dialog will be shown at startup
    """

    def __init__(self, title: str, width=1200, height=800, icon='', screen_index=0, file='', show_open_file_dialog=False):
        super().__init__()
        self.title(title)
        style = set_custom_style(gui_g.s.theme_name, gui_g.s.theme_font)
        self.style = style
        geometry = gui_f.center_window_on_screen(screen_index, height, width)
        self.geometry(geometry)
        if icon is None:
            self.attributes('-toolwindow', True)
        else:
            # windows only (remove the minimize/maximize buttons and the icon)
            icon = gui_f.path_from_relative_to_absolute(icon)
            if icon != '' and os.path.isfile(icon):
                self.iconbitmap(icon)
        self.resizable(True, False)
        self.editable_table = None
        self.do_not_launch_search = False
        pack_def_options = {'ipadx': 5, 'ipady': 5, 'padx': 3, 'pady': 3}

        table_frame = self.TableFrame(self)
        self.editable_table = EditableTable(container_frame=table_frame, file=file, fontsize=gui_g.s.table_font_size, show_statusbar=True)
        self.editable_table.show()
        self.editable_table.show_page(0)

        self.table_frame = table_frame
        toolbar_frame = self.ToolbarFrame(self)
        self.toolbar_frame = toolbar_frame
        control_frame = self.ControlFrame(self)
        self.control_frame = control_frame

        toolbar_frame.pack(**pack_def_options, fill=tk.X, side=tk.TOP, anchor=tk.NW)
        table_frame.pack(**pack_def_options, fill=tk.BOTH, side=tk.LEFT, anchor=tk.NW, expand=True)
        control_frame.pack(**pack_def_options, fill=tk.BOTH, side=tk.RIGHT, anchor=tk.NW)

        self.bind('<Key>', self.on_key_press)
        # Bind the table to the mouse motion event
        self.editable_table.bind('<Motion>', self.on_mouse_over_cell)
        self.editable_table.bind('<Leave>', self.on_mouse_leave_cell)
        self.editable_table.bind('<<CellSelectionChanged>>', self.on_selection_change)
        self.protocol('WM_DELETE_WINDOW', self.on_close)

        if show_open_file_dialog:
            if self.load_file() == '':
                gui_f.log_error(f'This application could not run without a file to read data from')
                self.quit()

    class ToolbarFrame(ttk.Frame):
        """
        This class is used to create the toolbar frame
        :param container: The parent container
        """

        def __init__(self, container):
            super().__init__()
            pack_def_options = {'ipadx': 2, 'ipady': 2, 'fill': tk.BOTH, 'expand': False}
            lblf_def_options = {'ipadx': 1, 'ipady': 1, 'expand': False}

            lblf_navigation = ttk.LabelFrame(self, text='Navigation')
            lblf_navigation.pack(side=tk.LEFT, **lblf_def_options)
            # (bootstyle is not recognized by PyCharm)
            # noinspection PyArgumentList
            btn_toggle_pagination = ttk.Button(lblf_navigation, text='Disable Pagination', command=container.toggle_pagination)
            # noinspection PyArgumentList
            btn_toggle_pagination.pack(**pack_def_options, side=tk.LEFT)
            btn_first_page = ttk.Button(lblf_navigation, text='First Page', command=container.show_first_page)
            btn_first_page.pack(**pack_def_options, side=tk.LEFT)
            btn_first_page.config(state=tk.DISABLED)
            btn_prev_page = ttk.Button(lblf_navigation, text='Prev Page', command=container.show_prev_page)
            btn_prev_page.pack(**pack_def_options, side=tk.LEFT)
            btn_prev_page.config(state=tk.DISABLED)
            entry_page_num_var = tk.StringVar(value=container.editable_table.current_page + 1)
            entry_page_num = ttk.Entry(lblf_navigation, width=5, justify=tk.CENTER, textvariable=entry_page_num_var)
            entry_page_num.pack(**pack_def_options, side=tk.LEFT)
            lbl_page_count = ttk.Label(lblf_navigation, text=f' / {container.editable_table.total_pages}')
            lbl_page_count.pack(**pack_def_options, side=tk.LEFT)
            btn_next_page = ttk.Button(lblf_navigation, text='Next Page', command=container.show_next_page)
            btn_next_page.pack(**pack_def_options, side=tk.LEFT)
            btn_last_page = ttk.Button(lblf_navigation, text='Last Page', command=container.show_last_page)
            btn_last_page.pack(**pack_def_options, side=tk.LEFT)
            btn_prev = ttk.Button(lblf_navigation, text='Prev Asset', command=container.prev_asset)
            btn_prev.pack(**pack_def_options, side=tk.LEFT)
            btn_next = ttk.Button(lblf_navigation, text='Next Asset', command=container.next_asset)
            btn_next.pack(**pack_def_options, side=tk.RIGHT)

            lblf_display = ttk.LabelFrame(self, text='Display')
            lblf_display.pack(side=tk.LEFT, **lblf_def_options)
            btn_expand = ttk.Button(lblf_display, text='Expand Cols', command=container.editable_table.expand_columns)
            btn_expand.pack(**pack_def_options, side=tk.LEFT)
            btn_shrink = ttk.Button(lblf_display, text='Shrink Cols', command=container.editable_table.contract_columns)
            btn_shrink.pack(**pack_def_options, side=tk.LEFT)
            btn_autofit = ttk.Button(lblf_display, text='Autofit Cols', command=container.editable_table.autofit_columns)
            btn_autofit.pack(**pack_def_options, side=tk.LEFT)
            btn_zoom_in = ttk.Button(lblf_display, text='Zoom In', command=container.editable_table.zoom_in)
            btn_zoom_in.pack(**pack_def_options, side=tk.LEFT)
            btn_zoom_out = ttk.Button(lblf_display, text='Zoom Out', command=container.editable_table.zoom_out)
            btn_zoom_out.pack(**pack_def_options, side=tk.LEFT)

            lblf_actions = ttk.LabelFrame(self, text='Actions')
            lblf_actions.pack(side=tk.RIGHT, **lblf_def_options)
            # noinspection PyArgumentList
            btn_on_close = ttk.Button(lblf_actions, text='Quit', command=container.on_close, bootstyle=WARNING)
            btn_on_close.pack(**pack_def_options, side=tk.RIGHT)
            btn_toggle_controls = ttk.Button(lblf_actions, text='Hide Controls', command=container.toggle_controls_pane)
            btn_toggle_controls.pack(**pack_def_options, side=tk.RIGHT)

            # Bind events for the Entry widget
            entry_page_num.bind('<FocusOut>', container.on_entry_page_num_changed)
            entry_page_num.bind('<Return>', container.on_entry_page_num_changed)

            self.btn_toggle_pagination = btn_toggle_pagination
            self.btn_first_page = btn_first_page
            self.btn_prev_page = btn_prev_page
            self.btn_next_page = btn_next_page
            self.btn_last_page = btn_last_page
            self.btn_toggle_controls = btn_toggle_controls
            self.lbl_page_count = lbl_page_count
            self.entry_page_num = entry_page_num
            self.entry_page_num_var = entry_page_num_var

    class TableFrame(ttk.Frame):
        """
        The TableFrame is a container for the Table widget.
        :param container: The parent container.
        """

        def __init__(self, container):
            super().__init__(container)

    class ControlFrame(ttk.Frame):
        """
        The ControlFrame is a container for the filter controls.
        :param container: The parent container.
        """

        # delete the temporary text in filter value entry
        def reset_entry_search(self, _event=None):
            self.entry_search.delete(0, 'end')
            self.entry_search.insert(0, gui_g.s.default_global_search)

        def del_entry_search(self, _event=None):
            self.entry_search.delete(0, 'end')

        def __init__(self, container):
            super().__init__()

            # grid_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'sticky': tk.NW}
            pack_def_options = {'ipadx': 2, 'ipady': 2, 'fill': tk.BOTH, 'expand': False}
            grid_fw_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'sticky': tk.EW}  # full width
            lblf_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.X, 'expand': False}
            lblf_fw_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.X, 'expand': True}  # full width

            lblf_content = ttk.LabelFrame(self, text='Content')
            lblf_content.pack(**lblf_def_options)
            btn_edit_row = ttk.Button(lblf_content, text='Edit Row', command=container.editable_table.create_edit_record_window)
            btn_edit_row.grid(row=0, column=0, **grid_fw_options)
            btn_reload_data = ttk.Button(lblf_content, text='Reload File Content', command=container.reload_data)
            btn_reload_data.grid(row=0, column=1, **grid_fw_options)
            btn_rebuild_file = ttk.Button(lblf_content, text='Rebuild File Content', command=container.rebuild_data)
            btn_rebuild_file.grid(row=0, column=2, **grid_fw_options)
            lblf_content.columnconfigure('all', weight=1)  # important to make the buttons expand

            lbf_filter_cat = ttk.LabelFrame(self, text='Search and Filter')
            lbf_filter_cat.pack(fill=tk.X, anchor=tk.NW, ipadx=5, ipady=5)
            var_is_purchased = tk.BooleanVar(value=False)
            var_is_purchased.trace_add('write', container.on_check_change)
            ck_purchased = ttk.Checkbutton(lbf_filter_cat, text='Purchased', variable=var_is_purchased)
            ck_purchased.grid(row=0, column=0, **grid_fw_options)
            var_is_not_obsolete = tk.BooleanVar(value=False)
            var_is_not_obsolete.trace_add('write', container.on_check_change)
            ck_obsolete = ttk.Checkbutton(lbf_filter_cat, text='Not Obsolete', variable=var_is_not_obsolete)
            ck_obsolete.grid(row=0, column=1, **grid_fw_options)
            try:
                # if the file is empty or absent or invalid when creating the class, the data is empty, so no categories
                categories = list(container.editable_table.data['Category'].cat.categories)
            except (AttributeError, TypeError):
                categories = []
            categories.insert(0, gui_g.s.default_category_for_all)
            var_category = tk.StringVar(value=categories[0])
            opt_category = ttk.Combobox(lbf_filter_cat, textvariable=var_category, values=categories)
            opt_category.grid(row=1, column=0, **grid_fw_options)
            var_global_search = tk.StringVar(value=gui_g.s.default_global_search)
            entry_search = ttk.Entry(lbf_filter_cat, textvariable=var_global_search)
            entry_search.grid(row=1, column=1, **grid_fw_options)
            entry_search.bind('<FocusIn>', self.del_entry_search)
            # entry_search.bind('<FocusOut>', container.search)
            btn_filter_by_text = ttk.Button(lbf_filter_cat, text='Filter', command=container.search)
            btn_filter_by_text.grid(row=2, column=0, **grid_fw_options)
            btn_reset_search = ttk.Button(lbf_filter_cat, text='Reset All', command=container.reset_search)
            btn_reset_search.grid(row=2, column=1, **grid_fw_options)
            lbf_filter_cat.columnconfigure('all', weight=1)  # important to make the buttons expand

            lblf_files = ttk.LabelFrame(self, text='Files')
            lblf_files.pack(**lblf_def_options)
            lbl_file_name = ttk.Label(lblf_files, text='Current File: ')
            lbl_file_name.grid(row=0, column=0, columnspan=3, **grid_fw_options)
            entry_file_name_var = tk.StringVar(value=container.editable_table.file)
            entry_file_name = ttk.Entry(lblf_files, textvariable=entry_file_name_var, state='readonly')
            entry_file_name.grid(row=1, column=0, columnspan=3, **grid_fw_options)
            btn_save_file = ttk.Button(lblf_files, text='Save to File', command=container.save_file)
            btn_save_file.grid(row=2, column=0, **grid_fw_options)
            btn_export_button = ttk.Button(lblf_files, text='Export Selection', command=container.export_selection)
            btn_export_button.grid(row=2, column=1, **grid_fw_options)
            btn_load_file = ttk.Button(lblf_files, text='Load a file', command=container.load_file)
            btn_load_file.grid(row=2, column=2, **grid_fw_options)
            lblf_files.columnconfigure('all', weight=1)  # important to make the buttons expand

            # note : the TAG of the child widgets of the lbf_quick_edit will also be used in the editable_table.quick_edit method
            # to get the widgets it needs. So they can't be changed freely
            lbtf_quick_edit = TaggedLabelFrame(self, text='Quick Edit User fields')
            lbtf_quick_edit.pack(**lblf_fw_options, anchor=tk.NW)
            lbl_desc = ttk.Label(lbtf_quick_edit, text='Changing this values will change the values of \nthe selected row when losing focus')
            lbl_desc.pack(**pack_def_options)
            lbtf_quick_edit.add_child(widget_type=WidgetType.ENTRY, tag='Url', focus_out_callback=container.on_quick_edit_focus_out)
            lbtf_quick_edit.add_child(
                widget_type=WidgetType.TEXT, tag='Comment', focus_out_callback=container.on_quick_edit_focus_out, width=10, height=4
            )
            lbtf_quick_edit.add_child(widget_type=WidgetType.ENTRY, tag='Stars', focus_out_callback=container.on_quick_edit_focus_out)
            lbtf_quick_edit.add_child(widget_type=WidgetType.ENTRY, tag='Test_result', focus_out_callback=container.on_quick_edit_focus_out)
            lbtf_quick_edit.add_child(widget_type=WidgetType.ENTRY, tag='Folder', default_content='Installed in')
            lbtf_quick_edit.add_child(widget_type=WidgetType.ENTRY, tag='Alternative', focus_out_callback=container.on_quick_edit_focus_out)

            lbt_image_preview = ttk.LabelFrame(self, text='Image Preview')
            lbt_image_preview.pack(**lblf_fw_options, anchor=tk.SW)
            canvas_image = tk.Canvas(lbt_image_preview, width=gui_g.s.preview_max_width, height=gui_g.s.preview_max_height, highlightthickness=0)
            canvas_image.pack(side=tk.BOTTOM, expand=True, anchor=tk.CENTER)
            canvas_image.create_rectangle((0, 0), (gui_g.s.preview_max_width, gui_g.s.preview_max_height), fill='black')

            lblf_bottom = ttk.Frame(self)
            lblf_bottom.pack(**lblf_def_options)
            ttk.Sizegrip(lblf_bottom).pack(side=tk.RIGHT)

            # store the controls that need to be accessible outside the class
            self.entry_file_name_var = entry_file_name_var
            self.entry_search = entry_search
            self.var_category = var_category
            self.var_global_search = var_global_search
            self.var_is_purchased = var_is_purchased
            self.var_is_not_obsolete = var_is_not_obsolete
            self.lbtf_quick_edit = lbtf_quick_edit
            self.canvas_image = canvas_image

    def _open_file_dialog(self, save_mode=False) -> str:
        """
        Open a file dialog to choose a file to save or load data to/from
        :param save_mode: if True, the dialog will be in saving mode, else in loading mode
        :return: the chosen filename
        """
        # adding category to the default filename
        initial_dir = os.path.dirname(gui_g.s.csv_filename)
        default_filename = os.path.basename(gui_g.s.csv_filename)  # remove dir
        default_ext = os.path.splitext(default_filename)[1]  # get extension
        default_filename = os.path.splitext(default_filename)[0]  # get filename without extension
        try:
            # if the file is empty or absent or invalid when creating the class, the control_frame is not defined
            category = self.control_frame.var_category.get().replace('/', '_')
        except AttributeError:
            category = None
        if category and category != gui_g.s.default_category_for_all:
            default_filename = default_filename + '_' + category + default_ext
        if save_mode:
            filename = fd.asksaveasfilename(
                title='Choose a file to save data to', initialdir=initial_dir, filetypes=gui_g.s.data_filetypes, initialfile=default_filename
            )
        else:
            filename = fd.askopenfilename(
                title='Choose a file to read data from', initialdir=initial_dir, filetypes=gui_g.s.data_filetypes, initialfile=default_filename
            )
        return filename

    def on_key_press(self, event) -> None:
        """
        Handle key press events
        :param event:
        """
        if event.keysym == 'Escape':
            if gui_g.edit_cell_window_ref:
                gui_g.edit_cell_window_ref.destroy()
                gui_g.edit_cell_window_ref = None
            elif gui_g.edit_row_window_ref:
                gui_g.edit_row_window_ref.destroy()
                gui_g.edit_row_window_ref = None
            else:
                self.on_close()
        elif event.keysym == 'Return':
            self.editable_table.create_edit_record_window()

    def on_mouse_over_cell(self, event=None) -> None:
        """
        Show the image of the asset when the mouse is over the cell
        :param event:
        """
        if event is None:
            return
        canvas_image = self.control_frame.canvas_image
        try:
            image_url = self.editable_table.get_image_url(row=self.editable_table.get_row_clicked(event))
            gui_f.show_asset_image(image_url=image_url, canvas_image=canvas_image)
        except IndexError:
            gui_f.show_default_image(canvas_image)

    def on_mouse_leave_cell(self, _event=None) -> None:
        """
        Show the default image when the mouse leaves the cell
        :param _event:
        """
        canvas_image = self.control_frame.canvas_image
        gui_f.show_default_image(canvas_image=canvas_image)

    def on_selection_change(self, event=None) -> None:
        """
        When the selection changes, show the selected row in the quick edit frame
        :param event:
        """
        selected_row = event.widget.currentrow
        self.editable_table.quit_edit_content(quick_edit_frame=self.control_frame.lbtf_quick_edit, row=selected_row)

    def on_entry_page_num_changed(self, _event=None) -> None:
        """
        When the page number changes, show the corresponding page
        :param _event:
        """
        page_num = 0
        try:
            page_num = self.toolbar_frame.entry_page_num.get()
            page_num = int(page_num)
            page_num -= 1
            gui_f.log_debug(f'showing page {page_num}')
            self.editable_table.show_page(page_num)
        except (ValueError, UnboundLocalError) as error:
            gui_f.log_error(f'could not convert page number {page_num} to int. {error!r}')

    # noinspection PyUnusedLocal
    def on_quick_edit_focus_out(self, event=None, tag='') -> None:
        """
        When the focus leaves a quick edit widget, save the value
        :param event:
        :param tag: tag of the widget that triggered the event
        """
        if tag == '':
            return
        widget = self.control_frame.lbtf_quick_edit.get_child_by_tag(tag)
        if widget is None:
            gui_f.log_warning(f'Could not find a widget with tag {tag}')
            return
        col = widget.col
        row = widget.row
        if col is None or row is None or col < 0 or row < 0:
            gui_f.log_debug(f'invalid values for row={row} and col={col}')
            return
        value = widget.get_content()
        self.editable_table.quick_edit_save_value(col=col, row=row, value=value)

    # noinspection PyUnusedLocal
    def on_check_change(self, *args) -> None:
        """
        When a checkbutton is changed, launch a search
        :param args:
        """
        if not self.do_not_launch_search:
            self.search()

    def on_close(self) -> None:
        """
        When the window is closed, check if there are unsaved changes and ask the user if he wants to save them
        """
        if self.editable_table.must_save:
            if gui_f.box_yesno('Changes have been made. Do you want to save them in the source file ?'):
                self.save_file(show_dialog=False)
        self.quit()

    def load_file(self) -> str:
        """
        Load a file
        :return: the name of the file that was loaded
        """
        filename = self._open_file_dialog()
        if filename and os.path.isfile(filename):
            self.editable_table.file = filename
            self.editable_table.load_data()
            self.editable_table.show_page(0)
            self.update_page_numbers()
            self.update_file_name()
            gui_f.box_message(f'The file {filename} as been read')
        return filename

    def save_file(self, show_dialog=True) -> str:
        """
        Save the data to a file
        :param show_dialog: if True, show a dialog to select the file to save to, if False, use the current file
        """
        if show_dialog:
            filename = self._open_file_dialog(save_mode=True)
            if filename:
                self.editable_table.file = filename
        else:
            filename = self.editable_table.file

        if filename:
            self.editable_table.save_data()
            self.update_file_name()
            gui_f.box_message(f'Data Saved to {self.editable_table.file}')
        return filename

    def export_selection(self) -> None:
        """
        Export the selected rows to a file
        """
        # Get selected row indices
        selected_row_indices = self.editable_table.multiplerowlist
        if selected_row_indices:
            selected_rows = self.editable_table.data_filtered.iloc[selected_row_indices]
            filename = self._open_file_dialog(save_mode=True)
            if filename:
                selected_rows.to_csv(filename, index=False)
                gui_f.box_message(f'Selected rows exported to "{filename}"')
        else:
            gui_f.box_message('Select at least one row first')

    def search(self, _event=None) -> None:
        """
        Search for a string in the table
        :param _event: Event
        """
        search_text = self.control_frame.var_global_search.get()
        category = self.control_frame.var_category.get()
        purchased = self.control_frame.var_is_purchased.get()
        not_obsolete = self.control_frame.var_is_not_obsolete.get()
        gui_g.UEVM_filter_category = category
        self.toggle_pagination(forced_value=False)
        filter_dict = {}
        if category != gui_g.s.default_category_for_all:
            filter_dict['Category'] = category
        else:
            filter_dict.pop('Category', None)
        if purchased:
            filter_dict['Purchased'] = True
        else:
            filter_dict.pop('Purchased', None)
        if not_obsolete:
            filter_dict['Obsolete'] = False
        else:
            filter_dict.pop('Obsolete', None)

        self.editable_table.search(filter_dict, global_search=search_text)
        # self.control_frame.reset_entry_search()

    def reset_search(self) -> None:
        """
        Reset the search controls to their default values
        """
        self.control_frame.var_global_search.set(gui_g.s.default_global_search)
        self.control_frame.var_category.set(gui_g.s.default_category_for_all)
        gui_g.UEVM_filter_category = ''
        self.do_not_launch_search = True  # Prevent the search to be launched when the checkbuttons are changed
        self.control_frame.var_is_purchased.set(False)
        self.control_frame.var_is_not_obsolete.set(False)
        self.do_not_launch_search = False
        self.editable_table.reset_search()

    def toggle_pagination(self, forced_value=None) -> None:
        """
        Toggle pagination. Will change the navigation buttons states when pagination is changed
        :param forced_value: if not None, will force the pagination to the given value
        """
        if forced_value is not None:
            self.editable_table.pagination_enabled = forced_value
        else:
            self.editable_table.pagination_enabled = not self.editable_table.pagination_enabled
        self.editable_table.show_page()
        if not self.editable_table.pagination_enabled:
            # Disable prev/next buttons when pagination is disabled
            self.toolbar_frame.btn_first_page.config(state=tk.DISABLED)
            self.toolbar_frame.btn_prev_page.config(state=tk.DISABLED)
            self.toolbar_frame.btn_next_page.config(state=tk.DISABLED)
            self.toolbar_frame.btn_last_page.config(state=tk.DISABLED)
            self.toolbar_frame.entry_page_num.config(state=tk.DISABLED)
            self.toolbar_frame.btn_toggle_pagination.config(text='Enable  Pagination')
        else:
            self.update_page_numbers()  # will also update buttons status
            self.toolbar_frame.btn_toggle_pagination.config(text='Disable Pagination')

    def show_first_page(self) -> None:
        """
        Show the first page of the table
        """
        self.editable_table.first_page()
        self.update_page_numbers()

    def show_prev_page(self) -> None:
        """
        Show the previous page of the table
        """
        self.editable_table.prev_page()
        self.update_page_numbers()

    def show_next_page(self) -> None:
        """
        Show the next page of the table
        """
        self.editable_table.next_page()
        self.update_page_numbers()

    def show_last_page(self) -> None:
        """
        Show the last page of the table
        """
        self.editable_table.last_page()
        self.update_page_numbers()

    def prev_asset(self) -> None:
        """
        Move to the previous asset in the table
        """
        self.editable_table.move_to_prev_record()

    def next_asset(self) -> None:
        """
        Move to the next asset in the table
        """
        self.editable_table.move_to_next_record()

    def toggle_controls_pane(self) -> None:
        """
        Toggle the visibility of the controls on the right side of the table
        """
        # Toggle visibility of filter controls frame
        if self.control_frame.winfo_ismapped():
            self.control_frame.pack_forget()
            self.toolbar_frame.btn_toggle_controls.config(text='Show Control')
        else:
            self.control_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
            self.toolbar_frame.btn_toggle_controls.config(text='Hide Control')

    def update_page_numbers(self) -> None:
        """
        Update the page numbers in the toolbar
        """
        page_num = self.editable_table.current_page + 1
        self.toolbar_frame.entry_page_num_var.set(page_num)
        self.toolbar_frame.lbl_page_count.config(text=f' / {self.editable_table.total_pages}')
        # enable all buttons by default
        self.toolbar_frame.btn_first_page.config(state=tk.NORMAL)
        self.toolbar_frame.btn_prev_page.config(state=tk.NORMAL)
        self.toolbar_frame.btn_next_page.config(state=tk.NORMAL)
        self.toolbar_frame.btn_last_page.config(state=tk.NORMAL)

        if not self.editable_table.pagination_enabled:
            self.toolbar_frame.entry_page_num.config(state=tk.NORMAL)
        if page_num == 1:
            self.toolbar_frame.btn_first_page.config(state=tk.DISABLED)
            self.toolbar_frame.btn_prev_page.config(state=tk.DISABLED)
        elif page_num == self.editable_table.total_pages:
            self.toolbar_frame.btn_next_page.config(state=tk.DISABLED)
            self.toolbar_frame.btn_last_page.config(state=tk.DISABLED)

    def update_file_name(self) -> None:
        """
        Update the file name in the control frame
        """
        filename = self.editable_table.file
        self.control_frame.entry_file_name_var.set(filename)

    def reload_data(self) -> None:
        """
        Reload the data from the file
        """
        if self.editable_table.must_save:
            if gui_f.box_yesno('Changes have been made, they will be lost. Are you sure you want to continue ?'):
                self.editable_table.reload_data()
                gui_f.box_message(f'Data Reloaded from {self.editable_table.file}')
                self.update_page_numbers()

    def rebuild_data(self) -> None:
        """
        Rebuild the data from the file. Will ask for confirmation before rebuilding
        """
        if gui_f.box_yesno(
            f'The process will change the content of the windows and the {self.editable_table.file} file.\nAre you sure you want to continue ?'
        ):
            if self.editable_table.rebuild_data():
                gui_f.box_message(f'Data rebuilt from {self.editable_table.file}')
                self.update_page_numbers()
