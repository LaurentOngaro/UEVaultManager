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
    show_delete_content_button = True
    show_content_list = True
    json_data = {
        'Label1': {  # MANDATORY: 'Label1' is the label to display in the first list. WHEN VALIDATE,  THIS VALUE IS RETURNED TO THE CALLER as first id
            'value': 'value 1',  # OPTIONAL: example of a value for an item of the list, it can be replaced by another field name. Other fields can also be added.
            'desc': 'this is Label1 description',  # MANDATORY: 'desc' is the description to display in the description text bellow the first list
            'content': {  # MANDATORY: 'content' is used to fill the second list if show_content_list is True
                'contentLabel1_1': {  # MANDATORY: 'contentLabel1' is the label to display in the second list. WHEN VALIDATE, THIS VALUE IS RETURNED TO THE CALLER as second id
                    'value': 'value 1_1',  # OPTIONAL: example of a value for an item of the list, it can be replaced by another field name. Other fields can also be added.
                    'text': 'this is the id1_1 short label'  # MANDATORY: 'text' is the text to display in the label above the second list
                }
            }
        },
        'Label2': {
            'value': 'value 2',
            'desc': 'this is Label2 description',
            'content': {
                'contentLabel2_1': {
                    'value': 'value 2_1',
                    'text': 'this is the id2_1 a short label'
                },
                'contentLabel2_2': {
                    'value': 'value 2_2',
                    'text': 'this is the id2_2 b short label'
                }
            }
        },
        'Label3': {
            'value': 'value 3',
            'desc': 'this is Label3 description'
        },
        'Label4': {
            'value': 'value 4',
            'desc': 'this is Label4 description',
            'content': {
                'contentLabel4_1': {
                    'value': 'value 4_1',
                    'text': 'this is the id4_1 short label'
                }
            }
        },
    }


