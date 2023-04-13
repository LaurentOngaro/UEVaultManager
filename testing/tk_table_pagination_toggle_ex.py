import tkinter as tk
import pandas as pd
from pandastable import Table


class Example(tk.Frame):

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.main = self.master
        self.main.geometry('600x400+200+100')
        self.main.title('Table app')
        self.currentPage = 0
        self.rowsPerPage = 10
        self.paginationEnabled = True

        # Load data from CSV file
        self.df = pd.read_csv('../results/list.csv')

        # Create frame for table
        f = tk.Frame(self.main)
        f.pack(fill=tk.BOTH, expand=1)

        # Create table to display data
        self.table = Table(f, dataframe=self.df.iloc[0:0], showtoolbar=False, showstatusbar=False)
        self.table.show()

        # Add buttons for pagination
        self.prevButton = tk.Button(self.main, text='Previous', command=self.prevPage)
        self.prevButton.pack(side=tk.LEFT)
        tk.Label(self.main, textvariable=self.currentPage).pack(side=tk.LEFT)
        self.nextButton = tk.Button(self.main, text='Next', command=self.nextPage)
        self.nextButton.pack(side=tk.LEFT)
        tk.Button(self.main, text='Toggle Pagination', command=self.togglePagination).pack(side=tk.LEFT)

        # Update table with data for current page
        self.updateTable()

    def updateTable(self):
        if self.paginationEnabled:
            # Calculate start and end rows for current page
            startRow = self.currentPage * self.rowsPerPage
            endRow = startRow + self.rowsPerPage

            # Update table with data for current page
            self.table.model.df = self.df.iloc[startRow:endRow]
            self.table.redraw()
        else:
            # Update table with all data
            self.table.model.df = self.df
            self.table.redraw()

    def prevPage(self):
        # Go to previous page if not on first page
        if self.currentPage > 0:
            self.currentPage -= 1
            self.updateTable()

    def nextPage(self):
        # Go to next page if not on last page
        if (self.currentPage + 1) * self.rowsPerPage < len(self.df):
            self.currentPage += 1
            self.updateTable()

    def togglePagination(self):
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


app = Example(tk.Tk())
app.mainloop()
