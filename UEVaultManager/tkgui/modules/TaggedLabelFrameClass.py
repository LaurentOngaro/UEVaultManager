# coding=utf-8
"""
Class definition for :
- TaggedLabelFrame: a custom LabelFrame widget that allows child widgets to be identified by tags

"""
import tkinter as tk
from tkinter import ttk

from UEVaultManager.tkgui.modules.ExtendedWidgetClasses import WidgetType, ExtendedEntry, ExtendedText, ExtendedLabel, ExtendedCheckButton
from UEVaultManager.tkgui.modules.functions import log_error, tag_to_label


class TaggedLabelFrame(ttk.LabelFrame):
    """
    A custom LabelFrame widget that allows child widgets to be identified by tags.
    :param args: Args to pass to the widget
    :param kwargs: Kwargs to pass to the widget
    :return: TaggedLabelFrame instance
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tagged_child = {}
        self.pack_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.X, 'expand': False}
        self.pack_fw_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.X, 'expand': True}  # full width
        self.lblf_fw_options = {'ipadx': 2, 'ipady': 2, 'fill': tk.X, 'expand': True}

    def add_child(
        self,
        tag: str,
        widget_type: WidgetType.ENTRY,
        default_content=None,
        height=None,
        width=None,
        layout_option='',
        focus_out_callback=None
    ) -> None:
        """
        Adds a child widget to the LabelFrame and associates it with the given tag.
        :param tag: Tag to search for (case-insensitive)
        :param widget_type: Type of widget to add. A string value of 'text', 'checkbutton', or 'entry'
        :param width: Width of the child widget. Only used for text widgets
        :param height: Height of the child widget. Only used for text widgets
        :param default_content: Default content of the child widget
        :param layout_option: Layout options to use. Default, full width.
        :param focus_out_callback: Callback to call when the child widget loses focus
        """
        tag = tag.lower()
        frame = ttk.Frame(self)
        frame.pack(**self.lblf_fw_options)
        label = ttk.Label(frame, text=tag_to_label(tag))
        label.pack(side=tk.LEFT, **self.pack_options)

        widget_class = {
            WidgetType.ENTRY: (lambda **kwargs: ExtendedEntry)(master=frame, tag=tag, default_content=default_content, height=height, width=width),
            WidgetType.TEXT:
            (lambda **kwargs: ExtendedText)(master=frame, wrap=tk.WORD, tag=tag, default_content=default_content, height=height, width=width),
            WidgetType.LABEL: (lambda **kwargs: ExtendedLabel)(master=frame, tag=tag, default_content=default_content, height=height, width=width),
            WidgetType.CHECKBUTTON:
            (lambda **kwargs: ExtendedCheckButton)(master=frame, tag=tag, default_content=default_content, height=height, width=width)
        }.get(widget_type)
        if widget_class is None:
            log_error(f'Invalid widget type: {widget_type}')
            return

        child = widget_class(frame, tag=tag, default_content=default_content, height=height, width=width)
        self._tagged_child[tag] = child
        child.reset_content()

        layout_option = self.pack_fw_options if layout_option == '' else layout_option
        child.pack(side=tk.LEFT, **layout_option)

        if focus_out_callback is not None:
            child.bind('<FocusOut>', lambda event: focus_out_callback(event=event, tag=tag))

    def get_child_by_tag(self, tag: str):
        """
        Returns the child widget associated with the given tag.
        :param tag: Tag to search for (case-insensitive)
        :return: Child widget
        """
        tag = tag.lower()
        return self._tagged_child.get(tag)

    def get_children(self) -> dict:
        """
        Returns the dictionary of tagged children.
        :return: A dictionary of tagged children
        """
        return self._tagged_child

    def set_default_content(self, tag: str = '') -> None:
        """
        Sets the default content of the child widget associated with the given tag.
        :param tag: Tag to search for (case-insensitive)
        """
        tag = tag.lower()
        widget = self.get_child_by_tag(tag)
        if widget is not None:
            widget.set_content(widget.default_content)

    def set_child_values(self, tag: str = '', content: str = '', row: int = -1, col: int = -1) -> None:
        """
        Sets the content of the child widget associated with the given tag.
        Also sets its row and column index.
        :param tag: Tag to search for (case-insensitive)
        :param content: Content to set
        :param row: Row index to set
        :param col: Column index to set
        """
        tag = tag.lower()
        widget = self.get_child_by_tag(tag)
        if widget is not None:
            widget.set_content(content)
            widget.row = row
            widget.col = col
