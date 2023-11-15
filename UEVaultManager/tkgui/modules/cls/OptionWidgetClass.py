# coding=utf-8
"""
Implementation for:
- OptionWidget: a widget for an option/setting.
"""
import tkinter as tk
from typing import Optional

import ttkbootstrap as ttk

import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.functions import update_loggers_level


class OptionWidget:
    """
    A widget for an option/setting.
    :param name: name of the setting.
    :param vtype: type of the setting.
    :param label: label of the widget.
    :param container: parent container.
    :param cur_row: current row.
    :param cur_col: current column.
    :param grid_options: grid options.
    :param is_cli: is the setting for the CLI.
    :param colspan: column span.
    :param callback: callback function to call when the widget value changes.
    """

    def __init__(
        self,
        name: str,
        vtype: str,
        label: str,
        container,
        cur_row: int,
        cur_col: int,
        grid_options: dict,
        is_cli: bool = False,
        colspan: int = 2,
        callback: callable = None
    ):
        self._container = container
        self._widget_label: Optional[tk.Label] = None
        self._trace_name: str = ''
        self.name = name
        self.vtype = vtype
        self.label = label
        self.is_cli = is_cli
        self.widget: Optional[tk.Widget] = None
        self._var = None
        self.cur_row = cur_row
        self.cur_col = cur_col
        self.colspan = colspan
        self.grid_options = grid_options
        self.callback = callback

    def setup(self):
        """ Set up the widget. """
        grid_e_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'sticky': tk.E}
        setting = self.get_setting()
        if self.vtype == 'bool':
            self._var = tk.BooleanVar(value=setting)
            self.widget = ttk.Checkbutton(self._container, text=self.label, variable=self._var)
            self._widget_label = None
            self.widget.grid(row=self.cur_row, column=self.cur_col + 1, columnspan=self.colspan, **self.grid_options)
        elif self.vtype == 'int' or self.vtype == 'str':
            self._var = tk.IntVar(value=setting)
            self._widget_label = ttk.Label(self._container, text=self.label)
            self._widget_label.grid(row=self.cur_row, column=self.cur_col, **grid_e_options)
            self.widget = ttk.Entry(self._container, textvariable=self._var)
            self.widget.grid(row=self.cur_row, column=self.cur_col + 1, columnspan=self.colspan - 1, **self.grid_options)
        self.trace_on()

    def trace_on(self):
        """ Turn on trace. """
        self._trace_name = self._var.trace_add('write', lambda name, index, mode: self.set_setting())

    def trace_off(self):
        """ Turn off trace. """
        self._var.trace_remove('write', self._trace_name)

    def set_value(self, value):
        """ Set the widget value (i.e. change the associated variable value). """
        self._var.set(value)

    def get_setting(self):
        """ Get the associated setting value."""
        if self.is_cli:
            # from the CLI object args
            setting = gui_g.UEVM_cli_args.get(self.name)
        else:
            # from the GUISettings object
            # get the property of the GUISettings class wich name is self.name
            setting = getattr(gui_g.s, self.name)
        return setting

    def set_setting(self):
        """ Set the associated setting value."""
        setting = self._var.get()
        if self.is_cli:
            # to the CLI object args
            gui_g.UEVM_cli_args.set(self.name, setting)
        else:
            # to the GUISettings object
            setattr(gui_g.s, self.name, setting)
        # special action for some values
        if self.name == 'debug_mode':
            update_loggers_level(debug_value=setting)

        # update the control state
        self.callback() if self.callback else None
