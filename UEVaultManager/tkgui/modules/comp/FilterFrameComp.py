# coding=utf-8
"""
Implementation for:
- FilterFrame class: a frame that contains widgets for filtering a DataFrame.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Tuple, Any, Dict

from UEVaultManager.tkgui.modules.functions import log_info, box_message


class FilterFrame(ttk.LabelFrame):
    """
    A frame that contains widgets for filtering a DataFrame.
    :param container: Container widget.
    :param data_func: A function that returns the DataFrame to be filtered.
    :param update_func: A function that updates the table.
    :param save_filter_func: A function that save the filters.
    :param title: The title of the frame.
    :param value_for_all: The value to use for the 'All' option.
    """
    _filters = {}
    _quick_filters = {
        # add ^ to the beginning of the value to search for the INVERSE the result
        'Owned': ['Owned', True],  #
        'Not Owned': ['Owned', False],  #
        'Obsolete': ['Obsolete', True],  #
        'Not Obsolete': ['Obsolete', False],  #
        'Must buy': ['Must buy', True],  #
        'Added manually': ['Added manually', True],  #
        'Grab OK': ['Grab result', 'NO_ERROR'],  #
        'Plugins only': ['Category', 'plugins'],  #
        'Free': ['Price', 0],  #
        'Dummy': ['Asset_id', 'dummy'],  #
        'Not Marketplace': ['Origin', '^Marketplace'],  # aset with origin NOT in marketplace
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

    def __init__(
        self,
        container: tk,
        data_func: Callable,
        update_func: Callable,
        save_filter_func: Callable,
        title: str = 'Define view filters for the data table',
        value_for_all: str = 'All'
    ):
        if container is None:
            raise ValueError('container cannot be None')
        if data_func is None:
            raise ValueError('data_func cannot be None')
        if update_func is None:
            raise ValueError('update_func cannot be None')

        super().__init__(container, text=title)
        self.value_for_all: str = value_for_all
        self.container = container
        self.data_func = data_func
        self.save_filter_func = save_filter_func
        if self.data_func is None:
            raise ValueError('data_func cannot be None')
        self.update_func = update_func
        if self.update_func is None:
            raise ValueError('update_func cannot be None')
        self._create_filter_widgets()

    def _search_combobox(self, _event, combobox) -> None:
        """
        Search for the text in the Combobox's values.
        :param _event: the event that triggered the search.
        :param combobox: the Combobox to search in.
        """
        # Get the current text in the Combobox
        text_lower = combobox.get().lower()
        if len(text_lower) < 3:
            return
        for value in combobox['values']:
            if value.lower().startswith(text_lower):
                combobox.set(value)
                self._update_filter_widgets()
                break

    # noinspection DuplicatedCode
    def _create_filter_widgets(self) -> None:
        """
        Create filter widgets inside the FilterFrame instance.
        """
        columns_to_list = self.data_func().columns.to_list()
        columns_to_list.insert(0, self.value_for_all)

        cur_row = 0
        cur_col = 0
        lbl_value = ttk.Label(self, text='Select filter')
        lbl_value.grid(row=cur_row, column=cur_col, **self.grid_def_options)
        cur_col += 1
        lbl_col_name = ttk.Label(self, text='Or Set a filter On')
        lbl_col_name.grid(row=cur_row, column=cur_col, columnspan=3, **self.grid_def_options)
        cur_col += 3
        lbl_value = ttk.Label(self, text='that contains ou equals')
        lbl_value.grid(row=cur_row, column=cur_col, columnspan=2, **self.grid_def_options)

        cur_row += 1
        cur_col = 0
        self.cb_quick_filter = ttk.Combobox(self, values=list(self._quick_filters.keys()), state='readonly', width=14)
        self.cb_quick_filter.grid(row=cur_row, column=cur_col, **self.grid_def_options)
        self.cb_quick_filter.bind('<<ComboboxSelected>>', lambda event: self.quick_filter())
        self.cb_quick_filter.bind('<KeyRelease>', lambda event: self._search_combobox(event, self.cb_quick_filter))

        cur_col += 1
        self.cb_col_name = ttk.Combobox(self, values=columns_to_list, state='readonly', width=18)
        self.cb_col_name.grid(row=cur_row, column=cur_col, columnspan=3, **self.grid_def_options)
        self.cb_col_name.bind('<<ComboboxSelected>>', lambda event: self._update_filter_widgets())
        self.cb_col_name.bind('<KeyRelease>', lambda event: self._search_combobox(event, self.cb_col_name))

        cur_col += 3
        self.frm_widgets = ttk.Frame(self)
        # widget dynamically created based on the dtype of the selected column in _update_filter_widgets()
        self.filter_widget = ttk.Entry(self.frm_widgets, state='disabled')
        self.filter_widget.pack(ipadx=1, ipady=1)
        self.frm_widgets.grid(row=cur_row, column=cur_col, columnspan=2, **self.grid_def_options)

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
        if self.save_filter_func is not None:
            cur_col += 1
            self.btn_save_filters = ttk.Button(self, text="Save", command=lambda: self.save_filter_func(self._filters))
            self.btn_save_filters.grid(row=cur_row, column=cur_col, **self.grid_def_options)
        self._update_filter_widgets()

    def _add_to_filters(self) -> None:
        """
        Read current selection from filter widgets and adds it to the filters' dictionary.
        """
        cb_selection = self.cb_col_name.get()
        if cb_selection:
            value_type_str, filter_value = self._get_filter_value_and_type()
            if cb_selection == 'Category' and filter_value != '':
                self.category = filter_value
            else:
                self.category = None
            if filter_value != '':
                # Filter values are a tuple of the form (value_type_str, filter_value)
                self._filters[cb_selection] = (value_type_str, filter_value)
                # print a text to easily add a new filter to self._quick_filters
                value = f"'{filter_value}'" if value_type_str == 'str' else filter_value
                log_info(f"Added filter: '{cb_selection}_filter':['{cb_selection}', {value}]  (value_type: {value_type_str})")
            self.update_controls()

    def _update_filter_widgets(self) -> None:
        """
        Update the widgets that are used for filtering based on the selected column.
        """
        cb_selection = self.cb_col_name.get()
        # Clear all widgets from the filter frame
        for widget in self.frm_widgets.winfo_children():
            widget.destroy()
        # Create the filter widget based on the dtype of the selected column
        if cb_selection:
            data = self.data_func()
            dtype = data[cb_selection].dtype if cb_selection != self.value_for_all else 'str'
            try:
                type_name = dtype.name
            except AttributeError:
                type_name = 'str'
            if type_name == 'bool':
                self.filter_value = tk.BooleanVar()
                self.filter_widget = ttk.Checkbutton(self.frm_widgets, variable=self.filter_value, command=self.update_func)
            elif type_name == 'category':
                self.filter_widget = ttk.Combobox(self.frm_widgets)
                self.filter_widget['values'] = list(data[cb_selection].cat.categories)
                self.filter_widget.bind('<KeyRelease>', lambda event: self._search_combobox(event, self.filter_widget))
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

    def _get_filter_value_and_type(self) -> Tuple[str, Any]:
        """
        Read current value from filter widgets and determines its type.
        :return: A tuple containing the type (str) and value of the filter condition.
        """
        if not self.filter_widget:
            return 'str', ''

        if isinstance(self.filter_widget, ttk.Checkbutton):
            value_type_str = 'bool'
            state = self.filter_widget.state()
            if 'alternate' in state:
                filter_value = ''
            elif 'selected' in state:
                filter_value = True
            else:
                filter_value = False
        elif isinstance(self.filter_widget, ttk.Spinbox):
            value_type_str = 'float'
            filter_value = self.filter_widget.get()
        else:
            value_type_str = 'str'
            filter_value = self.filter_widget.get()

        # value_type_str = re.sub(r"<class '(.*)'>", r'\1', str(value_type))
        return value_type_str, filter_value

    def create_mask(self):
        """
        Create a boolean mask for specified column based on filter value in a pandas DataFrame.
        :return: Boolean Series (mask) where True indicates rows that meet the condition.
        """
        data = self.data_func()
        final_mask = None
        mask = False
        for col_name, (value_type_str, filter_value) in self.get_filters().items():
            if col_name == self.value_for_all:
                mask = False
                for col in data.columns:
                    mask |= data[col].astype(str).str.lower().str.contains(filter_value.lower())
            else:
                try:
                    if value_type_str == 'bool' and filter_value != '':
                        mask = data[col_name].astype(bool) == filter_value
                    elif value_type_str == 'int':
                        mask = data[col_name].astype(int) == int(filter_value)
                    elif value_type_str == 'float':
                        filter_value = filter_value.replace(',', '.')
                        mask = data[col_name].astype(float) == float(filter_value)
                    else:
                        if filter_value[0] == '^':
                            # ^ negates the filter
                            mask = data[col_name].astype(str).str.lower().str.contains(filter_value[1:].lower()) == False
                        else:
                            mask = data[col_name].astype(str).str.lower().str.contains(filter_value.lower())
                except ValueError:
                    box_message(f'the value {filter_value} does not correspond to the type of column {col_name}')
            final_mask = mask if final_mask is None else final_mask & mask

        return final_mask

    def update_controls(self) -> None:
        """
        Update the state of the controls based on the current state of the filters.
        """
        cb_selection = self.cb_col_name.get()
        _, filter_value = self._get_filter_value_and_type()
        filter_count = len(self._filters)

        state = tk.NORMAL
        self.cb_col_name['state'] = state
        self.btn_clear_filters['state'] = state
        self.btn_save_filters['state'] = state  # empty filters can be saved to remove existing one in config

        cond_1 = (cb_selection == '')
        state = tk.NORMAL if cond_1 else tk.DISABLED
        self.cb_quick_filter['state'] = state

        cond_2 = (cb_selection != '' and filter_value != '')
        state = tk.NORMAL if cond_2 else tk.DISABLED
        self.btn_add_filters['state'] = state

        cond_3 = (filter_count > 0)
        state = tk.NORMAL if cond_3 else tk.DISABLED
        self.btn_view_filters['state'] = state

        state = tk.NORMAL if cond_2 or cond_3 else tk.DISABLED
        self.btn_apply_filters['state'] = state

        self.filters_count_var.set(f'Filters ({filter_count})')

    def get_filters(self) -> Dict[str, Tuple[type, Any]]:
        """
        Get the filter dictionary.
        :return: The filter dictionary containing the filter conditions.
        """
        return self._filters

    def apply_filters(self) -> None:
        """
        Applie the filters and updates the caller.
        """
        self._add_to_filters()
        # self._update_filter_widgets()
        self.update_controls()
        self.update_func(reset_page=True)

    def reset_filters(self) -> None:
        """
        Reset all filter conditions and update the caller.
        """
        self.cb_col_name.set('')
        self.cb_quick_filter.set('')
        if isinstance(self.filter_widget, ttk.Checkbutton):
            self.filter_widget.state(['alternate'])
        else:
            self.filter_widget.delete(0, 'end')
        self._filters = {}
        self._update_filter_widgets()
        self.update_func(reset_page=True)

    def view_filters(self) -> None:
        """
        View the filter dictionary.
        """
        values = '\n'.join([f'"{k}" equals or contains "{v[1]}"' for k, v in self._filters.items()])
        msg = values + '\n\nCopy values into clipboard ?'
        if messagebox.askyesno('View data filters', message=msg):
            self.clipboard_clear()
            self.clipboard_append(values)

    def quick_filter(self) -> None:
        """
        Update the widgets that are used for filtering based on the selected column.
        """
        selected_filter = self.cb_quick_filter.get()
        quick_filter = self._quick_filters.get(selected_filter, None)
        if selected_filter and quick_filter:
            store_filters = self._filters.copy()
            str_type = type(quick_filter[1]).__name__
            self._filters = {quick_filter[0]: (str_type, quick_filter[1])}
            self.update_func()
            self._filters = store_filters

    def load_filters(self, filters: Dict[str, Tuple[type, Any]]) -> None:
        """
        Load the filter dictionary.
        :param filters: The filter dictionary containing the filter conditions.
        """
        if filters is None or not isinstance(filters, dict) or len(filters) == 0:
            return
        self._filters = filters.copy()
        self._update_filter_widgets()
        self.update_func()
