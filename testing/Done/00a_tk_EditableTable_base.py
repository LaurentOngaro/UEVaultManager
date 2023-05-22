import tkinter as tk
import pandas as pd
from pandastable import Table

file = '../../results/list.csv'


class EditableTable(tk.Frame):

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.parent.geometry('1200x880')
        self.parent.title('Table app')
        self.currentPage = 0
        self.rowsPerPage = 35
        self.paginationEnabled = True
        self.df = pd.read_csv(file)
        self.df_filtered = self.df
        f = tk.Frame(self.parent)
        f.pack(fill=tk.BOTH, expand=1)
        self.table = Table(f, dataframe=self.df.iloc[0:0], showtoolbar=True, showstatusbar=True)
        self.table.show()
        self.update_table()

    def update_table(self):
        self.table.model.df = self.df_filtered
        self.table.redraw()


app = EditableTable(tk.Tk())
app.mainloop()
