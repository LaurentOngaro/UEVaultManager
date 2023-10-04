# coding=utf-8
"""
Implementation for:
- EditCellWindow: the window to edit a cell.
"""
import tkinter as tk
from tkinter import ttk

from ttkbootstrap import INFO, WARNING

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience


class EditCellWindow(tk.Toplevel):
    """
    The window to edit a cell.
    :param parent: the parent window.
    :param title: the title of the window.
    :param width: the width of the window.
    :param height: the height of the window.
    :param icon: the icon of the window.
    :param screen_index: the index of the screen on which the window will be displayed.
    :param editable_table: the table to edit.
    """

    def __init__(self, parent, title: str, width: int = 600, height: int = 400, icon=None, screen_index: int = 0, editable_table=None):
        super().__init__(parent)
        self.title(title)
        try:
            # an error can occur here AFTER a tool window has been opened and closed (ex: db "import/export")
            self.style = gui_fn.set_custom_style(gui_g.s.theme_name, gui_g.s.theme_font)
        except Exception as error:
            gui_f.log_warning(f'Error in EditCellWindowClass: {error!r}')
        self.geometry(gui_fn.center_window_on_screen(screen_index, width, height))
        gui_fn.set_icon_and_minmax(self, icon)
        self.resizable(True, False)

        self.editable_table = editable_table
        self.must_save: bool = False
        self.initial_values = []
        self.frm_content = self.ContentFrame(self)
        self.frm_control = self.ControlFrame(self)

        self.frm_content.pack(ipadx=5, ipady=5, padx=5, pady=5, fill=tk.X)
        self.frm_control.pack(ipadx=5, ipady=5, padx=5, pady=5, fill=tk.X)

        self.bind('<Tab>', self._focus_next_widget)
        self.bind('<Control-Tab>', self._focus_next_widget)
        self.bind('<Shift-Tab>', self._focus_prev_widget)
        self.bind('<Key>', self.on_key_press)
        self.bind('<Button-1>', self.on_left_click)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        gui_g.edit_cell_window_ref = self
        # gui_f.make_modal(self)  # could cause issue if done in the init of the class. better to be done by the caller
        self.update_controls_state()

    @staticmethod
    def _focus_next_widget(event):
        event.widget.tk_focusNext().focus()
        return 'break'

    @staticmethod
    def _focus_prev_widget(event):
        event.widget.tk_focusPrev().focus()
        return 'break'

    class ContentFrame(ttk.Frame):
        """
        The frame containing the content of the window.
        :param container: the container of the frame.
        """

        def __init__(self, container):
            super().__init__(container)

    class ControlFrame(ttk.Frame):
        """
        The frame containing the control buttons of the window.
        :param container: the container of the frame.
        """

        def __init__(self, container):
            super().__init__(container)
            grid_def_options = {'ipadx': 5, 'ipady': 5, 'padx': 2, 'pady': 2, 'sticky': tk.NSEW}
            ttk.Label(self, text='Respect the initial format when changing a value').grid(row=0, column=0, columnspan=2, **grid_def_options)
            # noinspection PyArgumentList
            # (bootstyle is not recognized by PyCharm)
            btn_save_cell = ttk.Button(self, text='Save Changes', command=container.save_changes, bootstyle=INFO)
            btn_save_cell.grid(row=1, column=0, **grid_def_options)
            # noinspection PyArgumentList
            # (bootstyle is not recognized by PyCharm)
            ttk_item = ttk.Button(self, text='Close', command=container.on_close, bootstyle=WARNING)
            ttk_item.grid(row=1, column=1, **grid_def_options)

            self.columnconfigure('all', weight=1)
            self.rowconfigure('all', weight=1)

            widget_list = gui_g.stated_widgets.get('table_has_changed', [])
            gui_fn.append_no_duplicate(widget_list, btn_save_cell)

    def set_size(self, width: int, height: int) -> None:
        """
        Set the size (aka geometry) the window.
        :param width: the width.
        :param height: the height
        
        Notes:
            The window is centered on the screen.
        """
        geometry = gui_fn.center_window_on_screen(0, width, height)
        self.geometry(geometry)

    # noinspection DuplicatedCode
    def on_key_press(self, event):
        """
        Event when a key is pressed.
        :param event: the event that triggered the call of this function.
        """
        self.update_controls_state()
        control_pressed = event.state == 4 or event.state & 0x00004 != 0
        if event.keysym == 'Escape':
            self.on_close()
        elif control_pressed and (event.keysym == 's' or event.keysym == 'S'):
            self.save_changes()
        return 'break'

    # noinspection PyUnusedLocal
    def on_left_click(self, event=None) -> None:
        """
        When the left mouse button is clicked, show the selected row in the quick edit frame.
        :param event:
        """
        self.update_controls_state()  # to update when clicking on the checkbox

    def on_close(self, _event=None) -> None:
        """
        Event when the window is closing.
        :param _event: the event that triggered the call of this function.
        """
        if self.must_save:
            if gui_f.box_yesno('Changes have been made in the window. Do you want to keep them ?'):
                self.save_changes()
        self.close_window()

    def close_window(self) -> None:
        """
        Close the window.
        """
        gui_g.edit_cell_window_ref = None
        self.editable_table.reset_style()
        self.destroy()

    def save_changes(self) -> None:
        """
        Save the changes made in the window  (Wrapper).
        """
        self.must_save = False
        self.editable_table.save_edit_cell_value()

    def update_controls_state(self) -> None:
        """
        Update some controls in the window depending on conditions
        """
        current_values = self.editable_table.get_edit_cell_values()
        # current_values is empty if save_button has been pressed because global variables have been cleared in save_changess()
        self.must_save = self.initial_values != current_values
        gui_f.update_widgets_in_list(self.must_save, 'table_has_changed')
