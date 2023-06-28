import tkinter as tk
from tkinter import ttk
from pandastable import Table
import pandas as pd
from functools import partial


class App:
    rows_per_page = 10

    def __init__(self, root):
        self.root = root
        self._data = None
        self._data_filtered = None
        self.table = None
        self.current_page = 1
        self.total_pages = 0

        self.filter_frame = None
        self.data_frame = None
        self.info_frame = None

        self.combo_box = None
        self.filter_entry = None

        self.total_results_var = None
        self.total_pages_var = None
        self.current_page_var = None

        self.next_button = None
        self.previous_button = None
        self.first_button = None
        self.last_button = None
        self.reset_button = None

        self.load_data()
        self.create_widgets()

    def load_data(self):
        self._data = pd.read_csv('K:/UE/UEVM/results/list.csv')
        self.total_pages = (len(self._data) - 1) // self.rows_per_page + 1

    def get_data(self):
        return self._data

    def create_widgets(self):
        self.create_filter_frame()
        self.create_data_frame()
        self.create_info_frame()
        self.create_navigation_frame()

    def create_filter_frame(self):
        self.filter_frame = ttk.Frame(self.root)
        self.filter_frame.pack(fill=tk.X, expand=True)

        self.combo_box = ttk.Combobox(self.filter_frame, values=self.get_data().columns.to_list())
        self.combo_box.grid(row=0, column=0)
        self.filter_entry = ttk.Entry(self.filter_frame)
        self.filter_entry.grid(row=0, column=1)
        self.filter_entry.bind('<KeyRelease>', lambda event: self.update_table())

        self.reset_button = ttk.Button(self.filter_frame, text="Reset Filter", command=self.reset_filter)
        self.reset_button.grid(row=0, column=2)

    def create_data_frame(self):
        self.data_frame = ttk.Frame(self.root)
        self.data_frame.pack(fill=tk.X, expand=True)
        self.table = Table(self.data_frame, dataframe=self.get_data().iloc[0:self.rows_per_page])
        self.table.show()

    def create_info_frame(self):
        self.info_frame = ttk.Frame(self.root)
        self.info_frame.pack(fill=tk.X, expand=True)

        self.total_results_var = tk.StringVar(self.root, f"Total Results: {len(self.get_data())}")
        total_results_label = ttk.Label(self.info_frame, textvariable=self.total_results_var)
        total_results_label.pack(side=tk.LEFT)

        self.total_pages_var = tk.StringVar(self.root, f"Total Pages: {self.total_pages}")
        total_pages_label = ttk.Label(self.info_frame, textvariable=self.total_pages_var)
        total_pages_label.pack(side=tk.LEFT)

        self.current_page_var = tk.StringVar(self.root, f"Current Page: {self.current_page}")
        current_page_label = ttk.Label(self.info_frame, textvariable=self.current_page_var)
        current_page_label.pack(side=tk.LEFT)

    def create_navigation_frame(self):
        navigation_frame = ttk.Frame(self.root)
        navigation_frame.pack(fill=tk.X, expand=True)

        prev_button = ttk.Button(navigation_frame, text="Prev", command=self.prev_page)
        prev_button.pack(side=tk.LEFT)

        next_button = ttk.Button(navigation_frame, text="Next", command=self.next_page)
        next_button.pack(side=tk.RIGHT)

    def update_table(self):
        selected_column = self.combo_box.get()
        filter_value = self.filter_entry.get()
        if selected_column and filter_value:
            mask = self.get_data()[selected_column].apply(lambda x: True if filter_value == '' else filter_value in str(x))
            self._data_filtered = self.get_data()[mask]
        else:
            self._data_filtered = self.get_data()

        self.total_pages = (len(self._data_filtered) - 1) // self.rows_per_page + 1
        start = (self.current_page - 1) * self.rows_per_page
        end = start + self.rows_per_page

        # Update the model df and redraw
        self.table.model.df = self._data_filtered.iloc[start:end]
        self.table.redraw()

        # Use f-string for formatting
        self.total_results_var.set(f"Total Results: {len(self._data_filtered)}")
        self.total_pages_var.set(f"Total Pages: {self.total_pages}")
        self.current_page_var.set(f"Current Page: {self.current_page}")

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_table()

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.update_table()

    def reset_filter(self):
        self.combo_box.set('')
        self.filter_entry.delete(0, 'end')
        self.update_table()


root = tk.Tk()
App(root)
root.mainloop()
