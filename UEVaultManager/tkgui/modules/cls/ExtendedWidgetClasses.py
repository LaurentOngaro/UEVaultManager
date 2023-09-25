# coding=utf-8
"""
Implementation for:
- ExtendedWidget: base class for all widgets in the app
- ExtendedEntry: extended entry widget
- ExtendedText: extended text widget
- ExtendedLabel: extended label widget
- ExtendedCheckButton: extended checkbutton widget
- ExtendedButton: extended button widget.
"""
import inspect
import tkinter as tk
from tkinter import ttk
from tkinter.font import nametofont

from UEVaultManager.lfs.utils import path_join
from UEVaultManager.tkgui.modules.functions import log_warning
from UEVaultManager.tkgui.modules.functions_no_deps import path_from_relative_to_absolute
from UEVaultManager.tkgui.modules.types import WidgetType


class ExtendedWidget:
    """
    Base class for all widgets in the app.
    :param tag: tag of the widget.
    :param row: row of the widget.
    :param col: column of the widget.
    :return: extendedWidget instance.
    """

    def __init__(self, tag=None, row: int = -1, col: int = -1, default_content=''):
        self.tag: str = tag
        self.col: int = col
        self.row: int = row
        self.default_content = default_content if default_content is not None else self.tag_to_label(tag)

        # can't call this here because the set_content function is specific and overridden in the derived classes
        # self.reset_content()

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
        :return: dict of extended args.
        """
        init_args = inspect.signature(function_signature)
        result = {}
        for key in init_args.parameters:
            if key == 'self':
                continue
            result[key] = kwargs.pop(key, None)
        return result

    @staticmethod
    def tag_to_label(tag: str or None) -> str:
        """
        Convert a tag to a label.
        :param tag: the tag to convert.
        :return: the label.
        """
        if tag is None:
            return ''

        return tag.capitalize().replace('_', ' ')

    def set_content(self, content='') -> None:
        """
        Sets the content of the widget.
        :param content: content to set.
        """
        try:
            # noinspection PyUnresolvedReferences
            self.config(text=content)
        except (AttributeError, tk.TclError) as error:
            log_warning(f'Failed to set content of {self} to {content}: {error!r}')

    def get_content(self) -> str:
        """
        Get the content of the widget.
        :return: content of the widget.
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
        :return: ttk.Style object.
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
        :return: the default font for ttk widgets.
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
    :param master: container for the widget.
    :param label: text to display next to the checkbutton.
    :param kwargs: kwargs to pass to the widget.
    :return: extendedEntry instance.
    """

    def __init__(self, master=None, **kwargs):
        if master is None:
            print('A container is needed to display this widget')
            return
        ext_args = self._extract_extended_args(kwargs, function_signature=ExtendedWidget.__init__)
        ExtendedWidget.__init__(self, **ext_args)
        # already made with _extract_extended_args
        # self._remove_extended_args(kwargs, function_signature=ExtendedWidget.__init__)
        ttk.Entry.__init__(self, master=master, **kwargs)
        self.widget_type = WidgetType.ENTRY

    def set_content(self, content='') -> None:
        """
        Sets the content of the widget.
        :param content: content to set.
        """
        self.delete(0, tk.END)
        self.insert(0, content)


class ExtendedText(ExtendedWidget, tk.Text):
    """
    Extended widget version of a ttk.Text. Also add a "ttk.style" like property to the widget.
    :param master: container for the widget.
    :param kwargs: kwargs to pass to the widget.
    :return: extendedText instance.
    """

    def __init__(self, master=None, **kwargs):
        if master is None:
            print('A container is needed to display this widget')
            return
        ext_args = self._extract_extended_args(kwargs, function_signature=ExtendedWidget.__init__)
        ExtendedWidget.__init__(self, **ext_args)

        # already made with _extract_extended_args
        # self._remove_extended_args(kwargs, function_signature=ExtendedWidget.__init__)
        tk.Text.__init__(self, master=master, **kwargs)
        self.widget_type = WidgetType.TEXT
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
        :param content: content to set.
        """
        try:
            self.delete('1.0', tk.END)
            self.insert('1.0', content)
        except (AttributeError, tk.TclError) as error:
            log_warning(f'Failed to set content of {self} to {content}: {error!r}')

    def get_content(self) -> str:
        """
        Get the content of the widget.
        :return: content of the widget.
        """
        try:
            # Note that by using END you're also getting the trailing newline that tkinter automatically adds.
            # You might want to use "end-1c"
            # return self.get('1.0', tk.END)
            return self.get('1.0', 'end-1c')
        except (AttributeError, tk.TclError) as error:
            log_warning(f'Failed to get content of {self}: {error!r}')
            return ''


class ExtendedLabel(ExtendedWidget, ttk.Label):
    """
    Extended widget version of a ttk.Label.
    :param master: container for the widget.
    :param text: text to display next to the checkbutton.
    :param kwargs: kwargs to pass to the widget.
    :return: extendedLabel instance.
    """

    def __init__(self, master=None, **kwargs):
        if master is None:
            print('A container is needed to display this widget')
            return
        ext_args = self._extract_extended_args(kwargs, function_signature=ExtendedWidget.__init__)
        ExtendedWidget.__init__(self, **ext_args)
        # already made with _extract_extended_args
        # self._remove_extended_args(kwargs, function_signature=ExtendedWidget.__init__)
        ttk.Label.__init__(self, master=master, **kwargs)
        self.widget_type = WidgetType.LABEL


