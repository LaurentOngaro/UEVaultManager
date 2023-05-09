import tkinter
from tkinter import ttk

import tkinter as tk
from UEVaultManager.tkgui.modules.functions import log_warning


def set_child_content(child: tkinter.Widget = None, content=''):
    """
    Sets the content of the given child widget.
    :param child: child widget
    :param content: content to set
    """
    if child is not None:
        try:
            widget_class = child.winfo_class().lower()
            if 'entry' in widget_class:
                # noinspection PyUnresolvedReferences
                child.delete(0, tk.END)
                # noinspection PyUnresolvedReferences
                child.insert(0, content)
            elif 'label' in widget_class:
                # noinspection PyUnresolvedReferences
                child.config(text=content)
        except Exception:
            log_warning(f'Failed to set content of {child} to {content}')


class TaggedLabelFrame(ttk.LabelFrame):
    """
    A custom LabelFrame widget that allows child widgets to be identified by tags.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tagged_child = {}
        self._default_content = {}
        self._col = {}
        self._row = {}
        self.pack_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.X, 'expand': False}
        self.pack_fw_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.X, 'expand': True}  # full width
        self.lblf_fw_options = {'ipadx': 2, 'ipady': 2, 'fill': tk.X, 'expand': True}

    def add_child(self, tag: str, default_content='', layout_option='', focus_out_callback=None):
        """
        Adds a child widget to the LabelFrame and associates it with the given tag.
        :param tag: tag to search for (case-insensitive)
        :param default_content: default content of the child widget
        :param layout_option: layout options to use
        :param focus_out_callback: callback to call when the child widget loses focus
        """
        tag = tag.lower()
        self._default_content[tag] = default_content
        frame = ttk.Frame(self)
        frame.pack(**self.lblf_fw_options)
        label = ttk.Label(frame, text=tag)
        # label.grid(row=0, column=0, **layout_option)
        label.pack(side=tk.LEFT, **self.pack_options)
        entry = ttk.Entry(frame)
        # entry.grid(row=0, column=1, **layout_option)
        layout_option = self.pack_fw_options if layout_option == '' else layout_option
        entry.pack(side=tk.LEFT, **layout_option)

        self._tagged_child[tag] = entry

        set_child_content(entry, default_content)
        if focus_out_callback is not None:
            # child.bind('<FocusOut>', lambda event: focus_out_callback(event, child))
            entry.bind('<FocusOut>', lambda event: focus_out_callback(event=event, tag=tag))

    def get_child_by_tag(self, tag: str):
        """
        Returns the child widget associated with the given tag.
        :param tag: tag to search for (case-insensitive)
        :return: child widget
        """
        tag = tag.lower()
        return self._tagged_child.get(tag, None)

    def get_row_by_tag(self, tag: str) -> int:
        """
        Returns the row index associated with the given tag.
        :param tag: tag to search for (case-insensitive)
        :return: row index or -1 if not found
        """
        tag = tag.lower()
        return self._row.get(tag, -1)

    def get_col_by_tag(self, tag: str) -> int:
        """
        Returns the column index associated with the given tag.
        :param tag: tag to search for (case-insensitive)
        :return: column index or -1 if not found
        """
        tag = tag.lower()
        return self._col.get(tag, -1)

    def get_tagged_children(self) -> dict:
        """
        Returns the child widget associated with the given tag.
        :return: a dictionary of tagged children
        """
        return self._tagged_child

    def get_default_content_by_tag(self, tag: str):
        """
        Returns the child default content associated with the given tag.
        :param tag: tag to search for (case-insensitive)
        """
        tag = tag.lower()
        return self._default_content.get(tag, '')

    def set_default_content(self, tag=''):
        """
        Sets the default content of the child widget associated with the given tag.
        :param tag: tag to search for (case-insensitive)
        """
        tag = tag.lower()
        widget = self.get_child_by_tag(tag)
        default_content = self.get_default_content_by_tag(tag)
        set_child_content(widget, default_content)

    def set_content(self, tag='', content='', row=-1, col=-1):
        """
        Sets the content of the child widget associated with the given tag.
        Also sets its row and column index.
        :param tag: tag to search for (case-insensitive)
        :param content: content to set
        :param row: row index to set
        :param col: column index to set
        """
        tag = tag.lower()
        widget = self.get_child_by_tag(tag)
        if widget is None:
            return
        set_child_content(widget, content)
        self._row[tag] = row
        self._col[tag] = col
