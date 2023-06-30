import tkinter as tk
import pandas as pd
from pandastable import Table
from tkinter import ttk

file = 'K:/UE/UEVM/Results//list.csv'


class EditableTable(tk.Frame):

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.currentPage = 0
        self.rowsPerPage = 35
        self.paginationEnabled = True

        # Load data from CSV file
        self.df = pd.read_csv(file)

        # Set 'code' and 'category' columns as category type
        self.df['Grab result'] = self.df['Grab result'].astype('category')
        self.df['Category'] = self.df['Category'].astype('category')

        # Initialize filtered DataFrame
        self.df_filtered = self.df

        # Create filters
        self.create_filters()

        # Create frame for table
        f = tk.Frame(self.master)
        f.pack(fill=tk.BOTH, expand=1)

        # Create table to display data
        self.table = Table(f, dataframe=self.df.iloc[0:0], showtoolbar=True, showstatusbar=True)
        self.table.show()

        # Update table with data for current page
        self.update_table()

    def create_filters(self):
        filter_frame = tk.Frame(self.master)
        filter_frame.pack(side=tk.TOP, fill=tk.X)

        # Create 'Category' filter
        category_label = tk.Label(filter_frame, text="Category:")
        category_label.pack(side=tk.LEFT, padx=(10, 5))
        self.category_combobox = ttk.Combobox(filter_frame, values=list(self.df['Category'].cat.categories), state="readonly")
        self.category_combobox.pack(side=tk.LEFT, padx=(0, 10))
        self.category_combobox.bind("<<ComboboxSelected>>", self.apply_filters)

        # Create 'Grab result' filter
        grab_result_label = tk.Label(filter_frame, text="Grab result:")
        grab_result_label.pack(side=tk.LEFT, padx=(10, 5))
        self.grab_result_combobox = ttk.Combobox(filter_frame, values=list(self.df['Grab result'].cat.categories), state="readonly")
        self.grab_result_combobox.pack(side=tk.LEFT, padx=(0, 10))
        self.grab_result_combobox.bind("<<ComboboxSelected>>", self.apply_filters)

        # Create 'On Sale' filter
        self.create_on_sale_filter(filter_frame)

        # Create 'Reset filters' button
        reset_button = tk.Button(filter_frame, text="Reset Filters", command=self.reset_filters)
        reset_button.pack(side=tk.LEFT, padx=(10, 0))

    def create_on_sale_filter(self, filter_frame):
        self.on_sale_var = tk.BooleanVar()
        on_sale_checkbutton = tk.Checkbutton(filter_frame, text="On Sale", variable=self.on_sale_var, command=self.apply_filters)
        on_sale_checkbutton.pack(side=tk.LEFT, padx=(10, 0))

    def reset_filters(self):
        self.category_combobox.set('')
        self.grab_result_combobox.set('')
        self.on_sale_var.set(False)
        self.df_filtered = self.df
        self.update_table()

    def apply_filters(self, event=None):
        category_filter = self.category_combobox.get()
        grab_result_filter = self.grab_result_combobox.get()
        on_sale_filter = self.on_sale_var.get()

        self.df_filtered = self.df

        if category_filter:
            self.df_filtered = self.df_filtered[self.df_filtered['Category'] == category_filter]

        if grab_result_filter:
            self.df_filtered = self.df_filtered[self.df_filtered['Grab result'] == grab_result_filter]

        if on_sale_filter:
            self.df_filtered = self.df_filtered[self.df_filtered['Price'] > self.df_filtered['Discount']]

        self.update_table()

    def update_table(self):
        # Update table with filtered data
        self.table.model.df = self.df_filtered
        self.table.redraw()


class TableApp(tk.Tk):

    def __init__(self):
        super().__init__()

        self.title("Editable Table App")
        self.geometry("1200x880")

        # Create an EditableTable object
        self.editable_table = EditableTable(self)
        self.editable_table.pack(fill=tk.BOTH, expand=1)


if __name__ == "__main__":
    app = TableApp()
    app.mainloop()
