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
    img = canvas.create_image(0, 0, anchor=tk.NW, image=canvas.image)


class EditableTable(ttk.Frame):

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
            # Resize the image
            resize_and_show_image(image, self.image_canvas, new_height, new_width)

        except Exception as e:
            print(f"Error showing image: {e}")

    def show_default_image(self):
        try:
            # Load the default image
            if os.path.isfile(default_image_filename):
                def_image = Image.open(default_image_filename)
                resize_and_show_image(def_image, self.image_canvas, max_width, max_height)
        except Exception as e:
            print(f"Error showing default image {default_image_filename} cwd:{os.getcwd()}: {e}")

    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        self.parent = parent
        self.master.geometry('1200x880')
        self.master.title('Table app')
        self.currentPage = 0
        self.rowsPerPage = 35
        self.paginationEnabled = True

        # Load data from CSV file
        self.df = pd.read_csv(file)

        # Convert Category column to category dtype
        self.df['Category'] = self.df['Category'].astype('category')

        # Initialize filtered DataFrame
        self.df_filtered = self.df

        # Create frame for table and filter controls
        self.table_frame = ttk.Frame(self.master)
        self.control_frame = ttk.Frame(self.master)

        # Create button to toggle filter controls visibility
        self.toggle_button = ttk.Button(self.master, text="Show Controls", command=self.toggle_filter_controls)
        self.toggle_button.pack(side=tk.TOP)

        # Create table to display data
        self.table = Table(self.table_frame, dataframe=self.df.iloc[0:0], showtoolbar=True, showstatusbar=True)
        self.table.show()

        # Pack the table_frame
        self.table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Bind the table to the mouse motion event
        self.table.bind('<Motion>', self.mouse_over_cell)

        # Bind the table to the mouse leave event
        self.table.bind('<Leave>', self.show_default_image)

        # Create a Canvas to display the image in a popup window
        self.image_canvas = tk.Canvas(self.control_frame, width=max_width, height=max_height, highlightthickness=0)
        self.image_canvas.pack(side=tk.LEFT)
        self.image_canvas.create_rectangle((0, 0), (max_width, max_height), fill='black')
        self.show_default_image()

        # Add controls for filtering by category
        category_options = list(self.df['Category'].cat.categories)
        self.category_var = tk.StringVar(value=category_options[0])
        category_menu = tk.OptionMenu(self.control_frame, self.category_var, *category_options, command=self.filter_by_category)
        category_menu.pack(side=tk.LEFT)

        # Add search box and button
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(self.control_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT)
        search_button = ttk.Button(self.control_frame, text="Search", command=self.search)
        search_button.pack(side=tk.LEFT)

        # Add pagination controls
        self.prev_button = ttk.Button(self.control_frame, text="<<", command=self.prev_page)
        self.prev_button.pack(side=tk.LEFT)
        self.next_button = ttk.Button(self.control_frame, text=">>", command=self.next_page)
        self.next_button.pack(side=tk.RIGHT)

        # Update table with data for current page
        self.update_table()

    def toggle_filter_controls(self):
        # Toggle visibility of filter controls frame
        if self.control_frame.winfo_ismapped():
            self.control_frame.pack_forget()
            self.toggle_button.config(text="Show Filters")
        else:
            self.control_frame.pack(side=tk.TOP, fill=tk.BOTH)
            self.toggle_button.config(text="Hide Filters")

    def update_table(self):
        # Calculate start and end row for current page
        start_row = self.currentPage * self.rowsPerPage
        end_row = start_row + self.rowsPerPage

        # Update table with data for current page
        self.table.model.df = self.df_filtered.iloc[start_row:end_row]
        self.table.redraw()

    def filter_by_category(self, category):
        # Filter dataframe by selected category
        self.df_filtered = self.df[self.df['Category'] == category]

        # Apply search filter if search box is not empty
        search_value = self.search_var.get()
        if search_value:
            self.df_filtered = self.df_filtered[self.df_filtered.apply(lambda row: search_value.lower() in str(row).lower(), axis=1)]

        # Reset current page to 0
        self.currentPage = 0

        # Update table with filtered data for current page
        self.update_table()

    def search(self):
        # Filter dataframe by search value
        search_value = self.search_var.get()
        self.df_filtered = self.df[self.df['Category'] == self.category_var.get()]
        self.df_filtered = self.df_filtered[self.df_filtered.apply(lambda row: search_value.lower() in str(row).lower(), axis=1)]

        # Reset current page to 0
        self.currentPage = 0

        # Update table with filtered data for current page
        self.update_table()

    def prev_page(self):
        # Decrement current page and update table
        if self.currentPage > 0:
            self.currentPage -= 1
            self.update_table()

    def next_page(self):
        # Increment current page and update table
        last_page = len(self.df_filtered) // self.rowsPerPage
        if self.currentPage < last_page:
            self.currentPage += 1
            self.update_table()


app = EditableTable(tk.Tk())
app.mainloop()
