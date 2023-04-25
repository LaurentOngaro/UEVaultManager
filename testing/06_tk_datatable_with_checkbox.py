import tkinter as tk
import pandas as pd
from pandastable import Table

file = '../results/list.csv'


def is_bool(x):
    try:
        if str(x).lower() in ('1', '1.0', 'true', 'yes', 'y', 't', '0', '0.0', 'false', 'no', 'n', 'f'):
            return True
        else:
            return False
    except ValueError:
        return False


class SpecialTable(Table):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.frame = args[0]
        self.cell_entry = None
        self.ck_offset_x = 0
        self.ck_offset_y = 0

    def drawCellEntry(self, row, col, text=''):
        x1, y1, x2, y2 = self.getCellCoords(row, col)
        cell_x = (x1+x2) // 2
        cell_y = (y1+y2) // 2
        # THIS OFFSET IS NOT VALID WHEN SCROLLING HORIZONTALLY.
        # Todo: fix the calculation.
        self.ck_offset_x = -int(self.Xscrollbar.get()[0] * self.winfo_width())
        # THIS OFFSET IS NOT VALID WHEN SCROLLING VERTICALLY.
        # Todo: fix the calculation.
        self.ck_offset_y = int(self.Yscrollbar.get()[0] * self.winfo_height())
        cell_x = x1 + self.ck_offset_x
        cell_y = y1 + self.ck_offset_y

        print(f'self.ck_offset_x: {self.ck_offset_x} self.ck_offset_y: {self.ck_offset_y}')
        cell_value = self.model.getValueAt(row, col)
        print(f'cell_value: {cell_value} is_bool: {is_bool(cell_value)} row: {row} col: {col} cell_x={cell_x} cell_y={cell_y}')
        if is_bool(cell_value):
            self.cell_entry = tk.Checkbutton(self.parentframe, command=self.check_box_handler(col, row))
            self.cell_entry.var = tk.BooleanVar(value=str(self.model.getValueAt(row, col)))
            self.cell_entry.config(variable=self.cell_entry.var)
            self.cell_entry.place(x=cell_x, y=cell_y, anchor='center', width=50, height=30)
        else:
            super().drawCellEntry(col, row, text)

    def check_box_handler(self, col, row):

        def toggle_checkbox():
            current_value = self.cell_entry.var.get()
            self.model.setValueAt(current_value, row, col)
            self.redraw()

        return toggle_checkbox


class EditableTable(tk.Frame):

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.master.geometry('1400x880')
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
        self.table = SpecialTable(f, dataframe=self.df.iloc[0:0], showtoolbar=True, showstatusbar=True)
        self.table.show()

        # Update table with data for current page
        self.update_table()

    def update_table(self):
        # Update table with all data
        self.table.model.df = self.df_filtered
        self.table.redraw()


app = EditableTable(tk.Tk())
app.mainloop()
