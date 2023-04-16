import tkinter as tk
import pandas as pd
from pandastable import Table

file = '../results/list.csv'


class EditableTable(tk.Frame):

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
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
        self.table_frame = tk.Frame(self.master)
        self.filter_frame = tk.Frame(self.master)

        # Create button to toggle filter controls visibility
        self.toggle_button = tk.Button(self.master, text="Show Filters", command=self.toggle_filter_controls)
        self.toggle_button.pack(side=tk.TOP)

        # Create table to display data
        self.table = Table(self.table_frame, dataframe=self.df.iloc[0:0], showtoolbar=True, showstatusbar=True)
        self.table.show()

        # Pack the table_frame
        self.table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Add controls for filtering by category
        category_options = list(self.df['Category'].cat.categories)
        self.category_var = tk.StringVar(value=category_options[0])
        category_menu = tk.OptionMenu(self.filter_frame, self.category_var, *category_options, command=self.filter_by_category)
        category_menu.pack(side=tk.LEFT)

        # Add search box and button
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(self.filter_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT)
        search_button = tk.Button(self.filter_frame, text="Search", command=self.search)
        search_button.pack(side=tk.LEFT)

        # Add pagination controls
        self.prev_button = tk.Button(self.filter_frame, text="<<", command=self.prev_page)
        self.prev_button.pack(side=tk.LEFT)
        self.next_button = tk.Button(self.filter_frame, text=">>", command=self.next_page)
        self.next_button.pack(side=tk.RIGHT)

        # Update table with data for current page
        self.update_table()

    def toggle_filter_controls(self):
        # Toggle visibility of filter controls frame
        if self.filter_frame.winfo_ismapped():
            self.filter_frame.pack_forget()
            self.toggle_button.config(text="Show Filters")
        else:
            self.filter_frame.pack(side=tk.TOP, fill=tk.BOTH)
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
