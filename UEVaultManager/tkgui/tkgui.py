"""
working file for the GUI integration in UEVaultManager

Bugs to confirm:

Bugs to fix:
- the url column is nan

To Do:
- add features and buttons to refresh csv file by calling UEVaultManager cli (WIP)
- integrate the code into the UEVaultManager code base (WIP)
- add more info about the current row (at least comment, review...) in the preview frame
- edit users fields (comment, alternative...) in the main windows (in the preview frame ?)
- save and load for tcsv files
- save and load for json files
- document the new features
- update the PyPi package

"""
import os
import tkinter as tk
from tkinter import filedialog as fd, filedialog, ttk, messagebox
import UEVaultManager.tkgui.modules.functions as f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.EditableTableClass import EditableTable


class UEVMGui(tk.Tk):

    def __init__(self, title: str, width=1200, height=800, icon='', screen_index=0, file=''):
        super().__init__()
        self.title(title)

        geometry = f.center_window_on_screen(screen_index, height, width)
        self.geometry(geometry)

        if icon != '' and os.path.isfile(icon):
            self.iconbitmap(icon)

        self.resizable(True, False)
        self.editable_table = None

        pack_def_options = {'ipadx': 5, 'ipady': 5, 'padx': 3, 'pady': 3}
        table_frame = self.TableFrame(self)
        self.editable_table = EditableTable(container_frame=table_frame, file=file, fontsize=g.s.table_font_size)

        self.editable_table.show()
        self.editable_table.show_page(0)
        self.table_frame = table_frame
        toolbar_frame = self.ToolbarFrame(self)
        self.toolbar_frame = toolbar_frame
        control_frame = self.ControlFrame(self)
        self.control_frame = control_frame

        # Pack the frames with the appropriate side option
        toolbar_frame.pack(**pack_def_options, fill=tk.X, side=tk.TOP, anchor=tk.NW)
        table_frame.pack(**pack_def_options, fill=tk.BOTH, side=tk.LEFT, anchor=tk.NW, expand=True)
        control_frame.pack(**pack_def_options, fill=tk.BOTH, side=tk.RIGHT, anchor=tk.NW)

        self.bind('<Key>', self.on_key_press)
        # Bind the table to the mouse motion event
        self.editable_table.bind('<Motion>', self.on_mouse_over_cell)
        # Bind the table to the mouse leave event
        self.editable_table.bind('<Leave>', self.on_mouse_leave_cell)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    class ToolbarFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__()
            pack_def_options = {'ipadx': 2, 'ipady': 2, 'fill': tk.BOTH, 'expand': False}
            lblf_def_options = {'ipadx': 1, 'ipady': 1, 'expand': False}

            lblf_pages = ttk.LabelFrame(self, text='Pagination')
            lblf_pages.pack(side=tk.LEFT, **lblf_def_options)
            btn_toggle_pagination = ttk.Button(lblf_pages, text='Disable Pagination', command=container.toggle_pagination)
            btn_toggle_pagination.pack(**pack_def_options, side=tk.LEFT)
            btn_first_page = ttk.Button(lblf_pages, text='First Page', command=container.show_first_page)
            btn_first_page.pack(**pack_def_options, side=tk.LEFT)
            btn_first_page.config(state=tk.DISABLED)
            btn_prev_page = ttk.Button(lblf_pages, text='Prev Page', command=container.show_prev_page)
            btn_prev_page.pack(**pack_def_options, side=tk.LEFT)
            btn_prev_page.config(state=tk.DISABLED)
            entry_page_num_var = tk.StringVar(value=container.editable_table.current_page + 1)
            entry_page_num = ttk.Entry(lblf_pages, width=5, justify=tk.CENTER, textvariable=entry_page_num_var)
            entry_page_num.pack(**pack_def_options, side=tk.LEFT)
            lbl_page_count = ttk.Label(lblf_pages, text=f' / {container.editable_table.total_pages}')
            lbl_page_count.pack(**pack_def_options, side=tk.LEFT)
            btn_next_page = ttk.Button(lblf_pages, text='Next Page', command=container.show_next_page)
            btn_next_page.pack(**pack_def_options, side=tk.LEFT)
            btn_last_page = ttk.Button(lblf_pages, text='Last Page', command=container.show_last_page)
            btn_last_page.pack(**pack_def_options, side=tk.LEFT)

            lblf_display = ttk.LabelFrame(self, text='Display')
            lblf_display.pack(side=tk.LEFT, **lblf_def_options)
            btn_expand = ttk.Button(lblf_display, text='Expand Cols', command=container.editable_table.expand_columns)
            btn_expand.pack(**pack_def_options, side=tk.LEFT)
            btn_shrink = ttk.Button(lblf_display, text='Shrink Cols', command=container.editable_table.contract_columns)
            btn_shrink.pack(**pack_def_options, side=tk.LEFT)
            btn_autofit = ttk.Button(lblf_display, text="Autofit Cols", command=container.editable_table.autofit_columns)
            btn_autofit.pack(**pack_def_options, side=tk.LEFT)
            btn_zoom_in = ttk.Button(lblf_display, text="Zoom In", command=container.editable_table.zoom_in)
            btn_zoom_in.pack(**pack_def_options, side=tk.LEFT)
            btn_zoom_out = ttk.Button(lblf_display, text="Zoom Out", command=container.editable_table.zoom_out)
            btn_zoom_out.pack(**pack_def_options, side=tk.LEFT)

            lblf_actions = ttk.LabelFrame(self, text='Actions')
            lblf_actions.pack(side=tk.RIGHT, **lblf_def_options)
            btn_on_close = ttk.Button(lblf_actions, text='Quit', command=container.on_close)
            btn_on_close.pack(**pack_def_options, side=tk.RIGHT)
            btn_toggle_controls = ttk.Button(lblf_actions, text="Hide Controls", command=container.toggle_filter_controls)
            btn_toggle_controls.pack(**pack_def_options, side=tk.RIGHT)

            # Bind events for the Entry widget
            entry_page_num.bind("<FocusOut>", container.on_entry_page_num_changed)
            entry_page_num.bind("<Return>", container.on_entry_page_num_changed)

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

        def __init__(self, container):
            super().__init__(container)

    class ControlFrame(ttk.Frame):
        # delete the temporary text in filter value entry
        def reset_entry_search(self, _event=None):
            self.entry_search.delete(0, 'end')
            self.entry_search.insert(0, g.s.default_search_text)

        def del_entry_search(self, _event=None):
            self.entry_search.delete(0, 'end')

        def __init__(self, container):
            super().__init__()

            grid_def_options = {'ipadx': 2, 'ipady': 2, 'sticky': tk.NW}
            lblf_def_options = {'ipadx': 1, 'ipady': 1, 'padx': 0, 'pady': 0, 'fill': tk.BOTH, 'expand': False}

            lblf_content = ttk.LabelFrame(self, text='Content')
            lblf_content.pack(**lblf_def_options)
            btn_edit_row = ttk.Button(lblf_content, text='Edit Row', command=container.editable_table.edit_record)
            btn_edit_row.grid(row=0, column=0, **grid_def_options)
            btn_reload_data = ttk.Button(lblf_content, text='Reload File Content', command=container.editable_table.reload_data)
            btn_reload_data.grid(row=0, column=1, **grid_def_options)
            btn_rebuild_file = ttk.Button(lblf_content, text='Rebuild File Content', command=container.editable_table.rebuild_data)
            btn_rebuild_file.grid(row=0, column=2, **grid_def_options)

            lbf_filter_cat = ttk.LabelFrame(self, text="Search and Filter")
            lbf_filter_cat.pack(fill=tk.X, anchor=tk.NW, ipadx=5, ipady=5)
            categories = list(container.editable_table.data['Category'].cat.categories)
            var_category = tk.StringVar(value=categories[0])
            categories.insert(0, g.s.default_category_for_all)
            opt_category = ttk.Combobox(lbf_filter_cat, textvariable=var_category, values=categories)
            opt_category.grid(row=0, column=0, **grid_def_options)
            var_search = tk.StringVar(value=g.s.default_search_text)
            entry_search = ttk.Entry(lbf_filter_cat, textvariable=var_search)
            entry_search.grid(row=0, column=1, **grid_def_options)
            entry_search.bind("<FocusIn>", self.del_entry_search)

            btn_filter_by_text = ttk.Button(lbf_filter_cat, text='Search', command=container.search)
            btn_filter_by_text.grid(row=1, column=0, **grid_def_options)
            btn_reset_search = ttk.Button(lbf_filter_cat, text='Reset', command=container.reset_search)
            btn_reset_search.grid(row=1, column=1, **grid_def_options)

            lblf_files = ttk.LabelFrame(self, text='Files')
            lblf_files.pack(**lblf_def_options)
            lbl_file_name = ttk.Label(lblf_files, text='Current File: ')
            lbl_file_name.grid(row=0, column=0, columnspan=3, **grid_def_options)
            entry_file_name_var = tk.StringVar(value=container.editable_table.file)
            entry_file_name = ttk.Entry(lblf_files, textvariable=entry_file_name_var, state='readonly')
            entry_file_name.grid(row=1, column=0, columnspan=3, **grid_def_options)
            btn_save_change = ttk.Button(lblf_files, text='Save to File', command=container.save_change)
            btn_save_change.grid(row=2, column=0, **grid_def_options)
            btn_export_button = ttk.Button(lblf_files, text='Export Selection', command=container.export_selection)
            btn_export_button.grid(row=2, column=1, **grid_def_options)
            btn_select_file = ttk.Button(lblf_files, text='Load a file', command=container.select_file)
            btn_select_file.grid(row=2, column=2, **grid_def_options)

            # Create a Canvas to preview the asset image
            lbf_preview = ttk.LabelFrame(self, text="Image Preview")
            lbf_preview.pack(**lblf_def_options, anchor=tk.SW)
            canvas_preview = tk.Canvas(lbf_preview, width=g.s.preview_max_width, height=g.s.preview_max_height, highlightthickness=0)
            canvas_preview.pack()
            canvas_preview.create_rectangle((0, 0), (g.s.preview_max_width, g.s.preview_max_height), fill='black')

            lblf_bottom = ttk.Frame(self)
            lblf_bottom.pack(**lblf_def_options)
            ttk.Sizegrip(lblf_bottom).pack(side=tk.RIGHT)

            # store the controls that need to be accessible outside the class
            self.entry_search = entry_search
            self.var_category = var_category
            self.var_search = var_search
            self.canvas_preview = canvas_preview
            self.entry_file_name_var = entry_file_name_var

    def on_close(self):
        if self.editable_table.must_save:
            if messagebox.askokcancel('Exit the application', 'Changes have been made. Do you want to save them in the source file ?'):
                self.save_change()
        self.quit()

    def save_change(self):
        self.editable_table.save_data()

    def on_key_press(self, event):
        if event.keysym == 'Escape':
            if g.edit_cell_window_ref:
                g.edit_cell_window_ref.destroy()
                g.edit_cell_window_ref = None
            elif g.edit_row_window_ref:
                g.edit_row_window_ref.destroy()
                g.edit_row_window_ref = None
            else:
                self.on_close()
        elif event.keysym == 'Return':
            self.editable_table.edit_record()

    def select_file(self):
        filetypes = (('csv file', '*.csv'), ('tcsv file', '*.tcsv'), ('json file', '*.json'), ('text file', '*.txt'))

        filename = fd.askopenfilename(title='Choose a file to open', initialdir='./', filetypes=filetypes)
        if filename and os.path.isfile(filename):
            messagebox.showinfo(title=g.s.app_title, message=f'The file {filename} as been read')
            self.editable_table.file = filename
            self.editable_table.load_data()
            self.editable_table.show_page(0)

    def search(self):
        search_text = self.control_frame.var_search.get()
        category = self.control_frame.var_category.get()
        if search_text == g.s.default_search_text and category == g.s.default_category_for_all:
            return
        self.toggle_pagination(forced_value=False)
        self.editable_table.search(search_text=search_text, category=category)
        self.control_frame.reset_entry_search()

    def reset_search(self):
        self.control_frame.var_search.set(g.s.default_search_text)
        self.control_frame.var_category.set(g.s.default_category_for_all)
        self.editable_table.reset_search()

    def toggle_pagination(self, forced_value=None):
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
            self.toolbar_frame.btn_toggle_pagination.config(text="Enable  Pagination")
        else:
            self.update_page_numbers()  # will also update buttons status
            self.toolbar_frame.btn_toggle_pagination.config(text="Disable Pagination")

    def show_first_page(self):
        self.editable_table.first_page()
        self.update_page_numbers()

    def show_prev_page(self):
        self.editable_table.prev_page()
        self.update_page_numbers()

    def show_next_page(self):
        self.editable_table.next_page()
        self.update_page_numbers()

    def show_last_page(self):
        self.editable_table.last_page()
        self.update_page_numbers()

    def toggle_filter_controls(self):
        # Toggle visibility of filter controls frame
        if self.control_frame.winfo_ismapped():
            self.control_frame.pack_forget()
            self.toolbar_frame.btn_toggle_controls.config(text="Show Control")
        else:
            self.control_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
            self.toolbar_frame.btn_toggle_controls.config(text="Hide Control")

    def export_selection(self):
        # Get selected row indices
        selected_row_indices = self.editable_table.multiplerowlist

        if selected_row_indices:
            # Get selected rows from filtered DataFrame
            selected_rows = self.editable_table.data_filtered.iloc[selected_row_indices]

            # Open file dialog to select file to save exported rows
            file_name = filedialog.asksaveasfilename(
                defaultextension=".csv",
                initialfile="export.csv",
                initialdir=os.path.dirname(self.editable_table.file),
                filetypes=[("CSV files", "*.csv")]
            )

            if file_name:
                # Export selected rows to the specified CSV file
                selected_rows.to_csv(file_name, index=False)
                messagebox.showinfo(title=g.s.app_title, message=f'Selected rows exported to "{file_name}"')
            else:
                messagebox.showwarning(title=g.s.app_title, message='No file has been selected')
        else:
            messagebox.showwarning(title=g.s.app_title, message='Select at least one row first')

    # noinspection DuplicatedCode
    def on_mouse_over_cell(self, event=None):
        if event is None:
            return
        # Get the row and column index of the cell under the mouse pointer
        row, col = self.editable_table.get_row_clicked(event), self.editable_table.get_col_clicked(event)
        if row is None or col is None or row >= len(self.editable_table.data):
            return
        col = self.editable_table.model.df.columns.get_loc('Image')
        if col:
            image_url = self.editable_table.model.getValueAt(row, col)
            f.show_asset_image(image_url=image_url, canvas_preview=self.control_frame.canvas_preview)
        else:
            f.show_default_image(canvas_preview=self.control_frame.canvas_preview)

    def on_mouse_leave_cell(self, _event=None):
        f.show_default_image(canvas_preview=self.control_frame.canvas_preview)

    def on_entry_page_num_changed(self, _event=None):
        page_num = 0
        try:
            page_num = self.toolbar_frame.entry_page_num.get()
            page_num = int(page_num)
            page_num -= 1
            f.log_debug(f'showing page {page_num}')
            self.editable_table.show_page(page_num)
        except (ValueError, UnboundLocalError) as error:
            f.log_error(f'could not convert page number {page_num} to int. Error {error!r}')

    def update_page_numbers(self):
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

    def update_file_name(self):
        filename = self.editable_table.file
        self.control_frame.entry_file_name_var.set(filename)


if __name__ == '__main__':
    app_icon_filename = f.path_from_relative_to_absolute(g.s.app_icon_filename)
    csv_filename = f.path_from_relative_to_absolute(g.s.csv_filename)
    main = UEVMGui(title=g.s.app_title, width=g.s.app_width, height=g.s.app_height, icon=app_icon_filename, screen_index=0, file=csv_filename)
    main.mainloop()