class ChoiceFromListWindow(tk.Toplevel):
    """
    Window to select a value in a list
    :param window_title: window title.
    :param title: title.
    :param sub_title: subtitle.
    :param width: width.
    :param height: height.
    :param icon: icon.
    :param screen_index: screen index.
    :param json_data: dict for choices to display. See the CFLW_Settings in this file for an example of format.
    :param default_value: default value to return if no value is selected. If None, the get_result_func method will not be called on closed window.
    :param show_validate_button: wether the validate button will be displayed.
    :param show_delete_button: wether the delete button will be displayed.
    :param get_result_func: function to call after the validate button is clicked and the window closed.
    :param list_remove_func: function to call after the delete button is clicked.
    :param show_content_list: wether the content list will be displayed.
    :param remove_from_content_func: function to call after the delete button is clicked in the content list.
    :param show_delete_content_button: wether the delete button for the content list will be displayed.

    """

    def __init__(
        self,
        window_title: str = 'Choose a value',
        title: str = '',
        sub_title: str = 'Please select a value in the list below',
        width: int = 320,
        height: int = 330,
        icon=None,
        screen_index: int = 0,
        json_data: dict = None,
        default_value='',
        show_content_list: bool = False,
        show_validate_button: bool = True,
        show_delete_button: bool = False,
        get_result_func: callable = None,
        list_remove_func: callable = None,
        remove_from_content_func: callable = None,
        show_delete_content_button: bool = False,
        no_content_text: str = 'No more content available for that choice',
        first_list_width: int = 35,
        second_list_width: int = 35,
        is_modal: bool = False,
    ):

        super().__init__()
        self.title(window_title)
        try:
            # an error can occur here AFTER a tool window has been opened and closed (ex: db "import/export")
            self.style = gui_fn.set_custom_style(gui_g.s.theme_name, gui_g.s.theme_font)
        except Exception as error:
            gui_f.log_warning(f'Error in DisplayContentWindow: {error!r}')
        self.main_title = title
        self.sub_title = sub_title
        self.json_data: dict = json_data.copy() if json_data else {}  # its content will be modified
        self.default_value = default_value
        self.show_content_list = show_content_list
        if self.show_content_list:
            height += 30
        self.geometry(gui_fn.center_window_on_screen(screen_index, width, height))
        gui_fn.set_icon_and_minmax(self, icon)
        self.show_validate_button = show_validate_button
        self.show_delete_button = show_delete_button
        self.get_result_func = get_result_func
        self.list_remove_func = list_remove_func
        self.remove_from_content_func = remove_from_content_func
        self.show_delete_content_button = show_delete_content_button
        self.no_content_text = no_content_text
        self.first_list_width = first_list_width
        self.second_list_width = second_list_width

        self.frm_control = self.ControlFrame(self)
        self.frm_control.pack(ipadx=0, ipady=0, padx=0, pady=0)
        self.is_modal = is_modal
        if is_modal:
            gui_f.make_modal(self)  # could cause issue if done in the init of the class. better to be done by the caller

    class ControlFrame(ttk.Frame):
        """
        The frame that contains the control buttons.
        :param container: container.
        """

        def __init__(self, container):
            super().__init__(container)
            self.container = container
            if container.main_title:
                self.lbl_title = tk.Label(self, text=container.main_title, font=('Helvetica', 14, 'bold'))
                self.lbl_title.pack(pady=10)
            if container.sub_title:
                self.lbl_sub_title = tk.Label(self, text=container.sub_title, wraplength=300, justify='center')
                self.lbl_sub_title.pack(pady=5)
            var_choices = list(container.json_data.keys())

            self.frm_list_choices = tk.Frame(self)
            self.frm_list_choices.pack(pady=5)
            if container.show_delete_button:
                self.cb_list_choices = ttk.Combobox(self.frm_list_choices, values=var_choices, state='readonly', width=container.first_list_width)
                self.cb_list_choices.grid(row=0, column=0, padx=5, pady=1)
                self.btn_list_del = ttk.Button(self.frm_list_choices, text='Remove', command=self.remove_from_list)
                self.btn_list_del.grid(row=0, column=1, padx=5, pady=1)
            else:
                self.cb_list_choices = ttk.Combobox(
                    self.frm_list_choices, values=var_choices, state='readonly', width=container.first_list_width + 10
                )
                self.cb_list_choices.grid(row=0, column=0, padx=5, pady=1)
            self.cb_list_choices.grid_columnconfigure(0, weight=3)

            self.lbl_description = tk.Label(self, text='Description', fg='blue', font=('Helvetica', 11, 'bold'))
            self.lbl_description.pack(padx=1, pady=1, anchor=tk.CENTER)
            self.text_description = ScrolledText(self, height=6, width=53, font=('Helvetica', 10),wrap=tk.WORD)
            # self.text_description = tk.Text(self, fg='blue', height=6, width=53, font=('Helvetica', 10))
            self.text_description.pack(padx=5, pady=2)

            if container.show_content_list:
                # we take the fist item of the first list to get the sub_choices
                list_selected_value = var_choices[0]
                list_data = container.json_data.get(list_selected_value, None)
                var_content_choices = list(list_data.keys())
                self.frm_content_choices = tk.Frame(self)
                self.frm_content_choices.pack(pady=2)
                self.lbl_content_label = tk.Label(self.frm_content_choices, text='sub list label', wraplength=300, justify='center')
                if container.show_delete_content_button:
                    self.lbl_content_label.grid(row=0, column=0, columnspan=2, padx=5, pady=1)
                    self.cb_content_choices = ttk.Combobox(
                        self.frm_content_choices, values=var_content_choices, state='readonly', width=container.second_list_width
                    )
                    self.cb_content_choices.grid(row=1, column=0, padx=5, pady=1)
                    self.btn_content_del = ttk.Button(self.frm_content_choices, text='Remove', command=self.remove_from_content)
                    self.btn_content_del.grid(row=1, column=1, padx=5, pady=1)
                else:
                    self.lbl_content_label.grid(row=0, column=0, padx=5, pady=1)
                    self.cb_content_choices = ttk.Combobox(
                        self.frm_content_choices, values=var_content_choices, state='readonly', width=container.second_list_width + 10
                    )
                    self.cb_content_choices.grid(row=1, column=0, padx=5, pady=1)
                self.cb_content_choices.grid_columnconfigure(0, weight=3)
                self.cb_content_choices.bind('<<ComboboxSelected>>', self.set_content_text)

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

            self.cb_list_choices.bind('<<ComboboxSelected>>', self.set_list_description)

            self.cb_list_choices.set(var_choices[0])  # select the first value
            self.set_list_description()

        def close_window(self) -> None:
            """
            Close the window.
            """
            if self.container.default_value is not None and self.container.get_result_func is not None:
                self.container.get_result_func(self.container.default_value)
            self.container.destroy()

        def set_list_description(self, _event=None) -> None:
            """
            Set the content of the description text.
            """
            list_selected_value = self.cb_list_choices.get()
            list_data = self.container.json_data.get(list_selected_value, None)
            if list_data is None:
                return
            desc = list_data.get('desc', 'No description available for that choice')
            try:
                self.text_description.delete('1.0', tk.END)
                self.text_description.insert('1.0', desc)
            except (AttributeError, tk.TclError):
                pass
            if self.container.show_content_list:
                self.set_content_list(list_selected_value)

        def remove_from_list(self) -> None:
            """
            Remove the selected value from the first list
            """
            check_if_deleted = True
            list_selected_value = self.cb_list_choices.get()
            data = self.container.json_data[list_selected_value]
            if data is None:
                return
            if self.container.list_remove_func is not None:
                check_if_deleted = self.container.list_remove_func(list_selected_value)
            if check_if_deleted:
                self.container.json_data.pop(list_selected_value, None)
                # clean the selected value
                self.cb_list_choices.set('')
                # clear the description
                self.text_description.delete('1.0', tk.END)
                # remove the value from the combobox
                self.cb_list_choices['values'] = [x for x in self.cb_list_choices['values'] if x != list_selected_value]
            return

        def validate(self) -> str:
            """
            Validate the selected values (in one list or both lists) and close the window.
            :return: the selected value(s) or None if no value is selected.
            """
            list_selected_value = self.cb_list_choices.get()
            list_data = self.container.json_data.get(list_selected_value, None)
            if list_data is None:
                return None
            return_value = list_selected_value
            if self.container.show_content_list:
                content_data = list_data.get('content', None)
                if content_data is None:
                    return None
                content_selected_value = self.cb_content_choices.get()
                return_value = (list_selected_value, content_selected_value)
            if self.container.get_result_func is not None:
                self.container.get_result_func(return_value)
            self.container.destroy()
            return return_value

        def set_content_list(self, list_selected_value: str = '') -> None:
            """
            Set the content of the sub choices.
            """
            if not self.container.show_content_list or not list_selected_value:
                return

            list_data = self.container.json_data.get(list_selected_value, {})
            content_data = list_data.get('content', {})

            try:
                self.cb_content_choices.set('')
                var_content_choices = list(content_data.keys())
                self.cb_content_choices['values'] = var_content_choices
                self.cb_content_choices.config(state=tk.NORMAL)
                self.btn_content_del.config(state=tk.NORMAL)
                self.cb_content_choices.set(var_content_choices[0])  # select the first value
                self.set_content_text()
            except (IndexError, KeyError, AttributeError):
                self.cb_content_choices.config(state=tk.DISABLED)
                self.btn_content_del.config(state=tk.DISABLED)
                self.lbl_content_label['text'] = self.container.no_content_text

        def set_content_text(self, _event=None) -> None:
            """
            Set the text of the content label.
            """
            # noinspection DuplicatedCode
            if not self.container.show_content_list:
                return

            list_selected_value = self.cb_list_choices.get()
            list_data = self.container.json_data.get(list_selected_value, {})
            content_data = list_data.get('content', {})

            content_selected_value = self.cb_content_choices.get()
            selected_content = content_data.get(content_selected_value, {})

            text = selected_content.get('text', self.container.no_content_text)
            self.lbl_content_label['text'] = text

        def remove_from_content(self) -> None:
            """
            Remove the selected value from the second list
            """
            # noinspection DuplicatedCode
            if not self.container.show_content_list:
                return

            list_selected_value = self.cb_list_choices.get()
            list_data = self.container.json_data.get(list_selected_value, {})
            content_data = list_data.get('content', {})
            content_selected_value = self.cb_content_choices.get()
            value_tuple = (list_selected_value, content_selected_value)
            if self.container.remove_from_content_func and self.container.remove_from_content_func(value_tuple):
                content_data.pop(content_selected_value, None)
                self.cb_content_choices.set('')
                self.cb_content_choices['values'] = [x for x in self.cb_content_choices['values'] if x != content_selected_value]
                self.set_list_description()


