# coding=utf-8
"""
Implementation for:
- WidgetType: enum for the widget types
- ExtendedWidget: base class for all widgets in the app
- ExtendedEntry: extended entry widget
- ExtendedText: extended text widget
- ExtendedLabel: extended label widget
- ExtendedCheckButton: extended checkbutton widget
"""

import inspect
import tkinter as tk
from enum import Enum
from tkinter import ttk
from tkinter.font import nametofont

from UEVaultManager.tkgui.modules.functions import log_warning, tag_to_label


class WidgetType(Enum):
    """
    Enum for the widget types
    """
    ENTRY = 0  # Entry widget
    TEXT = 1  # Text widget
    LABEL = 2  # Label widget
    CHECKBUTTON = 3  # Checkbutton widget


class ExtendedWidget:
    """
    Base class for all widgets in the app.
    :param tag: tag of the widget
    :param row: row of the widget
    :param col: column of the widget
    :return: ExtendedWidget instance
    """

    def __init__(self, tag=None, row=-1, col=-1, default_content=''):
        self.tag = tag
        self.col = col
        self.row = row
        self.default_content = default_content if default_content else tag_to_label(tag)

    @staticmethod
    def _remove_extended_args(kwargs, function_signature) -> None:
        """
        Removes the extended args from the kwargs.
        :param kwargs: args to extract from.
        :param function_signature: function to get the signature from. We can't use a non-static method because the init function will be the derived class's init function.
        """
        init_args = inspect.signature(function_signature)
        for key in init_args.parameters:
            kwargs.pop(key, None)

    @staticmethod
    def _extract_extended_args(kwargs, function_signature) -> dict:
        """
        Extracts the extended args from the kwargs.
        :param kwargs: args to extract from. Note that the kwargs will be modified and the extended args will be removed.
        :param function_signature: function to get the signature from. We can't use a non-static method because the init function will be the derived class's init function.
        :return: dict of extended args
        """
        init_args = inspect.signature(function_signature)
        result = {}
        for key in init_args.parameters:
            if key == 'self':
                continue
            result[key] = kwargs.pop(key, None)
        return result

    def set_content(self, content='') -> None:
        """
        Sets the content of the widget.
        :param content: content to set
        """
        try:
            # noinspection PyUnresolvedReferences
            self.config(text=content)
        except (AttributeError, tk.TclError) as error:
            log_warning(f'Failed to set content of {self} to {content}: {error!r}')

    def get_content(self) -> str:
        """
        Gets the content of the widget.
        :return: content of the widget
        """
        try:
            # noinspection PyUnresolvedReferences
            return self.get()
        except (AttributeError, tk.TclError) as error:
            log_warning(f'Failed to get content of {self}: {error!r}')
            return ''

    def reset_content(self) -> None:
        """
        Resets the content of the widget to the default content.
        """
        self.set_content(self.default_content)

    def get_style(self) -> ttk.Style:
        """
        Get the ttk.Style object of the widget.
        :return: ttk.Style object
        """
        try:
            # noinspection PyUnresolvedReferences
            style = self.winfo_toplevel().style  # only works if the widget is a child of UEVMGui,
        except AttributeError:
            try:
                # noinspection PyProtectedMember
                root = tk._default_root.style
                style_name = root.theme_use()
                style = root.Style(style_name)
            except AttributeError:
                style = None
        return style

    def get_default_font(self) -> tk.font.Font:
        """
        Get the default font for ttk widgets. If the default font is not found, use the TkDefaultFont.
        :return: The default font for ttk widgets.
        """
        default_font = nametofont("TkDefaultFont")
        style = self.get_style()
        if style is not None:
            default_font = style.lookup("TEntry", "font")
            if default_font == '':
                # noinspection PyUnresolvedReferences
                default_font = self.cget("font")

        return default_font


class ExtendedEntry(ExtendedWidget, ttk.Entry):
    """
    Extended widget version of a ttk.Entry class.
    :param master: master widget
    :param kwargs: kwargs to pass to the widget
    :return: ExtendedEntry instance
    """

    def __init__(self, master=None, **kwargs):
        ext_args = self._extract_extended_args(kwargs, function_signature=ExtendedWidget.__init__)
        ExtendedWidget.__init__(self, **ext_args)
        # already made with _extract_extended_args
        # self._remove_extended_args(kwargs, function_signature=ExtendedWidget.__init__)
        ttk.Entry.__init__(self, master, **kwargs)
        self.type: WidgetType.ENTRY

    def set_content(self, content='') -> None:
        """
        Sets the content of the widget.
        :param content: content to set
        """
        self.delete(0, tk.END)
        self.insert(0, content)


