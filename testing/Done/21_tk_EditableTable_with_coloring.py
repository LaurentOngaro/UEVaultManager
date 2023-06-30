import tkinter as tk
import pandas as pd
from pandastable import Table

file = 'K:/UE/UEVM/Results//list.csv'


class EditableTable(tk.Frame):

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.master.geometry('1200x880')
        self.master.title('Table app')
        self.currentPage = 0
        self.rowsPerPage = 35
        self.paginationEnabled = True
        self.df = pd.read_csv(file)
        self.df_filtered = self.df
        f = tk.Frame(self.master)
        f.pack(fill=tk.BOTH, expand=1)
        self.table = Table(f, dataframe=self.df.iloc[0:0], showtoolbar=True, showstatusbar=True)
        self.table.show()
        self.update_table()
        # Apply cell color formatting using a styler object
        self.highlight_cells()

    def update_table(self):
        self.table.model.df = self.df_filtered
        self.table.redraw()

    def highlight_cells(self):

        table = self.table
        table.setRowColors(rows=2, clr='red', cols='all')
        table.setRowColors(rows=[3, 4], clr='green', cols=[0, 1])
        table.setRowColors(rows=[5], clr='blue', cols=[-3, -1])


app = EditableTable(tk.Tk())
app.mainloop()

# table.textcolor = 'blue'
# table.cellbackgr = 'white'
# table.boxoutlinecolor = 'black'
# # set header colors
# table.rowheader.bgcolor = 'orange'
# table.colheader.bgcolor = 'lightgreen'
# table.colheader.textcolor = 'black'

#
# def highlight_cells_HS1(self):
#
#     def check_value(val):
#         print(f' val = {val}')
#         if not isinstance(val, (int, float)):
#             return
#
#         if val > 4.5:
#             color = 'green'
#         elif val > 4:
#             color = 'yellow'
#         elif val > 3:
#             color = 'orange'
#         else:
#             color = 'red'
#         return 'background-color: %s' % color
#
#     # Apply the cell color formatting to integer and float columns using the check_value method
#     self.df.style.applymap(check_value)
#     self.df.applymap(check_value)
#
# def highlight_cells_HS2(self):
#
#     def check_value(x):
#         if isinstance(x, (int, float)) and x < 4:
#             return 'background-color: red'
#         return 'background-color: green'
#
#     # Create a styler object from the DataFrame
#     styler = self.df_filtered.style
#
#     # Apply the cell color formatting to the "Review" column
#     styler = styler.applymap(check_value, subset=pd.IndexSlice[:, "Review"])
#
#     # Set the styled DataFrame back to the table
#     self.table.model.df = styler.data
#
#     # Redraw the table to display the updated styling
#     self.table.redraw()
