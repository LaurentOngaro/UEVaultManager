# coding=utf-8
"""
Implementation for:
- FilterFrame class: frame that contains widgets for filtering a DataFrame.
"""
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, Dict, Tuple

import pandas as pd

import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.functions import box_message, log_info


# not needed here
# warnings.filterwarnings('ignore', category=FutureWarning)  # Avoid the FutureWarning when PANDAS use ser.astype(object).apply()


class FilterFrame(ttk.LabelFrame):
    """
    A frame that contains widgets for filtering a DataFrame.
    :param container: container widget.
    :param data_func: function that returns the DataFrame to be filtered.
    :param update_func: function that updates the table.
    :param save_filter_func: function that save the filters.
    :param load_filter_func: function that load the filters.
    :param dynamic_filters_func: function used to create dynamic filter added to the quick filter list.
    :param title: title of the frame.
    :param value_for_all: value to use for the 'All' option.
    """

    def __init__(
        self,
        container: tk,
        data_func: Callable,
        update_func: Callable,
        save_filter_func: Callable,
        load_filter_func: Callable,
        dynamic_filters_func: Callable = None,
        title: str = 'Define view filters for the data table',
        value_for_all: str = 'All',
    ):
        if container is None:
            raise ValueError('container can not be None')
        if data_func is None:
            raise ValueError('data_func can not be None')
        if update_func is None:
            raise ValueError('update_func can not be None')

        super().__init__(container, text=title)
        self._filters = {}
        self._quick_filters = {}
        self._filter_mask = None
        self.frm_widgets = None
        self.cb_col_name = None
        self.cb_quick_filter = None
        self.btn_apply_filters = None
        self.btn_add_filters = None
        self.btn_clear_filters = None
        self.btn_view_filters = None
        self.lbl_filters_count = None
        self.var_filters_count = None
        self.category = None
        self.pack_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.X, 'expand': True}
        self.grid_def_options = {'ipadx': 1, 'ipady': 1, 'padx': 1, 'pady': 1, 'sticky': tk.W}
        self.value_for_all: str = value_for_all
        self.container = container
        self.data_func = data_func
        self.save_filter_func = save_filter_func
        self.load_filter_func = load_filter_func
        self.dynamic_filters_func = dynamic_filters_func
        if self.data_func is None:
            raise ValueError('data_func can not be None')
        self.update_func = update_func
        if self.update_func is None:
            raise ValueError('update_func can not be None')
        # call the dynamic filters function to add dynamic filters to the quick filters
        if self.dynamic_filters_func is not None:
            dynamic_filters = self.dynamic_filters_func()
            if dynamic_filters is not None:
                self._quick_filters.update(dynamic_filters)
        self._create_filter_widgets()

    def _search_combobox(self, _event, combobox) -> None:
        """
        Search for the text in the Combobox's values.
        :param _event: event that triggered the search.
        :param combobox: Combobox to search in.
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
        # new row
        cur_row = 0
        cur_col = 0
        ttk_item = ttk.Label(self, text='Select quick filter')
        ttk_item.grid(row=cur_row, column=cur_col, **self.grid_def_options)
        cur_col += 1
        ttk_item = ttk.Label(self, text='Or set a filter On')
        ttk_item.grid(row=cur_row, column=cur_col, columnspan=3, **self.grid_def_options)
        cur_col += 3
        ttk_item = ttk.Label(self, text='that is or contains')
        ttk_item.grid(row=cur_row, column=cur_col, columnspan=3, **self.grid_def_options)
        # new row
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
        self.frm_widgets.grid(row=cur_row, column=cur_col, columnspan=3, **self.grid_def_options)
        # new row
        cur_row += 1
        cur_col = 0
        self.var_filters_count = tk.StringVar(value='Filters (0)')
        self.lbl_filters_count = ttk.Label(self, textvariable=self.var_filters_count)
        self.lbl_filters_count.grid(row=cur_row, column=cur_col, **{'ipadx': 1, 'ipady': 1, 'padx': 1, 'pady': 1, 'sticky': tk.E})
        cur_col += 1
        self.btn_add_filters = ttk.Button(self, text='Add to', command=self._add_to_filters)
        self.btn_add_filters.grid(row=cur_row, column=cur_col, **self.grid_def_options)
        cur_col += 1
        self.btn_apply_filters = ttk.Button(self, text='Apply', command=self.apply_filters)
        self.btn_apply_filters.grid(row=cur_row, column=cur_col, **self.grid_def_options)
        cur_col += 1
        self.btn_view_filters = ttk.Button(self, text='View', command=self.view_filters)
        self.btn_view_filters.grid(row=cur_row, column=cur_col, **self.grid_def_options)
        cur_col += 1
        self.btn_clear_filters = ttk.Button(self, text='Clear', command=self.clear_filters)
        self.btn_clear_filters.grid(row=cur_row, column=cur_col, **self.grid_def_options)
        if self.save_filter_func is not None:
            cur_col += 1
            self.btn_save_filters = ttk.Button(self, text='Save', command=lambda: self.save_filter_func(self._filters))
            self.btn_save_filters.grid(row=cur_row, column=cur_col, **self.grid_def_options)
        if self.load_filter_func is not None:
            cur_col += 1
            self.btn_load_filters = ttk.Button(self, text='Load', command=self._load_filters)
            self.btn_load_filters.grid(row=cur_row, column=cur_col, **self.grid_def_options)
        self._update_filter_widgets()

    def _load_filters(self) -> None:
        """
        Load filters from a file.
        """
        filters = self.load_filter_func()
        if filters is not None:
            self.set_filters(filters)

    def _add_to_filters(self) -> None:
        """
        Read current selection from filter widgets and adds it to the filters' dictionary.
        """
        cb_selection = self.cb_col_name.get()
        if cb_selection:
            value_type_str, filter_value = self._get_filter_value_and_type()
            if cb_selection == 'Category' and filter_value:
                self.category = filter_value
            else:
                self.category = None
            if filter_value:
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
        :return: tuple containing the type (str) and value of the filter condition.
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

    def create_mask(self, filters=None):
        """
        Create a boolean mask for specified column based on filter value in a pandas DataFrame.
        """
        # if not filters:
        #     # load quick filter first
        #     filters = self.quick_filter(only_return_filter=True).items()
        # if not filters:
        #     filters = self._filters.items()

        if not filters:
            quick_filters: dict = self.quick_filter(only_return_filter=True)
            filters: dict = self._filters.copy()
            filters.update(quick_filters)

        final_mask = None
        mask = False
        data = self.data_func()
        for col_name, (value_type_str, filter_value) in filters.items():
            if col_name == self.value_for_all:
                mask = False
                for col in data.columns:
                    mask |= data[col].astype(str).str.lower().str.contains(filter_value.lower())
            else:
                try:
                    if value_type_str == 'bool':
                        mask = data[col_name].astype(bool) == filter_value
                    elif value_type_str == 'int':
                        mask = data[col_name].astype(int) == int(filter_value)
                    elif value_type_str == 'float':
                        filter_value = filter_value.replace(',', '.')
                        mask = data[col_name].astype(float) == float(filter_value)
                    elif value_type_str.lower() in ('callable', 'method') and filter_value:
                        # filter_value is a function that returns a mask (boolean Series)
                        mask = filter_value()
                    else:
                        check_value = True # needed for the test "==" bellow
                        if isinstance(filter_value, str) and filter_value.startswith('^'):
                            # ^ negates the filter
                            check_value = not check_value
                        mask = data[col_name].astype(str).str.lower().str.contains(filter_value.lower()) == check_value
                except ValueError:
                    box_message(f'the value {filter_value} does not correspond to the type of column {col_name}')
            final_mask = mask if final_mask is None else final_mask & mask
        self._filter_mask = final_mask

    def get_filter_mask(self) -> pd.Series:
        """
        Get the boolean mask for specified column based on filter value in a pandas DataFrame.
        :return: boolean mask.
        """
        return self._filter_mask

    def set_filters(self, filters: Dict[str, Tuple[type, Any]]) -> None:
        """
        Set the filters used.
        :param filters: filter dictionary containing the filter conditions.
        """
        if not filters or not isinstance(filters, dict):
            return
        self._filters = filters.copy()
        self._update_filter_widgets()
        self.update_func(reset_page=True, update_filters=True, update_format=True)

    def update_controls(self) -> None:
        """
        Update the state of the controls based on the current state of the filters.
        """
        # Note:
        # No need to use the global widgets list here beceause this frame is meant to be "standalone" and its widgets are not used elsewhere.

        cb_selection = self.cb_col_name.get()
        _, filter_value = self._get_filter_value_and_type()
        filter_count = len(self._filters)

        state = tk.NORMAL
        self.cb_col_name['state'] = state
        self.btn_clear_filters['state'] = state
        self.btn_save_filters['state'] = state  # empty filters can be saved to remove existing one in config

        cond_1 = not cb_selection
        state = tk.NORMAL if cond_1 else tk.DISABLED
        self.cb_quick_filter['state'] = state

        cond_2 = (cb_selection and filter_value)
        state = tk.NORMAL if cond_2 else tk.DISABLED
        self.btn_add_filters['state'] = state

        cond_3 = (filter_count > 0)
        state = tk.NORMAL if cond_3 else tk.DISABLED
        self.btn_view_filters['state'] = state
        self.btn_save_filters['state'] = state

        state = tk.NORMAL if cond_2 or cond_3 else tk.DISABLED
        self.btn_apply_filters['state'] = state

        self.var_filters_count.set(f'Filters ({filter_count})')

    def apply_filters(self) -> None:
        """
        Applie the filters and updates the caller.
        """
        self._add_to_filters()
        self.update_controls()
        self.update_func(reset_page=True, update_filters=True)

    def clear_filters(self) -> None:
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
        self._filter_mask = None
        gui_g.s.last_opened_filter = ''
        gui_g.s.save_config_file()
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

    def quick_filter(self, only_return_filter=False) -> dict:
        """
        Update the widgets that are used for filtering based on the selected column.
        :param only_return_filter: wether only return the filter string without applying it.
        :return: filter dict.
        """
        filter_dict = {}
        selected_filter = self.cb_quick_filter.get()
        quick_filter = self._quick_filters.get(selected_filter, None)
        if selected_filter and quick_filter:
            str_type = type(quick_filter[1]).__name__
            filter_dict = {quick_filter[0]: (str_type, quick_filter[1])}
            if not only_return_filter:
                # self.create_mask(filter_dict.items())
                self.update_func(reset_page=True, update_filters=True)
        return filter_dict
