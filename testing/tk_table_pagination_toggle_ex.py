import os.path
import tkinter as tk
from tkinter import ttk
import pandas as pd
from pandastable import Table
from tkinter import filedialog

file = '../results/list.csv'


class EditableTable(tk.Frame):

    def __init__(self, container_frame):
        tk.Frame.__init__(self, container_frame)
        self.container_frame = container_frame
        self.master.geometry('1200x880')
        self.master.title('Table app')
        self.current_page = 0
        self.rowsPerPage = 35
        self.pagination_enabled = True

        # Load data from CSV file
        self.df = pd.read_csv(file)

        # Initialize filtered DataFrame
        self.data_filtered = self.df

        # Create frame for table
        f = tk.Frame(self.master)
        f.pack(fill=tk.BOTH, expand=1)

        # Create table to display data
        self.table = Table(f, dataframe=self.df.iloc[0:0], showtoolbar=True, showstatusbar=True)
        self.table.show()

        # Add buttons for pagination
        self.prevButton = tk.Button(self.master, text='Previous', command=self.prev_page)
        self.prevButton.pack(side=tk.LEFT)
        tk.Label(self.master, textvariable=self.current_page).pack(side=tk.LEFT)
        self.nextButton = tk.Button(self.master, text='Next', command=self.next_page)
        self.nextButton.pack(side=tk.LEFT)
        tk.Button(self.master, text='Toggle Pagination', command=self.toggle_pagination).pack(side=tk.LEFT)

        # Add Combobox for selecting column names
        self.columnCombobox = ttk.Combobox(self.master, values=list(self.df.columns))
        self.columnCombobox.pack(side=tk.LEFT)

        # Add Entry for entering filter value
        self.filterValueEntry = tk.Entry(self.master)
        self.filterValueEntry.pack(side=tk.LEFT)

        # Add Button to filter rows based on entered value
        self.filterButton = tk.Button(self.master, text='Filter', command=self.filter_data)
        self.filterButton.pack(side=tk.LEFT)

        self.exportButton = tk.Button(self.master, text='Export Selected Row', command=self.export_selection)
        self.exportButton.pack(side=tk.LEFT)

        # Update table with data for current page
        self.update_table()

    def update_table(self):
        if self.pagination_enabled:
            # Calculate start and end rows for current page
            start = self.current_page * self.rowsPerPage
            end = start + self.rowsPerPage

            # Update table with data for current page
            self.table.model.df = self.data_filtered.iloc[start:end]
            self.table.redraw()
        else:
            # Update table with all data
            self.table.model.df = self.data_filtered
            self.table.redraw()

    def prev_page(self):
        # Go to previous page if not on first page
        if self.current_page > 0:
            self.current_page -= 1
            self.update_table()

    def next_page(self):
        # Go to next page if not on last page
        if (self.current_page + 1) * self.rowsPerPage < len(self.df):
            self.current_page += 1
            self.update_table()

    def toggle_pagination(self):
        # Toggle pagination on/off and update table
        self.pagination_enabled = not self.pagination_enabled
        if not self.pagination_enabled:
            # Reset current page when disabling pagination
            self.current_page = 0

            # Disable prev/next buttons when pagination is disabled
            self.prevButton.config(state=tk.DISABLED)
            self.nextButton.config(state=tk.DISABLED)
        else:
            # Enable prev/next buttons when pagination is enabled
            self.prevButton.config(state=tk.NORMAL)
            self.nextButton.config(state=tk.NORMAL)

        # Update table with data for current page or all data if pagination is disabled
        self.update_table()

    def filter_data(self):
        # Get selected column and entered value
        selected_column = self.columnCombobox.get()
        filter_value = self.filterValueEntry.get()

        if selected_column and filter_value:
            # Filter DataFrame based on selected column and entered value
            self.data_filtered = self.df[self.df[selected_column].astype(str).str.contains(filter_value)]

            # Reset current page to 0
            self.current_page = 0

            # Update table with filtered data
            self.update_table()
        else:
            # If no column/value is selected or entered, show the original data
            self.data_filtered = self.df
            self.update_table()

    def export_selection(self):
        # Get selected row indices
        selected_row_indices = self.table.multiplerowlist

        if selected_row_indices:
            # Get selected rows from filtered DataFrame
            selected_rows = self.data_filtered.iloc[selected_row_indices]

            # Open file dialog to select file to save exported rows
            file_name = filedialog.asksaveasfilename(
                defaultextension=".csv", initialfile="export.csv", initialdir=os.path.dirname(file), filetypes=[("CSV files", "*.csv")]
            )

            if file_name:
                # Export selected rows to the specified CSV file
                selected_rows.to_csv(file_name, index=False)

                print(f"Selected rows exported to '{file_name}'")
            else:
                print("No file selected")
        else:
            print("No rows selected")


app = EditableTable(tk.Tk())
app.mainloop()
