# coding=utf-8
"""
Implementation for:
- ChoiceFromListWindow: Window to select a value in a list
"""
import tkinter as tk
from tkinter import ttk

import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience


class CFLW_Settings:
    """
    Settings for the class when running as main.
    """
    title = 'Choose the version'
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
    :param title: the title.
    :param width: the width.
    :param height: the height.
    :param icon: the icon.
    :param screen_index: the screen index.
    :param choices: the dict for choices to display. Must be formatted as { 'Label1': { 'value': 'id1', 'desc': 'this is the description 1' }, }
    :param default_value: the default value to return if no value is selected. If None, the set_value_func method will not be called on closed window.
    :param set_value_func: the function to call after the validate button is clicked and the window closed.
    """

    def __init__(
        self,
        title: str = 'Choose the value',
        width: int = 300,
        height: int = 350,
        icon=None,
        screen_index: int = 0,
        choices: dict = None,
        default_value='',
        set_value_func: callable = None
    ):

        super().__init__()
        self.title(title)
        self.main_title = title
        self.geometry(gui_fn.center_window_on_screen(screen_index, width, height))
        gui_fn.set_icon_and_minmax(self, icon)
        self.choices: dict = choices
        self.frm_control = self.ControlFrame(self)
        self.frm_control.pack(ipadx=0, ipady=0, padx=0, pady=0)
        self.default_value = default_value
        self.set_value_func = set_value_func
        # make_modal(self)  # could cause issue if done in the init of the class. better to be done by the caller

    class ControlFrame(ttk.Frame):
        """
        The frame that contains the control buttons.
        :param container: the container.
        """

        def __init__(self, container):
            super().__init__(container)
            self.container = container
            self.lbl_title = tk.Label(self, text=container.main_title, font=('Helvetica', 16, 'bold'))
            self.lbl_title.pack(pady=10)
            self.lbl_goal = tk.Label(self, text="Please select a value in the list below", wraplength=300, justify='center')
            self.lbl_goal.pack(pady=5)
            var_choices = list(self.container.choices.keys())

            self.cb_choice = ttk.Combobox(self, values=var_choices, state='readonly')
            self.cb_choice.pack(fill=tk.X, padx=10, pady=1)

            self.lbl_description = tk.Label(self, text='Description', fg='lightblue')
            self.lbl_description.pack(padx=1, pady=1, anchor=tk.CENTER)
            self.text_description = tk.Text(self, fg='blue', height=8, width=53, font=('Helvetica', 10))
            self.text_description.pack(padx=5, pady=5)

            self.frm_inner = tk.Frame(self)
            self.frm_inner.pack(pady=5)
            self.btn_close = ttk.Button(self.frm_inner, text='Close Window', command=self.close_window)
            self.btn_close.pack(side=tk.LEFT, padx=5)
            self.btn_import = ttk.Button(self.frm_inner, text='Valid and Close', command=self.validate)
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


def set_choice(value):
    """
    Print the value choosen.
    """
    if value == '':  # test against the default_value
        print('No value has been selected')
    else:
        print(f'The value {value} has been selected')


if __name__ == '__main__':
    st = CFLW_Settings()
    main = tk.Tk()
    main.title('FAKE MAIN Window')
    main.geometry('200x100')
    ChoiceFromListWindow(title=st.title, choices=st.choices, default_value='', set_value_func=set_choice)
    main.mainloop()
