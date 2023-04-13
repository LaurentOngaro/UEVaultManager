import tkinter as tk
from tkinter import ttk
import pandas as pd
from pandastable import Table


class EditableTable(tk.Frame):

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.master.geometry('600x400+200+100')
        self.master.title('Table app')
        self.currentPage = 0
        self.rowsPerPage = 10
        self.paginationEnabled = True

        # Load data from CSV file
        self.df = pd.read_csv('../results/list.csv')

        # Initialize filtered DataFrame
        self.df_filtered = self.df

        # Create frame for table
        f = tk.Frame(self.master)
        f.pack(fill=tk.BOTH, expand=1)

        # Create table to display data
        self.table = Table(f, dataframe=self.df.iloc[0:0], showtoolbar=False, showstatusbar=False)
        self.table.show()

        # Add buttons for pagination
        self.prevButton = tk.Button(self.master, text='Previous', command=self.prev_page)
        self.prevButton.pack(side=tk.LEFT)
        tk.Label(self.master, textvariable=self.currentPage).pack(side=tk.LEFT)
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

        # Update table with data for current page
        self.updateTable()

    def updateTable(self):
        if self.paginationEnabled:
            # Calculate start and end rows for current page
            start_row = self.currentPage * self.rowsPerPage
            end_row = start_row + self.rowsPerPage

            # Update table with data for current page
            self.table.model.df = self.df_filtered.iloc[start_row:end_row]
            self.table.redraw()
        else:
            # Update table with all data
            self.table.model.df = self.df_filtered
            self.table.redraw()

    def prev_page(self):
        # Go to previous page if not on first page
        if self.currentPage > 0:
            self.currentPage -= 1
            self.updateTable()

    def next_page(self):
        # Go to next page if not on last page
        if (self.currentPage + 1) * self.rowsPerPage < len(self.df):
            self.currentPage += 1
            self.updateTable()

    def toggle_pagination(self):
        # Toggle pagination on/off and update table
        self.paginationEnabled = not self.paginationEnabled
        if not self.paginationEnabled:
            # Reset current page when disabling pagination
            self.currentPage = 0

            # Disable prev/next buttons when pagination is disabled
            self.prevButton.config(state=tk.DISABLED)
            self.nextButton.config(state=tk.DISABLED)
        else:
            # Enable prev/next buttons when pagination is enabled
            self.prevButton.config(state=tk.NORMAL)
            self.nextButton.config(state=tk.NORMAL)

        # Update table with data for current page or all data if pagination is disabled
        self.updateTable()

    def filter_data(self):
        # Get selected column and entered value
        selected_column = self.columnCombobox.get()
        filter_value = self.filterValueEntry.get()

        if selected_column and filter_value:
            # Filter DataFrame based on selected column and entered value
            self.df_filtered = self.df[self.df[selected_column].astype(str).str.contains(filter_value)]

            # Reset current page to 0
            self.currentPage = 0

            # Update table with filtered data
            self.updateTable()
        else:
            # If no column/value is selected or entered, show the original data
            self.df_filtered = self.df
            self.updateTable()


app = EditableTable(tk.Tk())
app.mainloop()
