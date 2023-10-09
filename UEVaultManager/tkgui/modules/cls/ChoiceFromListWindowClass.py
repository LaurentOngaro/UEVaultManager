# coding=utf-8
"""
Implementation for:
- ChoiceFromListWindow: Window to select a value in a list
"""
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from ttkbootstrap import INFO, WARNING

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience


class CFLW_Settings:
    """
    Settings for the class when running as main.
    """
    title = 'Choose the version'
    default = ''
    show_validate_button = True
    show_delete_button = False
    show_sub_delete_button = True
    choices = {
        'Label1': {
            'value': 'id1',
            'desc': 'this is Label1 description'
        },  #
        'Label2': {
            'value': 'id2',
            'desc': 'this is Label2 description'
        },  #
        'Label3': {
            'value': 'id3',
            'desc': 'this is Label3 description'
        },  #
        'Label4': {
            'value': 'id4',
            'desc': 'this is Label4 description'
        },  #
    }
    sub_choices = {
        # each key is a label from the first list
        'Label1': {
            'SubLabel1': {
                'value': 'sub_id1',
                'desc': 'this is the Sublabel1 short label'
            },  #
        },
        'Label2': {
            'SubLabel2a': {
                'value': 'sub_id2a',
                'desc': 'this is the Sublabel2 a short label'
            },
            'SubLabel2b': {
                'value': 'sub_id2b',
                'desc': 'this is the Sublabel2 b short label'
            },
        },  #
        'Label3': {},  #
        'Label4': {
            'SubLabel4': {
                'value': 'sub_id4',
                'desc': 'this is the Sublabel4 short label'
            },  #
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
    :param set_remove_func: the function to call after the delete button is clicked.
    :param sub_choices: the dict for choices in the second list to display. Must be formatted as { 'Label1': { 'Sublabel1: { 'value': 'subid1', 'desc': 'this is Sublabel1 description 1' }, } }
    :param set_sub_remove_func: the function to call after the delete button is clicked in the second list.
    """

    def __init__(
        self,
        window_title: str = 'Choose a value',
        title: str = '',
        sub_title: str = 'Please select a value in the list below',
        width: int = 320,
        height: int = 320,
        icon=None,
        screen_index: int = 0,
        choices: dict = None,
        default_value='',
        show_validate_button: bool = True,
        show_delete_button: bool = False,
        set_value_func: callable = None,
        set_remove_func: callable = None,
        sub_choices: dict = None,
        set_sub_remove_func: callable = None,
        show_sub_delete_button: bool = False,
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
        self.show_second_list = sub_choices is not None and len(sub_choices) > 0
        if self.show_second_list:
            height += 30
        self.geometry(gui_fn.center_window_on_screen(screen_index, width, height))
        gui_fn.set_icon_and_minmax(self, icon)
        self.show_validate_button = show_validate_button
        self.choices: dict = choices.copy() if choices else {}  # its content will be modified
        self.show_delete_button = show_delete_button
        self.set_value_func = set_value_func
        self.set_remove_func = set_remove_func
        self.sub_choices: dict = sub_choices.copy() if sub_choices else {}  # its content will be modified
        self.show_sub_delete_button = show_sub_delete_button
        self.set_sub_remove_func = set_sub_remove_func

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
            var_choices = list(container.choices.keys())

            self.frm_choices = tk.Frame(self)
            self.frm_choices.pack(pady=5)
            if container.show_delete_button:
                self.cb_choicess = ttk.Combobox(self.frm_choices, values=var_choices, state='readonly', width=35)
                self.cb_choices.grid(row=0, column=0, padx=5, pady=1)
                self.btn_del = ttk.Button(self.frm_choices, text='Remove', command=self.remove)
                self.btn_del.grid(row=0, column=1, padx=5, pady=1)
            else:
                self.cb_choices = ttk.Combobox(self.frm_choices, values=var_choices, state='readonly', width=45)
                self.cb_choices.grid(row=0, column=0, padx=5, pady=1)
            self.cb_choices.grid_columnconfigure(0, weight=3)

            self.lbl_description = tk.Label(self, text='Description', fg='blue', font=('Helvetica', 11, 'bold'))
            self.lbl_description.pack(padx=1, pady=1, anchor=tk.CENTER)
            self.text_description = ScrolledText(self, height=6, width=53, font=('Helvetica', 10))
            # self.text_description = tk.Text(self, fg='blue', height=6, width=53, font=('Helvetica', 10))
            self.text_description.pack(padx=5, pady=2)

            if container.show_second_list:
                # we take the fist item of the first list to get the sub_choices
                first_label = var_choices[0]
                first_list = container.sub_choices[first_label]
                var_sub_choices = list(first_list.keys())
                self.frm_sub_choices = tk.Frame(self)
                self.frm_sub_choices.pack(pady=2)
                self.lbl_sub_label = tk.Label(self.frm_sub_choices, text='sub list label', wraplength=300, justify='center')
                if container.show_sub_delete_button:
                    self.lbl_sub_label.grid(row=0, column=0, columnspan=2, padx=5, pady=1)
                    self.cb_sub_choices = ttk.Combobox(self.frm_sub_choices, values=var_sub_choices, state='readonly', width=35)
                    self.cb_sub_choices.grid(row=1, column=0, padx=5, pady=1)
                    self.btn_del = ttk.Button(self.frm_sub_choices, text='Remove', command=self.sub_remove)
                    self.btn_del.grid(row=1, column=1, padx=5, pady=1)
                else:
                    self.lbl_sub_label.grid(row=0, column=0, padx=5, pady=1)
                    self.cb_sub_choices = ttk.Combobox(self.frm_sub_choices, values=var_sub_choices, state='readonly', width=45)
                    self.cb_sub_choices.grid(row=1, column=0, padx=5, pady=1)
                self.cb_sub_choices.grid_columnconfigure(0, weight=3)

            self.frm_buttons = tk.Frame(self)
            self.frm_buttons.pack(pady=5)
            # noinspection PyArgumentList
            # (bootstyle is not recognized by PyCharm)
            self.btn_close = ttk.Button(self.frm_buttons, text='Close', bootstyle=WARNING, command=self.close_window)
            self.btn_close.pack(side=tk.LEFT, padx=5)
            if container.show_validate_button:
                # noinspection PyArgumentList
                # (bootstyle is not recognized by PyCharm)
                self.btn_import = ttk.Button(self.frm_buttons, text='Valid and Close', bootstyle=INFO, command=self.validate)
                self.btn_import.pack(side=tk.LEFT, padx=5)

            self.cb_choices.bind("<<ComboboxSelected>>", self.set_description)

            self.cb_choices.set(var_choices[0])  # select the first value
            self.set_description()

        def set_description(self, _event=None) -> None:
            """
            Set the content of the description text.
            """
            first_list_selection = self.cb_choices.get()
            first_list_data = self.container.choices.get(first_list_selection, None)
            if first_list_data is None:
                return
            desc = first_list_data.get('desc', 'No description available for that choice')
            try:
                self.text_description.delete('1.0', tk.END)
                self.text_description.insert('1.0', desc)
            except (AttributeError, tk.TclError):
                pass
            if self.container.show_second_list:
                self.set_sub_choices(first_list_selection)

        def close_window(self) -> None:
            """
            Close the window.
            """
            if self.container.default_value is not None and self.container.set_value_func is not None:
                self.container.set_value_func(self.container.default_value)
            self.container.destroy()

        def validate(self) -> None:
            """
            Validate the selected values (in one list or both lists) and close the window.
            """
            first_list_selection = self.cb_choices.get()
            first_list_data = self.container.choices.get(first_list_selection, None)
            if first_list_data is None:
                return
            value = first_list_data.get('value', None)
            if self.container.show_second_list:
                second_list_selection = self.cb_sub_choices.get()
                second_list_data = self.container.sub_choices[first_list_selection].get(second_list_selection, None)
                if second_list_data is None:
                    return
                value = value, second_list_data.get('value', None)
            if self.container.set_value_func is not None:
                self.container.set_value_func(value)
            self.container.destroy()
            return

        def remove(self) -> None:
            """
            Remove the selected value from the first list
            """
            check_if_deleted = True
            first_list_selection = self.cb_choices.get()
            data = self.container.choices[first_list_selection]
            if data is None:
                return
            value = data.get('value', None)
            if self.container.set_remove_func is not None:
                check_if_deleted = self.container.set_remove_func(value)
            if check_if_deleted:
                self.container.choices.pop(first_list_selection, None)
                # clean the selected value
                self.cb_choices.set('')
                # clear the description
                self.text_description.delete('1.0', tk.END)
                # remove the value from the combobox
                self.cb_choices['values'] = [x for x in self.cb_choices['values'] if x != first_list_selection]
            return

        def set_sub_choices(self, selected_key: str = '') -> None:
            """
            Set the content of the sub choices.
            """
            if not selected_key:
                return
            sub_choices = self.container.sub_choices.get(selected_key, None)
            if sub_choices is None:
                return
            var_sub_choices = list(sub_choices.keys())
            self.cb_sub_choices['values'] = var_sub_choices
            self.cb_sub_choices.set('')
            try:
                second_list_data = sub_choices.get(var_sub_choices[0], None)
                text = second_list_data['desc']
                self.cb_sub_choices.config(state=tk.NORMAL)
                self.cb_sub_choices.set(var_sub_choices[0])  # select the first value
            except (IndexError, KeyError):
                text = 'No other choices available for that version'
                # hide self.cb_sub_choices
                self.cb_sub_choices.config(state=tk.DISABLED)
            self.lbl_sub_label['text'] = text
            return

        def sub_remove(self) -> None:
            """
            Remove the selected value from the second list
            """
            first_list_selection = self.cb_choices.get()
            second_list_selection = self.cb_sub_choices.get()
            first_list_data = self.container.choices.get(first_list_selection)
            if not first_list_data:
                return
            second_list_data = self.container.sub_choices.get(first_list_selection, {}).get(second_list_selection)
            if not second_list_data:
                return
            value_tuple = (first_list_data.get('value'), second_list_data.get('value'))
            if self.container.set_sub_remove_func and self.container.set_sub_remove_func(value_tuple):
                second_list_data = self.container.sub_choices.get(first_list_selection, None)
                if second_list_data is None:
                    return
                second_list_data.pop(second_list_selection, None)
                self.cb_sub_choices.set('')
                self.cb_sub_choices['values'] = [x for x in self.cb_sub_choices['values'] if x != second_list_selection]
                self.set_description()


def set_choice(selection):
    """
    Print the value chosen.
    """
    st_l = CFLW_Settings()
    if isinstance(selection, tuple):
        first_list, second_list = selection
        if first_list != st_l.default:
            print(f'The values {first_list, second_list} have been SELECTED')
            return True
    elif selection != st_l.default:
        print(f'The value {selection} has been SELECTED')
        return True

    print('No value has been selected')
    return False


def delete_list(list_id) -> bool:
    """
    Delete the id choosen in the first list.
    :param list_id: the value to delete.
    :return: True if the value has been deleted, False otherwise.
    """
    st_l = CFLW_Settings()
    if list_id != st_l.default:
        print(f'The value {list_id} has been DELETED')
        return True
    print('No value has been selected')
    return False


def delete_sub_list(list_id_tuple: tuple) -> bool:
    """
    Delete the id choosen in the second list.
    :param list_id_tuple: tuple of (id in the first list, id in the second list)
    :return: True if the value has been deleted, False otherwise.
    """
    st_l = CFLW_Settings()
    first_list, second_list = list_id_tuple
    if first_list != st_l.default and second_list != st_l.default:
        print(f'The value {first_list,second_list} has been DELETED')
        return True
    print('No value has been selected')
    return False


if __name__ == '__main__':
    st = CFLW_Settings()
    main = tk.Tk()
    main.title('FAKE MAIN Window')
    main.geometry('200x100')
    ChoiceFromListWindow(
        title=st.title,
        choices=st.choices,
        default_value=st.default,
        show_validate_button=st.show_validate_button,
        show_delete_button=st.show_delete_button,
        set_value_func=set_choice,
        set_remove_func=delete_list,
        sub_choices=st.sub_choices,
        show_sub_delete_button=st.show_sub_delete_button,
        set_sub_remove_func=delete_sub_list,
    )
    main.mainloop()
