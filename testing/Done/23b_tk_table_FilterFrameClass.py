# coding=utf-8
"""
This module contains a class that creates a frame with widgets for filtering a DataFrame.
"""
import tkinter as tk
from tkinter import ttk

from pandastable import Table
import pandas as pd
import os

from UEVaultManager.tkgui.modules.comp.FilterFrameComp import FilterFrame

global_rows_per_page = 36
global_value_for_all = 'All'


def log_info(msg: str) -> None:
    """
    Logs an info message.
    :param msg: The message to log.
    """
    print(f'[INFO] {msg}')


def log_error(msg: str) -> None:
    """
    Logs an error message.
    :param msg: The message to log.
    """
    print(f'[ERROR] {msg}')


class App(tk.Tk):
    """
    Main application class
    """
    _data = {}
    _filtered = {}
    table = None
    current_page = 1
    total_pages = 0

    _filter_frame = None
    data_frame = None
    info_frame = None

    total_results_var = None
    total_pages_var = None
    current_page_var = None

    next_button = None
    previous_button = None
    first_button = None
    last_button = None
    reset_button = None

    pack_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.BOTH, 'expand': False}
    lblf_def_options = {'ipadx': 1, 'ipady': 1, 'expand': False}
    grid_def_options = {'ipadx': 1, 'ipady': 1, 'padx': 1, 'pady': 1, 'sticky': tk.SE}

    def __init__(self, file='', rows_per_page=global_rows_per_page):
        super().__init__()
        self.file = file
        self.rows_per_page = rows_per_page

        self.load_data()
        self.create_widgets()

    def create_widgets(self) -> None:
        """
        Creates all widgets for the application
        """
        self._filter_frame = FilterFrame(self, data_func=self.get_data, update_func=self.update, value_for_all=global_value_for_all)
        self._filter_frame.pack(**self.lblf_def_options)

        self._create_data_frame()
        self._create_info_frame()
        self._create_navigation_frame()

    def _create_data_frame(self) -> None:
        """
        Creates the data frame and table
        """
        self.data_frame = ttk.Frame(self)
        self.data_frame.pack(**self.pack_def_options)
        self.table = Table(self.data_frame, dataframe=self.get_data().iloc[0:self.rows_per_page])
        self.table.show()

    def _create_info_frame(self) -> None:
        """
        Creates the info frame
        """
        self.info_frame = ttk.Frame(self)
        self.info_frame.pack(**self.pack_def_options)
        self.total_results_var = tk.StringVar()
        total_results_label = ttk.Label(self.info_frame, textvariable=self.total_results_var)
        total_results_label.pack(side=tk.LEFT, **self.pack_def_options)
        self.total_pages_var = tk.StringVar()
        total_pages_label = ttk.Label(self.info_frame, textvariable=self.total_pages_var)
        total_pages_label.pack(side=tk.LEFT, **self.pack_def_options)
        self.current_page_var = tk.StringVar()
        current_page_label = ttk.Label(self.info_frame, textvariable=self.current_page_var)
        current_page_label.pack(side=tk.LEFT, **self.pack_def_options)

    def _create_navigation_frame(self) -> None:
        """
        Creates the navigation frame.
        """
        navigation_frame = ttk.Frame(self)
        navigation_frame.pack(**self.pack_def_options)
        prev_button = ttk.Button(navigation_frame, text='Prev', command=self.prev_page)
        prev_button.pack(side=tk.LEFT, **self.pack_def_options)
        next_button = ttk.Button(navigation_frame, text='Next', command=self.next_page)
        next_button.pack(side=tk.RIGHT, **self.pack_def_options)

    def get_data(self) -> pd.DataFrame:
        """
        Returns the data that is currently displayed in the table
        :return:
        """
        return self._data

    def load_data(self) -> None:
        """
        Loads the data from the file specified in the constructor.
        :return:
        """
        if os.path.isfile(self.file):
            self._data = pd.read_csv(self.file)

            # Change the dtype for 'Category' and 'Grab Result' to 'category'
            for col in ['Category', 'Grab result']:
                if col in self._data.columns:
                    self._data[col] = self._data[col].astype('category')
        else:
            raise FileNotFoundError(f'No such file: "{self.file}"')
        self.total_pages = (len(self._data) - 1) // self.rows_per_page + 1

    def update(self) -> None:
        """
        Updates the table with the current data.
        """
        data = self.get_data()
        mask = None
        if self._filter_frame is not None:
            mask = self._filter_frame.create_mask()
        if mask is not None:
            self._filtered = data[mask]
        else:
            self._filtered = data
        self.update_page()

    def update_page(self) -> None:
        """
        Updates the page
        """
        data_count = len(self._filtered)
        self.total_pages = (data_count-1) // self.rows_per_page + 1
        start = (self.current_page - 1) * self.rows_per_page
        end = start + self.rows_per_page
        try:
            # could be empty before load_data is called
            self.table.model.df = self._filtered.iloc[start:end]
        except IndexError:
            self.current_page = self.total_pages

        self.table.redraw()
        self.total_results_var.set(f'Total Results: {data_count}')
        self.total_pages_var.set(f'Total Pages: {self.total_pages}')
        self.current_page_var.set(f'Current Page: {self.current_page}')

    def next_page(self) -> None:
        """
        Shows the next page.
        """
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update()

    def prev_page(self) -> None:
        """
        Shows the previous page.
        """
        if self.current_page > 1:
            self.current_page -= 1
            self.update()


if __name__ == '__main__':
    main = App(file='K:/UE/UEVM/results/list.csv')
    main.mainloop()
