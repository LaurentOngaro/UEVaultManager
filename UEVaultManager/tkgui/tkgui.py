"""
working file for the GUI integration in UEVaultManager

Bugs to confirm:

Bugs to fix:

To Do:
- use image cache for the preview image in row edit window
- add pagination info in a new frame. See tk_table_filter_ex.py
- add more info about the current row (at least comment, review...) in the preview frame
- check the TODOs
- add features and buttons to refresh csv file by calling UEVaultManager cli
- in edit_row_window, implement the prev and next buttons
- save and load for tcsv files
- save and load for json files
- migrate the code into the UEVaultManager code base
- document the new features
- update the PyPi package

"""
import time
import requests
from io import BytesIO
from tkinter import filedialog as fd, filedialog, messagebox
from tkinter.messagebox import showwarning
from screeninfo import get_monitors
from UEVaultManager.tkgui.modules.EditableTableClass import *
from UEVaultManager.tkgui.modules.functions import *


class AppWindow(tk.Tk):

    def __init__(self, title: str, width: int, height: int, icon: str, file: str, screen_index=0):
        super().__init__()

        self.title(title)

        monitors = get_monitors()
        if screen_index > len(monitors):
            log_warning(f'The screen #{screen_index} is not available. Using 0 as screen index.')
            screen_index = 0

        log_info(f'The app is displayed is the center of the screen #{screen_index}.')

        # Position the window in the center of the screen
        target_screen = monitors[screen_index]
        screen_width = target_screen.width
        screen_height = target_screen.height
        x = target_screen.x + (screen_width-width) // 2
        y = target_screen.y + (screen_height-height) // 2
        geometry: str = f'{width}x{height}+{x}+{y}'
        self.geometry(geometry)

        if icon != '' and os.path.isfile(icon):
            self.iconbitmap(icon)

        self.resizable(True, False)
        self.editable_table = None

        # Create frames
        pack_def_options = {'ipadx': 5, 'ipady': 5, 'padx': 3, 'pady': 3}
        table_frame = self.TableFrame(self)
        self.editable_table = EditableTable(container_frame=table_frame, file=file, fontsize=table_font_size)

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
        self.editable_table.bind('<Motion>', self.mouse_over_cell)
        # Bind the table to the mouse leave event
        self.editable_table.bind('<Leave>', self.mouse_leave_cell)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    class ToolbarFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__()
            pack_def_options = {'ipadx': 2, 'ipady': 2, 'fill': tk.BOTH, 'expand': False}
            lblf_def_options = {'ipadx': 1, 'ipady': 1, 'expand': False}

            lblf_pages = ttk.LabelFrame(self, text='Pagination')
            lblf_pages.pack(side=tk.LEFT, **lblf_def_options)
            btn_toggle_pagination = ttk.Button(lblf_pages, text='Toggle Pagination', command=container.toggle_pagination)
            btn_toggle_pagination.pack(**pack_def_options, side=tk.LEFT)
            btn_first_page = ttk.Button(lblf_pages, text='First Page', command=container.editable_table.first_page)
            btn_first_page.pack(**pack_def_options, side=tk.LEFT)
            btn_prev_page = ttk.Button(lblf_pages, text='Prev Page', command=container.editable_table.prev_page)
            btn_prev_page.pack(**pack_def_options, side=tk.LEFT)
            btn_next_page = ttk.Button(lblf_pages, text='Next Page', command=container.editable_table.next_page)
            btn_next_page.pack(**pack_def_options, side=tk.LEFT)
            btn_last_page = ttk.Button(lblf_pages, text='Last Page', command=container.editable_table.last_page)
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

            lblf_options = ttk.LabelFrame(self, text='Options')
            lblf_options.pack(side=tk.RIGHT, **lblf_def_options)
            btn_on_close = ttk.Button(lblf_options, text='Quit', command=container.on_close)
            btn_on_close.pack(**pack_def_options, side=tk.RIGHT)
            btn_toggle_controls = ttk.Button(lblf_options, text="Hide Controls", command=container.toggle_filter_controls)
            btn_toggle_controls.pack(**pack_def_options, side=tk.RIGHT)

            # store the buttons that need to be disabled when the pagination is disabled
            self.btn_first_page = btn_first_page
            self.btn_prev_page = btn_prev_page
            self.btn_next_page = btn_next_page
            self.btn_last_page = btn_last_page
            self.btn_toggle_controls = btn_toggle_controls

    class TableFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__(container)

    class ControlFrame(ttk.Frame):
        # delete the temporary text in filter value entry
        def reset_entry_search(self, _event=None):
            self.entry_search.delete(0, 'end')
            self.entry_search.insert(0, default_search_text)

        def del_entry_search(self, _event=None):
            self.entry_search.delete(0, 'end')

        def __init__(self, container):
            super().__init__()

            pack_def_options = {'ipadx': 2, 'ipady': 2, 'fill': tk.BOTH, 'expand': False}
            grid_def_options = {'ipadx': 2, 'ipady': 2, 'sticky': tk.NW}
            lblf_def_options = {'ipadx': 1, 'ipady': 1, 'padx': 0, 'pady': 0, 'fill': tk.BOTH, 'expand': False}

            lblf_content = ttk.LabelFrame(self, text='Content')
            lblf_content.pack(**lblf_def_options)
            btn_edit_row = ttk.Button(lblf_content, text='Edit Row', command=container.editable_table.edit_record)
            btn_edit_row.pack(**pack_def_options, side=tk.LEFT)
            btn_reload_data = ttk.Button(lblf_content, text='Reload Content', command=container.editable_table.reload_data)
            btn_reload_data.pack(**pack_def_options, side=tk.LEFT)

            lbf_filter_cat = ttk.LabelFrame(self, text="Search and Filter")
            lbf_filter_cat.pack(fill=tk.X, anchor=tk.NW, ipadx=5, ipady=5)
            categories = list(container.editable_table.data['Category'].cat.categories)
            var_category = tk.StringVar(value=categories[0])
            categories.insert(0, default_category_for_all)
            opt_category = ttk.Combobox(lbf_filter_cat, textvariable=var_category, values=categories)
            opt_category.grid(row=0, column=0, **grid_def_options)
            var_search = tk.StringVar(value=default_search_text)
            entry_search = ttk.Entry(lbf_filter_cat, textvariable=var_search)
            entry_search.grid(row=0, column=1, **grid_def_options)
            entry_search.bind("<FocusIn>", self.del_entry_search)

            btn_filter_by_text = ttk.Button(lbf_filter_cat, text='Search', command=container.search)
            btn_filter_by_text.grid(row=1, column=0, **grid_def_options)
            btn_reset_search = ttk.Button(lbf_filter_cat, text='Reset', command=container.reset_search)
            btn_reset_search.grid(row=1, column=1, **grid_def_options)

            lblf_files = ttk.LabelFrame(self, text='Files')
            lblf_files.pack(**lblf_def_options)
            btn_save_change = ttk.Button(lblf_files, text='Save to File', command=container.save_change)
            btn_save_change.pack(**pack_def_options, side=tk.LEFT)
            btn_export_button = ttk.Button(lblf_files, text='Export Selection', command=container.export_selection)
            btn_export_button.pack(**pack_def_options, side=tk.LEFT)
            btn_select_file = ttk.Button(lblf_files, text='Load a file', command=container.select_file)
            btn_select_file.pack(**pack_def_options, side=tk.LEFT)

            # Create a Canvas to preview the asset image
            lbf_preview = ttk.LabelFrame(self, text="Image Preview")
            lbf_preview.pack(**lblf_def_options, anchor=tk.SW)
            canvas_preview = tk.Canvas(lbf_preview, width=preview_max_width, height=preview_max_height, highlightthickness=0)
            canvas_preview.pack()
            canvas_preview.create_rectangle((0, 0), (preview_max_width, preview_max_height), fill='black')

            lblf_bottom = ttk.Frame(self)
            lblf_bottom.pack(**lblf_def_options)
            ttk.Sizegrip(lblf_bottom).pack(side=tk.RIGHT)

            # store the controls that need to be accessible outside the class
            self.entry_search = entry_search
            self.var_category = var_category
            self.var_search = var_search
            self.canvas_preview = canvas_preview

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
            showinfo(title=app_title, message=f'The file {filename} as been read')
            self.editable_table.file = filename
            self.editable_table.load_data()
            self.editable_table.show_page(0)

    def search(self):
        search_text = self.control_frame.var_search.get()
        category = self.control_frame.var_category.get()
        if search_text == default_search_text and category == default_category_for_all:
            return
        self.toggle_pagination(forced_value=False)
        self.editable_table.search(search_text=search_text, category=category)
        self.control_frame.reset_entry_search()

    def reset_search(self):
        self.control_frame.var_search.set(default_search_text)
        self.control_frame.var_category.set(default_category_for_all)
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
        else:
            # Enable prev/next buttons when pagination is enabled
            self.toolbar_frame.btn_first_page.config(state=tk.NORMAL)
            self.toolbar_frame.btn_prev_page.config(state=tk.NORMAL)
            self.toolbar_frame.btn_next_page.config(state=tk.NORMAL)
            self.toolbar_frame.btn_last_page.config(state=tk.NORMAL)

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
                showinfo(title=app_title, message=f'Selected rows exported to "{file_name}"')
            else:
                showwarning(title=app_title, message='No file has been selected')
        else:
            showwarning(title=app_title, message='Select at least one row first')

    # noinspection DuplicatedCode
    def mouse_over_cell(self, event=None):
        if event is None:
            return
        # Get the row and column index of the cell under the mouse pointer
        row, col = self.editable_table.get_row_clicked(event), self.editable_table.get_col_clicked(event)
        if row is None or col is None or row >= len(self.editable_table.data):
            return
        col = self.editable_table.model.df.columns.get_loc('Image')
        if col:
            img_url = self.editable_table.model.getValueAt(row, col)
            self.show_asset_image(img_url)
        else:
            self.show_default_image()

    def mouse_leave_cell(self, _event=None):
        self.show_default_image()

    def show_asset_image(self, img_url):
        try:
            # noinspection DuplicatedCode
            if not os.path.isdir(cache_folder):
                os.mkdir(cache_folder)

            image_filename = os.path.join(cache_folder, os.path.basename(img_url))

            # Check if the image is already cached
            if os.path.isfile(image_filename) and (time.time() - os.path.getmtime(image_filename)) < cache_max_time:
                # Load the image from the cache folder
                image = Image.open(image_filename)
            else:
                response = requests.get(img_url)
                image = Image.open(BytesIO(response.content))

                with open(image_filename, "wb") as f:
                    f.write(response.content)

            # Calculate new dimensions while maintaining the aspect ratio
            width_ratio = preview_max_width / float(image.width)
            height_ratio = preview_max_height / float(image.height)
            ratio = min(width_ratio, height_ratio, 1)
            new_width = min(int(image.width * ratio), preview_max_width)
            new_height = min(int(image.height * ratio), preview_max_height)
            log_debug(f'Image size: {image.width}x{image.height} -> {new_width}x{new_height} ratio: {ratio}')
            # noinspection PyTypeChecker
            resize_and_show_image(image, self.control_frame.canvas_preview, new_height, new_width)

        except Exception as error:
            log_error(f"Error showing image: {error}")

    def show_default_image(self, _event=None):
        try:
            # Load the default image
            if os.path.isfile(default_image_filename):
                def_image = Image.open(default_image_filename)
                # noinspection PyTypeChecker
                resize_and_show_image(def_image, self.control_frame.canvas_preview, preview_max_width, preview_max_height)
        except Exception as error:
            log_warning(f"Error showing default image {default_image_filename} cwd:{os.getcwd()}: {error}")


if __name__ == '__main__':
    app_icon_filename = path_from_relative_to_absolute(app_icon_filename)
    csv_filename = path_from_relative_to_absolute(csv_filename)

    main = AppWindow(title=app_title, width=app_width, height=app_height, icon=app_icon_filename, file=csv_filename)
    main.mainloop()
