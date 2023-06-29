# coding=utf-8
"""
This module contains a class that creates a frame with widgets for filtering a DataFrame.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Tuple, Any, Dict

from pandastable import Table
import pandas as pd
import os
import re

global_rows_per_page = 10
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


def create_mask(col_name: str, value_type: type, filter_value, data: pd.DataFrame) -> pd.Series:
    """
    Creates a boolean mask for specified column based on filter value in a pandas DataFrame.
    :param col_name: Column name for which the mask will be created.
    :param value_type: Type of the filter value.
    :param filter_value: The value to filter by.
    :param data: The pandas DataFrame where the mask will be applied.
    :return: Boolean Series (mask) where True indicates rows that meet the condition.
    """
    if col_name == global_value_for_all:
        mask = None
        for col in data.columns:
            mask |= data[col].astype(str).str.lower().str.contains(filter_value.lower())
    else:
        if value_type == bool and filter_value != '':
            mask = data[col_name].astype(bool) == filter_value
        elif value_type == int:
            mask = data[col_name].astype(int) == int(filter_value)
        elif value_type == float:
            mask = data[col_name].astype(float) == float(filter_value)
        else:
            mask = data[col_name].astype(str).str.lower().str.contains(filter_value.lower())
    return mask


class FilterFrame(ttk.LabelFrame):
    """
    A frame that contains widgets for filtering a DataFrame.
    :param parent: Parent widget.
    :param data_func: A function that returns the DataFrame to be filtered.
    :param update_func: A function that updates the table.
    """
    _filters = {}
    _quick_filters = {
        'Owned': ['Owned', True],  #
        'Not Owned': ['Owned', False],  #
        'Obsolete': ['Obsolete', True],  #
        'Not Obsolete': ['Obsolete', False],  #
        'Must buy': ['Must buy', True],  #
        'Added manually': ['Added manually', True],  #
        'Grab OK': ['Grab result', 'NO_ERROR'],  #
        'Plugins only': ['Category', 'plugins'],  #
        'Free': ['Price', 0],  #
    }
    frm_widgets = None
    cb_col_name = None
    cb_quick_filter = None
    btn_apply_filters = None
    btn_add_filters = None
    btn_clear_filters = None
    btn_view_filters = None
    lbl_filters_count = None
    filters_count_var = None
    pack_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.X, 'expand': True}
    grid_def_options = {'ipadx': 1, 'ipady': 1, 'padx': 1, 'pady': 1, 'sticky': tk.W}

    def __init__(self, parent: tk, data_func: Callable[[], pd.DataFrame], update_func: Callable[[], None]):
        super().__init__(parent, text='Set filters for data')
        self.container = parent
        self.data_func = data_func
        if self.data_func is None:
            raise ValueError('data_func cannot be None')
        self.update_func = update_func
        if self.update_func is None:
            raise ValueError('update_func cannot be None')
        self._create_filter_widgets()

    def _create_filter_widgets(self) -> None:
        """
        Creates filter widgets inside the FilterFrame instance.
        """
        columns_to_list = self.data_func().columns.to_list()
        columns_to_list.insert(0, global_value_for_all)

        cur_row = 0
        cur_col = 0
        # empty cell for now
        cur_col += 1
        lbl_value = ttk.Label(self, text='Quick Filter')
        lbl_value.grid(row=cur_row, column=cur_col, **self.grid_def_options)
        cur_col += 2
        lbl_col_name = ttk.Label(self, text='Filter On')
        lbl_col_name.grid(row=cur_row, column=cur_col, columnspan=2, **self.grid_def_options)
        cur_col += 2
        lbl_value = ttk.Label(self, text='With value')
        lbl_value.grid(row=cur_row, column=cur_col, columnspan=2, **self.grid_def_options)

        cur_row += 1
        cur_col = 0
        self.btn_clear_filters = ttk.Button(self, text="Clear All", command=self.reset_filters)
        self.btn_clear_filters.grid(row=cur_row, column=cur_col, **self.grid_def_options)
        cur_col += 1
        self.cb_quick_filter = ttk.Combobox(self, values=list(self._quick_filters.keys()), state='readonly')
        self.cb_quick_filter.grid(row=cur_row, column=cur_col, columnspan=2, **self.grid_def_options)
        self.cb_quick_filter.bind('<<ComboboxSelected>>', lambda event: self.quick_filter())
        cur_col += 2
        self.cb_col_name = ttk.Combobox(self, values=columns_to_list, state='readonly')
        self.cb_col_name.grid(row=cur_row, column=cur_col, columnspan=2, **self.grid_def_options)
        self.cb_col_name.bind('<<ComboboxSelected>>', lambda event: self._update_filter_widgets())
        cur_col += 2
        self.frm_widgets = ttk.Frame(self)
        # widget dynamically created based on the dtype of the selected column in _update_filter_widgets()
        self.filter_widget = ttk.Entry(self.frm_widgets, state='disabled')
        self.filter_widget.pack(ipadx=1, ipady=1)
        self.frm_widgets.grid(row=cur_row, column=cur_col, **self.grid_def_options)

        cur_row += 1
        cur_col = 0
        lbl_filters = ttk.Label(self, text='Filter List:')
        lbl_filters.grid(row=cur_row, column=cur_col, **{'ipadx': 1, 'ipady': 1, 'padx': 1, 'pady': 1, 'sticky': tk.E})
        cur_col += 1
        self.filters_count_var = tk.StringVar(value='Count: 0')
        self.lbl_filters_count = ttk.Label(self, textvariable=self.filters_count_var)
        self.lbl_filters_count.grid(row=cur_row, column=cur_col, **self.grid_def_options)
        cur_col += 1
        self.btn_add_filters = ttk.Button(self, text="Add to", command=self._add_to_filters)
        self.btn_add_filters.grid(row=cur_row, column=cur_col, **self.grid_def_options)
        cur_col += 1
        self.btn_apply_filters = ttk.Button(self, text="Apply", command=self.apply_filters)
        self.btn_apply_filters.grid(row=cur_row, column=cur_col, **self.grid_def_options)
        cur_col += 1
        self.btn_view_filters = ttk.Button(self, text="View", command=self.view_filters)
        self.btn_view_filters.grid(row=cur_row, column=cur_col, **self.grid_def_options)
        cur_col += 1
        # empty cell for now

        self._update_filter_widgets()

    def _add_to_filters(self) -> None:
        """
        Reads current selection from filter widgets and adds it to the filters' dictionary.
        """
        selected_column = self.cb_col_name.get()
        if selected_column:
            value_type, filter_value = self._get_filter_value_and_type()
            if filter_value != '':
                # Filter values are a tuple of the form (value_type, filter_value)
                self._filters[selected_column] = (value_type, filter_value)
                # print a text to easily add a new filter to self._quick_filters
                value_type = re.sub(r"<class '(.*)'>", r'\1', str(value_type))
                value = f"'{filter_value}'" if value_type == 'str' else filter_value
                log_info(f"Added filter: '{selected_column}_filter':['{selected_column}', {value}]  (value_type: {value_type})")
            self.update_controls()

    def _update_filter_widgets(self) -> None:
        """
        Updates the widgets that are used for filtering based on the selected column.
        """
        selected_column = self.cb_col_name.get()
        # Clear all widgets from the filter frame
        for widget in self.frm_widgets.winfo_children():
            widget.destroy()
        # Create the filter widget based on the dtype of the selected column
        if selected_column:
            data = self.data_func()
            dtype = data[selected_column].dtype if selected_column != global_value_for_all else 'str'
            try:
                type_name = dtype.name
            except AttributeError:
                type_name = 'str'
            if type_name == 'bool':
                self.filter_value = tk.BooleanVar()
                self.filter_widget = ttk.Checkbutton(self.frm_widgets, variable=self.filter_value, command=self.update_func)
            elif type_name == 'category':
                self.filter_widget = ttk.Combobox(self.frm_widgets)
                self.filter_widget['values'] = list(data[selected_column].cat.categories)
            elif type_name in ('int', 'float', 'int64', 'float64'):
                self.filter_widget = ttk.Spinbox(self.frm_widgets, increment=0.1, from_=0, to=100, command=self.update_func)
            else:
                self.filter_widget = ttk.Entry(self.frm_widgets, width=20)
        else:
            self.filter_widget = ttk.Entry(self.frm_widgets, width=20, state='disabled')

        self.filter_widget.bind('<FocusIn>', lambda event: self.update_controls())
        self.filter_widget.bind('<Key>', lambda event: self.update_controls())
        self.filter_widget.pack(ipadx=1, ipady=1)

        self.update_controls()

    def _get_filter_value_and_type(self) -> Tuple[type, Any]:
        """
        Reads current value from filter widgets and determines its type.
        :return: A tuple containing the type and value of the filter condition.
        """
        if not self.filter_widget:
            return str, ''

        if isinstance(self.filter_widget, ttk.Checkbutton):
            value_type = bool
            state = self.filter_widget.state()
            if 'alternate' in state:
                filter_value = ''
            elif 'selected' in state:
                filter_value = True
            else:
                filter_value = False
        elif isinstance(self.filter_widget, ttk.Spinbox):
            value_type = float
            filter_value = self.filter_widget.get()
        else:
            value_type = str
            filter_value = self.filter_widget.get()
        return value_type, filter_value

    def update_controls(self) -> None:
        """
        Updates the state of the controls based on the current state of the filters.
        """
        selected_column = self.cb_col_name.get()
        _, filter_value = self._get_filter_value_and_type()
        filter_count = len(self._filters)

        state = tk.NORMAL
        self.cb_col_name['state'] = state
        self.btn_clear_filters['state'] = state

        state = tk.NORMAL if selected_column != '' else tk.DISABLED
        state_inversed = tk.NORMAL if selected_column == '' else tk.DISABLED
        self.cb_quick_filter['state'] = state_inversed

        state = tk.NORMAL if (selected_column != '' and filter_value != '') else tk.DISABLED
        self.btn_add_filters['state'] = state
        self.btn_apply_filters['state'] = state

        state = tk.NORMAL if filter_count > 0 else tk.DISABLED
        self.btn_view_filters['state'] = state

        self.filters_count_var.set(f'Count: {filter_count}')

    def get_filters(self) -> Dict[str, Tuple[type, Any]]:
        """
        Get the filters dictionary
        :return: The filters dictionary containing the filter conditions.
        """
        return self._filters

    def apply_filters(self) -> None:
        """
        Applies the filters and updates the caller.
        """
        if len(self._filters) <= 0:
            self._add_to_filters()
            self._update_filter_widgets()
        self.update_controls()
        self.update_func()

    def reset_filters(self) -> None:
        """
        Resets all filter conditions and updates the caller.
        """
        self.cb_col_name.set('')
        if isinstance(self.filter_widget, ttk.Checkbutton):
            self.filter_widget.state(['alternate'])
        else:
            self.filter_widget.delete(0, 'end')
        self._filters = {}
        self._update_filter_widgets()
        self.update_func()

    def view_filters(self) -> None:
        """
        View the filters dictionary
        """
        values = '\n'.join([f'"{k}" equals or contains "{v[1]}"' for k, v in self._filters.items()])
        msg = values + '\n\nCopy values into clipboard ?'
        if messagebox.askyesno('View data filters', message=msg):
            self.clipboard_clear()
            self.clipboard_append(values)

    def quick_filter(self) -> None:
        """
        Updates the widgets that are used for filtering based on the selected column.
        """
        selected_filter = self.cb_quick_filter.get()
        quick_filter = self._quick_filters.get(selected_filter, None)
        if selected_filter and quick_filter:
            store_filters = self._filters.copy()
            self._filters = {quick_filter[0]: (type(quick_filter[1]), quick_filter[1])}
            self.update_func()
            self._filters = store_filters


class App(tk.Tk):
    """
    Main application class
    """
    _data = {}
    _filtered = {}
    table = None
    current_page = 1
    total_pages = 0

    _frm_filters = None
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
        self._frm_filters = FilterFrame(self, self.get_data, self.update)
        self._frm_filters.pack(**self.lblf_def_options)

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
        final_mask = None
        for column, (value_type, filter_value) in self._frm_filters.get_filters().items():
            mask = create_mask(column, value_type, filter_value, data)
            final_mask = mask if final_mask is None else final_mask & mask
        if final_mask is not None:
            self._filtered = data[final_mask]
        else:
            self._filtered = data
        self.update_page_info()

    def update_page_info(self) -> None:
        """
        Updates the page info.
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
        self.total_results_var.set(f'Total Results: {len(self._filtered)}')
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