class ExtendedCheckButton(ExtendedWidget):
    """
    Create a new widget version of a ttk.Checkbutton.
    :param master: parent widget.
    :param label: text to display next to the checkbutton.
    :param images_folder: path to the folder containing the images for the checkbutton. If empty, the './assets' folder will be used.
    :param change_state_on_click: whether the state of the checkbutton will change when clicking on the text or the checkbutton. if not, the change must be done manually by calling the switch_state method.
    :param kwargs: kwargs to pass to the widget.
    :return: extendedCheckButton instance.

    Notes:
        We don't use the ttk.Checkbutton because it's hard to sync its state when using the on_click event.
    """
    default_content = False

    def __init__(self, master, label: str = None, images_folder: str = '', change_state_on_click: bool = True, **kwargs):
        if master is None:
            print('A container is needed to display this widget')
            return
        ext_args = self._extract_extended_args(kwargs, function_signature=ExtendedWidget.__init__)
        ExtendedWidget.__init__(self, **ext_args)
        # by default , images are searched in a folder named 'statics' in the directory of this file
        if not images_folder:
            images_folder = path_from_relative_to_absolute('./assets/')
        self._img_checked = tk.PhotoImage(file=path_join(images_folder, 'checked_16.png'))  # Path to the checked image
        self._img_uncheckked = tk.PhotoImage(file=path_join(images_folder, 'unchecked_16.png'))  # Path to the unchecked image
        self.widget_type = WidgetType.CHECKBUTTON
        self._var = tk.BooleanVar(value=bool(self.default_content))
        frm_inner = ttk.Frame(master=master)
        lbl_text = ttk.Label(frm_inner, text='')  # no text bydefault
        lbl_check = ttk.Label(frm_inner, image=self._img_uncheckked, cursor='hand2')
        lbl_text.pack(side=tk.LEFT)
        lbl_check.pack(side=tk.LEFT)
        self._frm_inner = frm_inner
        self._lbl_text = lbl_text
        self._lbl_check = lbl_check

        if label is not None:
            self.set_label(label)
        # noinspection PyTypeChecker
        # keep "bad" type to keep compatible signatures with overriden methods
        self.set_content(bool(self.default_content))

        if change_state_on_click:
            self.bind("<Button-1>", self.switch_state)

    def _update_state(self) -> None:
        """
        Updates the image of the checkbutton.
        """
        current_state = self._var.get()
        if current_state:
            self._lbl_check.config(image=self._img_checked)
        else:
            self._lbl_check.config(image=self._img_uncheckked)

    def pack(self, **kwargs) -> None:
        """
        Packs the widget.
        :param kwargs: kwargs to pass to the widget.
        """
        self._frm_inner.pack(**kwargs)

    def grid(self, **kwargs) -> None:
        """
        Grids the widget.
        :param kwargs: kwargs to pass to the widget.
        """
        self._frm_inner.grid(**kwargs)

    def bind(self, sequence=None, command=None) -> None:
        """
        Binds a callback to the widget.
        :param sequence: sequence to bind to.
        :param command:  function to bind.
        """
        self._lbl_text.bind(sequence, command)
        self._lbl_check.bind(sequence, command)

    # noinspection PyUnusedLocal
    def switch_state(self, event=None) -> bool:
        """
        Switches the state of the checkbutton.
        :param event: event that triggered the call.
        """
        value = bool(self._var.get())
        # print(f'Current state: {value} event: {event}   ')
        value = not value
        self._var.set(value)
        self._update_state()
        return value

    def set_label(self, text='') -> None:
        """
        Sets the label of the widget.
        :param text: text to set.
        """
        self._lbl_check.config(text=text)

    def set_content(self, content='') -> None:
        """
        Sets the content of the widget. True, 'True' and '1' will be considered as True, everything else will be considered as False.
        :param content: content to set.
        """
        try:
            if content or type(content) is bool:
                # noinspection PyTypeChecker
                # keep "bad" type to keep compatible signatures with overriden methods
                self._var.set(content)
            elif bool(content):
                self._var.set(True)
            elif not bool(content):
                self._var.set(False)
            elif (content.lower() == 'true') or (content == '1'):
                self._var.set(True)
            else:
                self._var.set(False)

            self._update_state()
        except (AttributeError, tk.TclError) as error:
            log_warning(f'Failed to set content of {self} to {content}: {error!r}')

    def get_content(self) -> bool:
        """
        Get the content of the widget.
        :return: True if the checkbutton is checked, False otherwise.
        """
        return bool(self._var.get())


class ExtendedButton(ExtendedWidget, ttk.Button):
    """
    Extended widget version of a ttk.Button.
    :param master: container for the widget.
    :param command: function to call when the button is clicked.
    :param kwargs: kwargs to pass to the widget.
    :return: extendedButton instance.
    """

    def __init__(self, master=None, command: str = '', **kwargs):
        if master is None:
            print('A container is needed to display this widget')
            return
        ext_args = self._extract_extended_args(kwargs, function_signature=ExtendedWidget.__init__)
        ExtendedWidget.__init__(self, **ext_args)
        # already made with _extract_extended_args
        # self._remove_extended_args(kwargs, function_signature=ExtendedWidget.__init__)
        ttk.Button.__init__(self, master=master, command=command, **kwargs)
        self.widget_type = WidgetType.BUTTON
