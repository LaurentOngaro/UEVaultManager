# coding=utf-8
"""
Implementation for:
- FilterFrame class: frame that contains widgets for filtering a DataFrame.
"""
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Dict

import pandas as pd

import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.cls.FilterValueClass import FilterValue
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
    :param quick_filters: initial content for quick_filters
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
        quick_filters=None,
        title: str = 'Define view filters for the data table',
        value_for_all: str = 'All',
    ):
        if quick_filters is None:
            quick_filters = dict()
        if container is None:
            raise ValueError('container can not be None')
        if data_func is None:
            raise ValueError('data_func can not be None')
        if update_func is None:
            raise ValueError('update_func can not be None')

        super().__init__(container, text=title)
        self._filters: Dict[str, FilterValue] = {}
        self._quick_filters = quick_filters if quick_filters else {}  # type: Dict[str, FilterValue]
        self._filter_mask = None
        self.frm_widgets = None
        self.cb_col_name = None
        self.cb_quick_filter = None
        self.btn_apply_filters = None
        self.btn_add_and_filters = None
        self.btn_add_or_filters = None
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
        if self.data_func is None:
            raise ValueError('data_func can not be None')
        self.update_func = update_func
        if self.update_func is None:
            raise ValueError('update_func can not be None')

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
        self.cb_quick_filter.bind('<<ComboboxSelected>>', lambda event: self.get_quick_filter())
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
        self.btn_add_and_filters = ttk.Button(self, text='+ (And)', command=self._add_and_to_filters)
        self.btn_add_and_filters.grid(row=cur_row, column=cur_col, **self.grid_def_options)
        cur_col += 1
        self.btn_add_or_filters = ttk.Button(self, text='+ (Or)', command=self._add_or_to_filters)
        self.btn_add_or_filters.grid(row=cur_row, column=cur_col, **self.grid_def_options)
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

    def _add_and_to_filters(self) -> None:
        self._add_to_filters(use_or=False)

    def _add_or_to_filters(self) -> None:
        self._add_to_filters(use_or=True)

    def _add_to_filters(self, use_or: bool = False) -> None:
        """
        Read current selection from filter widgets and adds it to the filters' dictionary.
        """
        col_name = self.cb_col_name.get()
        if col_name:
            current_filter = self._create_filter_from_widgets(col_name, use_or)
            if col_name == 'Category' and current_filter.value:
                self.category = current_filter.value
            else:
                self.category = None
            if current_filter.value:
                filter_name = f'Filter_{col_name}'
                self._filters[filter_name] = current_filter
                log_info(f'Added {current_filter!r}')
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

    def _create_filter_from_widgets(self, col_name: str, use_or: bool = False) -> FilterValue:
        """
        Read current value from filter widgets and determines its type.
        :param col_name: name of the column to filter.
        :param use_or: wether to use an OR condition.
        :return: tuple containing the type (str) and value of the filter condition.
        """
        if not self.filter_widget or not col_name:
            return FilterValue('', '', False)

        if isinstance(self.filter_widget, ttk.Checkbutton):
            # value_type = bool
            state = self.filter_widget.state()
            if 'alternate' in state:
                value = ''
            elif 'selected' in state:
                value = True
            else:
                value = False
        elif isinstance(self.filter_widget, ttk.Spinbox):
            # value_type = float
            value = self.filter_widget.get()
        else:
            # value_type = str
            value = self.filter_widget.get()
        return FilterValue(col_name, value, use_or)

    def create_mask(self, filters=None):
        """
        Create a boolean mask for specified column based on filter value in a pandas DataFrame.
        """
        if not filters:
            # if no filters are specified, use the quick_filter
            filters = self._filters.copy()
            quick_filter = self.get_quick_filter(only_return_filter=True)
            if quick_filter:
                filters['quick_filter'] = quick_filter

        final_mask = None
        mask = False
        data = self.data_func()
        for filter_name, a_filter in filters.items():
            col_name = a_filter.col_name
            ftype = a_filter.ftype
            filter_value = a_filter.value
            use_or = a_filter.use_or
            if col_name == self.value_for_all:
                mask = False
                for col in data.columns:
                    mask |= data[col].astype(str).str.lower().str.contains(filter_value.lower())
            else:
                try:
                    if ftype == bool:
                        mask = data[col_name].astype(bool) == filter_value
                    elif ftype == int:
                        mask = data[col_name].astype(int) == int(filter_value)
                    elif ftype == float:
                        filter_value = str(filter_value).replace(',', '.')
                        mask = data[col_name].astype(float) == float(filter_value)
                    elif str(ftype).lower() in ('callable', 'method') and filter_value:
                        # filter_value is a function that returns a mask (boolean Series)
                        mask = filter_value()
                    else:
                        check_value = True  # needed for the test "==" bellow
                        if isinstance(filter_value, str) and filter_value.startswith('^'):
                            # ^ negates the filter
                            check_value = not check_value
                        mask = data[col_name].astype(str).str.lower().str.contains(filter_value.lower()) == check_value
                except ValueError:
                    box_message(f'the value {filter_value} does not correspond to the type of column {col_name}')
            # final_mask = mask if final_mask is None else final_mask | mask if use_or else final_mask & mask
            if use_or:
                final_mask = mask if final_mask is None else final_mask | mask
            else:
                final_mask = mask if final_mask is None else final_mask & mask
        self._filter_mask = final_mask

    def get_filter_mask(self) -> pd.Series:
        """
        Get the boolean mask for specified column based on filter value in a pandas DataFrame.
        :return: boolean mask.
        """
        return self._filter_mask

    def set_filters(self, filters: Dict = None) -> None:
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

        col_name = self.cb_col_name.get()
        current_filter = self._create_filter_from_widgets(col_name=col_name)

        filter_count = len(self._filters)

        state = tk.NORMAL
        self.cb_col_name['state'] = state
        self.btn_clear_filters['state'] = state
        self.btn_save_filters['state'] = state  # empty filters can be saved to remove existing one in config

        cond_1 = not col_name
        state = tk.NORMAL if cond_1 else tk.DISABLED
        self.cb_quick_filter['state'] = state

        cond_2 = (col_name and current_filter.value)
        state = tk.NORMAL if cond_2 else tk.DISABLED
        self.btn_add_and_filters['state'] = state
        self.btn_add_or_filters['state'] = state

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
        self.update_func(reset_page=True, update_filters=True)  # will call self.create_mask() and self.get_filter_mask()

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
        values = []
        for filter_name in self._filters:
            a_filter: FilterValue = self._filters[filter_name]  # cast to FilterValue because the loop variable is a string
            values.append(f'{a_filter!r}')
        values = '\n'.join(values)
        msg = values + '\n\nCopy values into clipboard ?'
        if messagebox.askyesno('View data filters', message=msg):
            self.clipboard_clear()
            self.clipboard_append(values)

    def get_quick_filter(self, only_return_filter=False) -> FilterValue:
        """
        Update the widgets that are used for filtering based on the selected column.
        :param only_return_filter: wether only return the filter string without applying it.
        :return: filter dict.
        """
        quick_filter_name = self.cb_quick_filter.get()
        state = tk.NORMAL if quick_filter_name else tk.DISABLED
        self.btn_apply_filters['state'] = state

        quick_filter = self._quick_filters.get(quick_filter_name, None)
        if quick_filter_name and quick_filter:
            if not only_return_filter:
                # self.create_mask(filter_dict.items()) # done in the line bellow
                self.update_func(reset_page=True, update_filters=True)
        return quick_filter
