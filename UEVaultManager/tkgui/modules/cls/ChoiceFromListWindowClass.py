# coding=utf-8
"""
Implementation for:
- ChoiceFromListWindow: Window to select a value in a list
"""
import tkinter as tk
from tkinter import ttk

from ttkbootstrap import INFO, WARNING

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience


class CFLW_Settings:
    """
    Settings for the class when running as main.
    """
    title = 'Choose the version'
    show_validate_button = True
    show_delete_button = False
    choices = {
        'Label1': {
            'value': 'id1',
            'desc': 'this is the description 1'
        },  #
        'Label2': {
            'value': 'id2',
            'desc': 'this is the description 2'
        },  #
        'Label3': {
            'value': 'id3',
            'desc': 'this is the description 3'
        },  #
        'Label4': {
            'value': 'id4',
            'desc': 'this is the description 4'
        },  #
    }


class ChoiceFromListWindow(tk.Toplevel):
    """
    Window to select a value in a list
    :param window_title: the window title.
    :param title: the title.
    :param width: the width.
    :param height: the height.
    :param icon: the icon.
    :param screen_index: the screen index.
    :param choices: the dict for choices to display. Must be formatted as { 'Label1': { 'value': 'id1', 'desc': 'this is the description 1' }, }
    :param default_value: the default value to return if no value is selected. If None, the set_value_func method will not be called on closed window.
    :param show_delete_button: if True, the delete button will be displayed.
    :param set_value_func: the function to call after the validate button is clicked and the window closed.
    :param set_delete_func: the function to call after the delete button is clicked.
    """

    def __init__(
        self,
        window_title: str = 'Choose a value',
        title: str = '',
        sub_title: str = 'Please select a value in the list below',
        width: int = 310,
        height: int = 300,
        icon=None,
        screen_index: int = 0,
        choices: dict = None,
        default_value='',
        show_validate_button: bool = True,
        show_delete_button: bool = False,
        set_value_func: callable = None,
        set_delete_func: callable = None,
    ):

        super().__init__()
        self.title(window_title)
        try:
            # an error can occur here AFTER a tool window has been opened and closed (ex: db "import/export")
            self.style = gui_fn.set_custom_style(gui_g.s.theme_name, gui_g.s.theme_font)
        except Exception as error:
            gui_f.log_warning(f'Error in DisplayContentWindow: {error!r}')
        self.main_title = title or window_title
        self.sub_title = sub_title
        self.geometry(gui_fn.center_window_on_screen(screen_index, width, height))
        gui_fn.set_icon_and_minmax(self, icon)
        self.show_delete_button = show_delete_button
        self.show_validate_button = show_validate_button
        self.set_value_func = set_value_func
        self.set_delete_func = set_delete_func
        self.choices: dict = choices
        self.frm_control = self.ControlFrame(self)
        self.frm_control.pack(ipadx=0, ipady=0, padx=0, pady=0)
        self.default_value = default_value
        # make_modal(self)  # could cause issue if done in the init of the class. better to be done by the caller

    class ControlFrame(ttk.Frame):
        """
        The frame that contains the control buttons.
        :param container: the container.
        """

        def __init__(self, container):
            super().__init__(container)
            self.container = container
            self.lbl_title = tk.Label(self, text=container.main_title, font=('Helvetica', 14, 'bold'))
            self.lbl_title.pack(pady=10)
            self.lbl_goal = tk.Label(self, text=container.sub_title, wraplength=300, justify='center')
            self.lbl_goal.pack(pady=5)
            var_choices = list(self.container.choices.keys())

            self.frm_choice = tk.Frame(self)
            self.frm_choice.pack(pady=5)

            if container.show_delete_button:
                self.cb_choice = ttk.Combobox(self.frm_choice, values=var_choices, state='readonly', width=35)
                self.cb_choice.grid(row=0, column=0, padx=5, pady=1)
                self.btn_del = ttk.Button(self.frm_choice, text='Delete', command=self.delete)
                self.btn_del.grid(row=0, column=1, padx=5, pady=1)
            else:
                self.cb_choice = ttk.Combobox(self.frm_choice, values=var_choices, state='readonly', width=45)
                self.cb_choice.grid(row=0, column=0, padx=5, pady=1)
            self.cb_choice.grid_columnconfigure(0, weight=3)

            self.lbl_description = tk.Label(self, text='Description', fg='blue', font=('Helvetica', 11, 'bold'))
            self.lbl_description.pack(padx=1, pady=1, anchor=tk.CENTER)
            self.text_description = tk.Text(self, fg='blue', height=6, width=53, font=('Helvetica', 10))
            self.text_description.pack(padx=5, pady=5)

            self.frm_buttons = tk.Frame(self)
            self.frm_buttons.pack(pady=5)
            # noinspection PyArgumentList
            # (bootstyle is not recognized by PyCharm)
            self.btn_close = ttk.Button(self.frm_buttons, text='Cancel and Close', bootstyle=WARNING, command=self.close_window)
            self.btn_close.pack(side=tk.LEFT, padx=5)
            if container.show_validate_button:
                # noinspection PyArgumentList
                # (bootstyle is not recognized by PyCharm)
                self.btn_import = ttk.Button(self.frm_buttons, text='Valid and Close', bootstyle=INFO, command=self.validate)
                self.btn_import.pack(side=tk.LEFT, padx=5)

            self.cb_choice.bind("<<ComboboxSelected>>", self.set_description)

        def set_description(self, _event) -> None:
            """
            Set the content of the description text.
            """
            selected_value = self.cb_choice.get()
            data = self.container.choices.get(selected_value, None)
            if data is None:
                return
            desc = data.get('desc', 'No description available for that choice')
            try:
                self.text_description.delete('1.0', tk.END)
                self.text_description.insert('1.0', desc)
            except (AttributeError, tk.TclError):
                pass

        def close_window(self) -> None:
            """
            Close the window.
            """
            if self.container.default_value is not None:
                self.container.set_value_func(self.container.default_value)
            self.container.destroy()

        def validate(self) -> None:
            """
            Validate the selected value
            """
            selected_value = self.cb_choice.get()
            data = self.container.choices.get(selected_value, None)
            if data is None:
                return
            value = data.get('value', None)
            self.container.set_value_func(value)
            self.container.destroy()
            return

        def delete(self) -> None:
            """
            Delete the selected value
            """
            selected_value = self.cb_choice.get()
            # clean the selected value
            self.cb_choice.set('')
            # clear the description
            self.text_description.delete('1.0', tk.END)
            # remove the value from the combobox
            self.cb_choice['values'] = [x for x in self.cb_choice['values'] if x != selected_value]
            # remove the value from the dict
            data = self.container.choices.pop(selected_value, None)
            if data is None:
                return
            value = data.get('value', None)
            self.container.set_delete_func(value)
            return


def set_choice(value):
    """
    Print the value choosen.
    """
    if value == '':  # test against the default_value
        print('No value has been selected')
    else:
        print(f'The value {value} has been selected')


def delete_choice(value):
    """
    Print the value choosen.
    """
    if value == '':  # test against the default_value
        print('No value has been selected')
    else:
        print(f'The value {value} has been DELETED')


if __name__ == '__main__':
    st = CFLW_Settings()
    main = tk.Tk()
    main.title('FAKE MAIN Window')
    main.geometry('200x100')
    ChoiceFromListWindow(
        title=st.title,
        choices=st.choices,
        default_value='',
        show_validate_button=st.show_validate_button,
        show_delete_button=st.show_delete_button,
        set_value_func=set_choice,
        set_delete_func=delete_choice
    )
    main.mainloop()
