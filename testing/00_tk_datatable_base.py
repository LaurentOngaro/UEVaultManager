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

        # Initialize filtered DataFrame
        self.df_filtered = self.df

        # Create frame for table
        f = tk.Frame(self.master)
        f.pack(fill=tk.BOTH, expand=1)

        # Create table to display data
        self.table = Table(f, dataframe=self.df.iloc[0:0], showtoolbar=True, showstatusbar=True)
        self.table.show()

        # Update table with data for current page
        self.update_table()

    def update_table(self):
        # Update table with all data
        self.table.model.df = self.df_filtered
        self.table.redraw()


app = EditableTable(tk.Tk())
app.mainloop()