class ExtendedText(ExtendedWidget, tk.Text):
    """
    Extended widget version of a ttk.Text. Also add a "ttk.style" like property to the widget.
    :param master: master widget
    :param kwargs: kwargs to pass to the widget
    :return: ExtendedText instance
    """

    def __init__(self, master=None, **kwargs):
        ext_args = self._extract_extended_args(kwargs, function_signature=ExtendedWidget.__init__)
        ExtendedWidget.__init__(self, **ext_args)

        # already made with _extract_extended_args
        # self._remove_extended_args(kwargs, function_signature=ExtendedWidget.__init__)
        tk.Text.__init__(self, master, **kwargs)
        self.type: WidgetType.TEXT
        self.update_style()

    def update_style(self) -> None:
        """
        Update the style of the widget based on a ttk.Entry widget.
        """
        style = self.get_style()

        if style is None:
            return
        # get some style from the ttk.Entry widget
        font = self.get_default_font()
        bg_color = style.lookup('TEntry', 'fieldbackground', default='white')
        fg_color = style.lookup('TEntry', 'foreground', default='black')
        relief = style.lookup('TEntry', 'relief', default='flat')
        # border_color = style.lookup('TEntry', 'bordercolor', default='black')
        self.configure(background=bg_color, foreground=fg_color, borderwidth=1, relief=relief, font=font)

    def set_content(self, content='') -> None:
        """
        Sets the content of the widget.
        :param content: content to set
        """
        try:
            self.delete('1.0', tk.END)
            self.insert('1.0', content)
        except (AttributeError, tk.TclError) as error:
            log_warning(f'Failed to set content of {self} to {content}: {error!r}')

    def get_content(self) -> str:
        """
        Gets the content of the widget.
        :return: content of the widget
        """
        try:
            return self.get('1.0', tk.END)
        except (AttributeError, tk.TclError) as error:
            log_warning(f'Failed to get content of {self}: {error!r}')
            return ''


class ExtendedLabel(ExtendedWidget, ttk.Label):
    """
    Extended widget version of a ttk.Label.
    :param master: master widget
    :param kwargs: kwargs to pass to the widget
    :return: ExtendedLabel instance
    """

    def __init__(self, master=None, **kwargs):
        ext_args = self._extract_extended_args(kwargs, function_signature=ExtendedWidget.__init__)
        ExtendedWidget.__init__(self, **ext_args)
        # already made with _extract_extended_args
        # self._remove_extended_args(kwargs, function_signature=ExtendedWidget.__init__)
        ttk.Label.__init__(self, master, **kwargs)
        self.type: WidgetType.LABEL


class ExtendedCheckButton(ExtendedWidget, ttk.Checkbutton):
    """
    Extended widget version of a ttk.Checkbutton.
    :param master: master widget
    :param kwargs: kwargs to pass to the widget
    :return: ExtendedCheckButton instance
    """

    def __init__(self, master=None, **kwargs):
        ext_args = self._extract_extended_args(kwargs, function_signature=ExtendedWidget.__init__)
        ExtendedWidget.__init__(self, **ext_args)
        # already made with _extract_extended_args
        # self._remove_extended_args(kwargs, function_signature=ExtendedWidget.__init__)
        ttk.Checkbutton.__init__(self, master, **kwargs)
        self.type: WidgetType.CHECKBUTTON
        self.default_content = False

    def set_content(self, content=''):
        """
        Sets the content of the widget.
        :param content: content to set
        """
        try:
            content = str(content).capitalize()
            if content or (content == 'True') or (content == '1'):
                # noinspection PyUnresolvedReferences
                self.select()
            else:
                # noinspection PyUnresolvedReferences
                self.deselect()
        except (AttributeError, tk.TclError) as error:
            log_warning(f'Failed to set content of {self} to {content}: {error!r}')

    def get_content(self):
        """
        Gets the content of the widget.
        :return: content of the widget
        """
        try:
            return self.instate(['selected'])
        except (AttributeError, tk.TclError) as error:
            log_warning(f'Failed to get content of {self}: {error!r}')
            return None
