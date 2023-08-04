# coding=utf-8
"""
Implementation for:
- TaggedLabelFrame: a custom LabelFrame widget that allows child widgets to be identified by tags.
"""
from UEVaultManager.tkgui.modules.cls.ExtendedWidgetClasses import *
from UEVaultManager.tkgui.modules.functions import log_error, log_warning, log_debug
from UEVaultManager.tkgui.modules.types import WidgetType


class TaggedLabelFrame(ttk.LabelFrame):
    """
    A custom LabelFrame widget that allows child widgets to be identified by tags.
    :param args: Args to pass to the widget.
    :param kwargs: Kwargs to pass to the widget.
    :return: TaggedLabelFrame instance.
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
        alternate_container=None,
        default_content=None,
        width=None,
        height=None,
        label=None,
        layout_option='',
        images_folder=None,
        add_label_before=True,
        focus_out_callback=None,
        focus_in_callback=None,
        click_on_callback=None
    ):
        """
        Adds a child widget to the LabelFrame and associates it with the given tag.
        :param tag: Tag to search for (case-insensitive).
        :param widget_type: Type of widget to add.
        :param alternate_container: Alternate container to use for the child widget. If None, uses the TaggedLabelFrame.
        :param width: Width of the child widget. Only used for text widgets.
        :param height: Height of the child widget. Only used for text widgets.
        :param label: Text to display in the child widget.
        :param default_content: Default content of the child widget.
        :param layout_option: Layout options to use. Default, full width.
        :param images_folder: folder for image used by some widgets.
        :param add_label_before: If True, adds a label before the child widget.
        :param focus_out_callback: Callback to call when the child widget loses focus.
        :param focus_in_callback: Callback to call when the child widget get focus.
        :param click_on_callback: Callback to call when the child widget is clicked or checked.
        :return: Child widget

        Notes:
        we can not use command parameter to manage callback here because it should be transmited
        to the parent widget and in that case tag won't be available as an indentificator.
        If alternate_container is not None, the widget the layout of the child must be managed by the caller.
        """
        tag = tag.lower()
        if alternate_container is None:
            frame = ttk.Frame(self)
            frame.pack(**self.lblf_fw_options)
        else:
            frame = alternate_container
        if add_label_before:
            lbl_name = ttk.Label(frame, text=ExtendedWidget.tag_to_label(tag))
            lbl_name.pack(side=tk.LEFT, **self.pack_options)
        if widget_type == WidgetType.ENTRY:
            child = ExtendedEntry(master=frame, tag=tag, default_content=default_content, height=height, width=width)
        elif widget_type == WidgetType.TEXT:
            child = ExtendedText(master=frame, tag=tag, default_content=default_content, wrap=tk.WORD, height=height, width=width)
        elif widget_type == WidgetType.LABEL:
            child = ExtendedLabel(master=frame, tag=tag, default_content=default_content)
        elif widget_type == WidgetType.CHECKBUTTON:
            child = ExtendedCheckButton(master=frame, tag=tag, default_content=default_content, label=label, images_folder=images_folder)
        elif widget_type == WidgetType.BUTTON:
            child = ExtendedButton(master=frame, tag=tag, default_content=default_content)
        else:
            error = f'Invalid widget type: {widget_type}'
            log_error(error)
            return None

        self._tagged_child[tag] = child

        layout_option = self.pack_fw_options if layout_option == '' else layout_option
        child.pack(side=tk.LEFT, **layout_option)

        if focus_out_callback is not None:
            child.bind('<FocusOut>', lambda event: focus_out_callback(event=event, tag=tag))
        if focus_in_callback is not None:
            child.bind('<FocusIn>', lambda event: focus_in_callback(event=event, tag=tag))
        if click_on_callback is not None:
            child.bind('<Button-1>', lambda event: click_on_callback(event=event, tag=tag))
        return child

    def get_child_by_tag(self, tag: str):
        """
        Return the child widget associated with the given tag.
        :param tag: Tag to search for (case-insensitive).
        :return: Child widget.
        """
        tag = tag.lower()
        return self._tagged_child.get(tag)

    def get_children(self) -> dict:
        """
        Return the dictionary of tagged children.
        :return: A dictionary of tagged children.
        """
        return self._tagged_child

    def set_default_content(self, tag='') -> None:
        """
        Set the default content of the child widget associated with the given tag.
        :param tag: Tag to search for (case-insensitive).
        """
        tag = tag.lower()
        widget = self.get_child_by_tag(tag)
        if widget is not None:
            widget.set_content(widget.default_content)

    def set_child_values(self, tag='', content='', label=None, row: int = -1, col: int = -1) -> None:
        """
        Set the content of the child widget associated with the given tag.
        Also sets its row and column index.
        :param tag: Tag to search for (case-insensitive).
        :param label: Text to set (only for CheckButton widget).
        :param content: Content to set.
        :param row: Row index to set.
        :param col: Column index to set.
        """
        tag = tag.lower()
        widget = self.get_child_by_tag(tag)
        if widget is not None:
            widget.set_content(content)
            widget.row = row
            widget.col = col
            if label is not None:
                try:
                    widget.set_label(label)
                except AttributeError:
                    log_debug(f'Widget with tag {tag} does not have a set_label method')
        else:
            log_warning(f'Widget with tag {tag} not found')
