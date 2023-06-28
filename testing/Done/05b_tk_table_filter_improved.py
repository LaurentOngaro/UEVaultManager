import tkinter as tk
from tkinter import ttk
from pandastable import Table
import pandas as pd
from functools import partial
import os
import numpy as np


class App:
    rows_per_page = 10
    value_for_all = 'All'
    _data = None
    _data_filtered = None
    table = None
    current_page = 1
    total_pages = 0

    filter_frame = None
    data_frame = None
    info_frame = None
    inner_frame = None

    combo_box = None
    filter_widget = None
    filter_value = None

    total_results_var = None
    total_pages_var = None
    current_page_var = None

    next_button = None
    previous_button = None
    first_button = None
    last_button = None
    reset_button = None

    def __init__(self, root, file=''):
        self.root = root
        self.file = file

        self.load_data()
        self.create_widgets()

    def load_data(self):
        if os.path.isfile(self.file):
            self._data = pd.read_csv(self.file)
        else:
            raise FileNotFoundError(f"No such file: '{self.file}'")
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

        # Init self.combo_box here, so it's not None when update_filter_widgets is called for the first time
        columns_to_list = self.get_data().columns.to_list()
        columns_to_list.insert(0, self.value_for_all)
        self.combo_box = ttk.Combobox(self.filter_frame, values=columns_to_list, state='readonly')
        self.combo_box.grid(row=0, column=0)

        self.inner_frame = ttk.Frame(self.filter_frame)
        self.filter_widget = ttk.Entry(self.inner_frame)
        self.filter_widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.filter_widget.bind('<FocusOut>', lambda event: self.update_table())
        self.inner_frame.grid(row=0, column=1)

        # Recreate the reset button
        self.reset_button = ttk.Button(self.filter_frame, text="Reset Filter", command=self.reset_filter)
        self.reset_button.grid(row=0, column=2)

        # Continue to bind the <<ComboboxSelected>> only after you've dealt with the existing selected_column
        self.combo_box.bind('<<ComboboxSelected>>', lambda event: self.update_filter_widgets())

    def update_filter_widgets(self):
        selected_column = self.combo_box.get()

        # Clear all widgets from the filter frame
        for widget in self.inner_frame.winfo_children():
            widget.destroy()

        # Create the filter widget based on the dtype of the selected column
        if selected_column:
            dtype = self.get_data()[selected_column].dtype if selected_column != self.value_for_all else 'str'
            if dtype == 'bool':
                self.filter_value = tk.BooleanVar()
                self.filter_widget = ttk.Checkbutton(self.inner_frame, variable=self.filter_value, command=self.update_table)
                self.filter_widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            elif np.issubdtype(dtype, int) or np.issubdtype(dtype, float):
                self.filter_widget = ttk.Spinbox(self.inner_frame, increment=0.1, from_=0, to=100, command=self.update_table)
                self.filter_widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            else:
                self.filter_widget = ttk.Entry(self.inner_frame)
                self.filter_widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self.filter_widget.bind('<FocusOut>', lambda event: self.update_table())

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

    def reset_filter(self):
        self.combo_box.set('')
        if isinstance(self.filter_widget, ttk.Checkbutton):
            self.filter_widget.state(['alternate'])
        else:
            self.filter_widget.delete(0, 'end')

        self.update_filter_widgets()
        self.update_table()

    def update_table(self):
        selected_column = self.combo_box.get()
        filter_value = None
        value_type = None
        if selected_column:
            if isinstance(self.filter_widget, ttk.Checkbutton):
                value_type = bool
                # empty string for alternate state, True for selected state, False for unselected state
                state = self.filter_widget.state()
                if 'selected' in state:
                    filter_value = True
                elif 'alternate' in state:
                    filter_value = ''
                elif not ('selected' in state or 'alternate' in state):
                    filter_value = False
            elif isinstance(self.filter_widget, ttk.Spinbox):
                value_type = float
                filter_value = self.filter_widget.get()
            else:
                value_type = str
                filter_value = self.filter_widget.get()

        if filter_value is not None:
            if selected_column == self.value_for_all:
                mask = False
                for col in self.get_data().columns:
                    mask |= self.get_data()[col].astype(str).apply(lambda x: True if filter_value == '' else str(filter_value).lower() in x.lower())
            else:
                if value_type == bool and filter_value != '':
                    mask = self.get_data()[selected_column].astype(bool).apply(lambda x: True if x==filter_value else False)
                elif value_type == float:
                    mask = self.get_data()[selected_column].astype(float).apply(lambda x: True if filter_value == '' else x == float(filter_value))
                else:
                    mask = self.get_data(
                    )[selected_column].astype(str).apply(lambda x: True if filter_value == '' else str(filter_value).lower() in x.lower())
            self._data_filtered = self.get_data()[mask]
        else:
            self._data_filtered = self.get_data()

        self.total_pages = (len(self._data_filtered) - 1) // self.rows_per_page + 1
        start = (self.current_page - 1) * self.rows_per_page
        end = start + self.rows_per_page
        self.table.model.df = self._data_filtered.iloc[start:end]

        self.table.redraw()
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


root = tk.Tk()
App(root, 'K:/UE/UEVM/results/list.csv')
root.mainloop()
