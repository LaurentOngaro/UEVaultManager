# coding=utf-8
"""
Implementation for:
- FilterFrame class: a frame that contains widgets for filtering a DataFrame.
"""
import re
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Tuple, Any, Dict

from UEVaultManager.tkgui.modules.functions import log_info


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
    category = None
    pack_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.X, 'expand': True}
    grid_def_options = {'ipadx': 1, 'ipady': 1, 'padx': 1, 'pady': 1, 'sticky': tk.W}

    def __init__(self, parent: tk, data_func: Callable, update_func: Callable, title='Set filters for data', value_for_all='All'):
        if data_func is None:
            raise ValueError('data_func cannot be None')
        if update_func is None:
            raise ValueError('update_func cannot be None')

        super().__init__(parent, text=title)
        self.value_for_all = value_for_all
        self.container = parent
        self.data_func = data_func
        if self.data_func is None:
            raise ValueError('data_func cannot be None')
        self.update_func = update_func
        if self.update_func is None:
            raise ValueError('update_func cannot be None')
        self._create_filter_widgets()

    # noinspection DuplicatedCode
    def _create_filter_widgets(self) -> None:
        """
        Creates filter widgets inside the FilterFrame instance.
        """
        columns_to_list = self.data_func().columns.to_list()
        columns_to_list.insert(0, self.value_for_all)

        cur_row = 0
        cur_col = 0
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
        self.filters_count_var = tk.StringVar(value='Filters (0)')
        self.lbl_filters_count = ttk.Label(self, textvariable=self.filters_count_var)
        self.lbl_filters_count.grid(row=cur_row, column=cur_col, **{'ipadx': 1, 'ipady': 1, 'padx': 1, 'pady': 1, 'sticky': tk.E})
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
        self.btn_clear_filters = ttk.Button(self, text="Clear All", command=self.reset_filters)
        self.btn_clear_filters.grid(row=cur_row, column=cur_col, **self.grid_def_options)

        self._update_filter_widgets()

    def _add_to_filters(self) -> None:
        """
        Reads current selection from filter widgets and adds it to the filters' dictionary.
        """
        selected_column = self.cb_col_name.get()
        if selected_column:
            value_type, filter_value = self._get_filter_value_and_type()
            if selected_column == 'Category' and filter_value != '':
                self.category = filter_value
            else:
                self.category = None
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
            dtype = data[selected_column].dtype if selected_column != self.value_for_all else 'str'
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

    def create_mask(self):
        """
        Creates a boolean mask for specified column based on filter value in a pandas DataFrame.
        :return: Boolean Series (mask) where True indicates rows that meet the condition.
        """
        data = self.data_func()
        final_mask = None

        for col_name, (value_type, filter_value) in self.get_filters().items():
            if col_name == self.value_for_all:
                mask = False
                for col in data.columns:
                    mask |= data[col].astype(str).str.lower().str.contains(filter_value.lower())
            else:
                if value_type == bool and filter_value != '':
                    mask = data[col_name].astype(bool) == filter_value
                elif value_type == int:
                    mask = data[col_name].astype(int) == int(filter_value)
                elif value_type == float:
                    filter_value = filter_value.replace(',', '.')
                    mask = data[col_name].astype(float) == float(filter_value)
                else:
                    mask = data[col_name].astype(str).str.lower().str.contains(filter_value.lower())
            final_mask = mask if final_mask is None else final_mask & mask

        return final_mask

    def update_controls(self) -> None:
        """
        Updates the state of the controls based on the current state of the filters
        """
        selected_column = self.cb_col_name.get()
        _, filter_value = self._get_filter_value_and_type()
        filter_count = len(self._filters)

        state = tk.NORMAL
        self.cb_col_name['state'] = state
        self.btn_clear_filters['state'] = state

        state = tk.NORMAL if selected_column == '' else tk.DISABLED
        self.cb_quick_filter['state'] = state

        state = tk.NORMAL if (selected_column != '' and filter_value != '') else tk.DISABLED
        self.btn_add_filters['state'] = state
        self.btn_apply_filters['state'] = state

        state = tk.NORMAL if filter_count > 0 else tk.DISABLED
        self.btn_view_filters['state'] = state

        self.filters_count_var.set(f'Filters ({filter_count})')

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

    def load_filters(self, filters: Dict[str, Tuple[type, Any]]) -> None:
        """
        Loads the filters dictionary
        :param filters: The filters dictionary containing the filter conditions.
        """
        if filters is None or not isinstance(filters, dict) or len(filters) == 0:
            return
        self._filters = filters.copy()
        self._update_filter_widgets()
        self.update_controls()
