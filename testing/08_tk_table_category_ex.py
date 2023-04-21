import os
import tkinter as tk
import time
from tkinter import ttk

import pandas as pd
from pandastable import Table
from PIL import Image, ImageTk
import requests
from io import BytesIO

file = '../results/list.csv'
cache_folder = "../cache"
cache_max_time = 60 * 60 * 24 * 15  # 15 days
default_image_filename = '../UEVaultManager/assets/UEVM_200x200.png'
max_width = 150
max_height = 150


def resize_and_show_image(image, canvas, new_height, new_width):
    image = image.resize((new_width, new_height), Image.LANCZOS)
    canvas.config(width=new_width, height=new_height)
    canvas.image = ImageTk.PhotoImage(image)
    canvas.create_image(0, 0, anchor=tk.NW, image=canvas.image)


class EditableTable(ttk.Frame):
    # noinspection DuplicatedCode
    def mouse_over_cell(self, event):
        # Get the row and column index of the cell under the mouse pointer
        row, col = self.table.get_row_clicked(event), self.table.get_col_clicked(event)

        # Check if the mouse is over the "img_url" column
        if self.table.model.df.columns[col] == 'Image':
            # Get the image URL
            img_url = self.table.model.getValueAt(row, col)

            # Show the image
            self.show_asset_image(img_url)
        else:
            # Show the default
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
            width_ratio = max_width / float(image.width)
            height_ratio = max_height / float(image.height)
            ratio = min(width_ratio, height_ratio, 1)
            new_width = min(int(image.width * ratio), max_width)
            new_height = min(int(image.height * ratio), max_height)
            print(f"Image size: {image.width}x{image.height} -> {new_width}x{new_height} ratio: {ratio}")
            # noinspection PyTypeChecker
            resize_and_show_image(image, self.canvas_preview, new_height, new_width)

        except Exception as e:
            print(f"Error showing image: {e}")

    def show_default_image(self):
        try:
            # Load the default image
            if os.path.isfile(default_image_filename):
                def_image = Image.open(default_image_filename)
                # noinspection PyTypeChecker
                resize_and_show_image(def_image, self.canvas_preview, max_width, max_height)
        except Exception as e:
            print(f"Error showing default image {default_image_filename} cwd:{os.getcwd()}: {e}")

    def __init__(self, container):
        ttk.Frame.__init__(self, container)
        container.geometry('1200x880')
        container.title('Table app')
        self.current_page = 0
        self.rows_per_page = 35
        self.pagination_enabled = True

        # Load data from CSV file
        self.data = pd.read_csv(file)

        # Convert Category column to category dtype
        self.data['Category'] = self.data['Category'].astype('category')

        # Initialize filtered DataFrame
        self.data_filtered = self.data

        # Create frames
        toolbar_frame = ttk.Frame(container)
        table_frame = ttk.Frame(container)
        control_frame = ttk.Frame(container)
        # Pack the frames with the appropriate side option
        toolbar_frame.pack(fill=tk.X, side=tk.TOP, anchor=tk.NW, ipadx=5, ipady=5)
        table_frame.pack(fill=tk.BOTH, side=tk.LEFT, anchor=tk.NW, ipadx=5, ipady=5, expand=True)
        control_frame.pack(fill=tk.BOTH, side=tk.RIGHT, anchor=tk.NW, ipadx=5, ipady=5)

        # Create table to display data
        self.table = Table(table_frame, dataframe=self.data.iloc[0:0], showtoolbar=True, showstatusbar=True)
        self.table.show()

        # Bind the table to the mouse motion event
        self.table.bind('<Motion>', self.mouse_over_cell)

        # Bind the table to the mouse leave event
        self.table.bind('<Leave>', self.show_default_image)

        # Add pagination controls
        prev_button = ttk.Button(toolbar_frame, text="<<", command=self.prev_page)
        prev_button.pack(side=tk.LEFT)
        next_button = ttk.Button(toolbar_frame, text=">>", command=self.next_page)
        next_button.pack(side=tk.LEFT)
        # Create button to toggle filter controls visibility
        btn_toggle_controls = ttk.Button(toolbar_frame, text="Hide Controls", command=self.toggle_filter_controls)
        btn_toggle_controls.pack(side=tk.RIGHT)

        # Add controls for filtering by category
        lbf_filter_cat = ttk.LabelFrame(control_frame, text="Category")
        lbf_filter_cat.pack(fill=tk.X, anchor=tk.NW, ipadx=5, ipady=5)
        category_options = list(self.data['Category'].cat.categories)
        var_category = tk.StringVar(value=category_options[0])
        category_menu = tk.OptionMenu(lbf_filter_cat, var_category, *category_options, command=self.filter_by_category)
        category_menu.pack(side=tk.TOP)

        # Add search box and button
        lbf_search = ttk.LabelFrame(control_frame, text="Search by text")
        lbf_search.pack(fill=tk.X, anchor=tk.NW, ipadx=5, ipady=5)
        var_search = tk.StringVar()
        search_entry = ttk.Entry(lbf_search, textvariable=var_search)
        search_entry.pack(side=tk.LEFT)
        search_button = ttk.Button(lbf_search, text="Search", command=self.search)
        search_button.pack(side=tk.RIGHT)

        # Create a Canvas to display the image
        lbf_preview = ttk.LabelFrame(control_frame, text="Image Preview")
        lbf_preview.pack(fill=tk.X, anchor=tk.SW, ipadx=5, ipady=5)
        canvas_preview = tk.Canvas(lbf_preview, width=max_width, height=max_height, highlightthickness=0)
        canvas_preview.pack()
        canvas_preview.create_rectangle((0, 0), (max_width, max_height), fill='black')

        self.control_frame = control_frame
        self.btn_toggle_controls = btn_toggle_controls
        self.var_category = var_category
        self.var_search = var_search
        self.canvas_preview = canvas_preview

        self.show_default_image()

        # Update table with data for current page
        self.update_table()

    def toggle_filter_controls(self):
        # Toggle visibility of filter controls frame
        if self.control_frame.winfo_ismapped():
            self.control_frame.pack_forget()
            self.btn_toggle_controls.config(text="Show Control")
        else:
            self.control_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
            self.btn_toggle_controls.config(text="Hide Control")

    def update_table(self):
        # Calculate start and end row for current page
        start_row = self.current_page * self.rows_per_page
        end_row = start_row + self.rows_per_page

        # Update table with data for current page
        self.table.model.df = self.data_filtered.iloc[start_row:end_row]
        self.table.redraw()

    def filter_by_category(self, category):
        # Filter dataframe by selected category
        self.data_filtered = self.data[self.data['Category'] == category]

        # Apply search filter if search box is not empty
        search_value = self.var_search.get()
        if search_value:
            self.data_filtered = self.data_filtered[self.data_filtered.apply(lambda row: search_value.lower() in str(row).lower(), axis=1)]

        # Reset current page to 0
        self.current_page = 0

        # Update table with filtered data for current page
        self.update_table()

    def search(self):
        # Filter dataframe by search value
        search_value = self.var_search.get()
        self.data_filtered = self.data[self.data['Category'] == self.var_category.get()]
        self.data_filtered = self.data_filtered[self.data_filtered.apply(lambda row: search_value.lower() in str(row).lower(), axis=1)]

        # Reset current page to 0
        self.current_page = 0

        # Update table with filtered data for current page
        self.update_table()

    def prev_page(self):
        # Decrement current page and update table
        if self.current_page > 0:
            self.current_page -= 1
            self.update_table()

    def next_page(self):
        # Increment current page and update table
        last_page = len(self.data_filtered) // self.rows_per_page
        if self.current_page < last_page:
            self.current_page += 1
            self.update_table()


app = EditableTable(tk.Tk())
app.mainloop()