def set_choice(selection):
    """
    Print the value chosen.
    """
    st_l = CFLW_Settings()
    if isinstance(selection, tuple):
        list_id, content_id = selection
        if list_id != st_l.default:
            print(f'The values {list_id, content_id} have been SELECTED')
            return True
    elif selection != st_l.default:
        print(f'The value {selection} has been SELECTED')
        return True

    print('No value has been selected')
    return False


def delete_list(list_id) -> bool:
    """
    Delete the id choosen in the first list.
    :param list_id: value to delete.
    :return: True if the value has been deleted, False otherwise.
    """
    st_l = CFLW_Settings()
    if list_id != st_l.default:
        print(f'The value {list_id} has been DELETED')
        return True
    print('No value has been selected')
    return False


def delete_content(id_tuple: tuple) -> bool:
    """
    Delete the id choosen in the second list.
    :param id_tuple: tuple of (list_id, content_id).
    :return: True if the value has been deleted, False otherwise.
    """
    st_l = CFLW_Settings()
    list_id, content_id = id_tuple
    if list_id != st_l.default and content_id != st_l.default:
        print(f'The value {list_id, content_id} has been DELETED')
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
        json_data=st.json_data,
        default_value=st.default,
        show_validate_button=st.show_validate_button,
        show_delete_button=st.show_delete_button,
        get_result_func=set_choice,
        list_remove_func=delete_list,
        show_delete_content_button=st.show_delete_content_button,
        show_content_list=st.show_content_list,
        remove_from_content_func=delete_content,
    )
    main.mainloop()
