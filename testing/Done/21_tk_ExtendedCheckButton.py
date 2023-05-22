# coding=utf-8
import os.path
import tkinter as tk
from tkinter import ttk


class ExtendedCheckButton(tk.Frame):
    """
    Create a new widget version of a ttk.Checkbutton.
    Note: We don't use the ttk.Checkbutton because it's hard to sync its state when using the on_click event.
    :param master: Parent widget
    :param text: Text to display next to the checkbutton
    :param images_folder: Path to the folder containing the images for the checkbutton. If empty, the './assets' folder will be used
    :param change_state_on_click: If True, the state of the checkbutton will change when clicking on the text or the checkbutton. if not, the change must be done manually by calling the switch_state method
    :param kwargs: kwargs to pass to the widget
    :return: ExtendedCheckButton instance
    """

    def __init__(self, master, text='', images_folder=None, change_state_on_click=True, **kwargs):
        super().__init__(master, **kwargs)
        if images_folder is None:
            images_folder = './assets/'
        self._img_checked = tk.PhotoImage(file=os.path.join(images_folder, 'checked_16.png'))  # Path to the checked image
        self._img_uncheckked = tk.PhotoImage(file=os.path.join(images_folder, 'unchecked_16.png'))  # Path to the unchecked image
        self._var = tk.BooleanVar(value=False)

        frm_inner = ttk.Frame(self)
        frm_inner.pack(fill=tk.BOTH, expand=True)

        lbl_text = ttk.Label(frm_inner, text=text)
        lbl_text.pack(side=tk.LEFT)

        check_label = ttk.Label(frm_inner, image=self._img_uncheckked, cursor='hand2')
        check_label.pack(side=tk.LEFT)

        self._lbl_text = lbl_text
        self._check_label = check_label

        if change_state_on_click:
            self.bind("<Button-1>", self.switch_state)

        self._update_state()

    def _update_state(self) -> None:
        """
        Updates the image of the checkbutton
        """
        current_state = self._var.get()
        if current_state:
            self._check_label.config(image=self._img_checked)
        else:
            self._check_label.config(image=self._img_uncheckked)

    def bind(self, sequence=None, command=None, add=True) -> None:
        """
        Binds a callback to the widget
        :param sequence: Sequence to bind to
        :param command:  function to bind
        :param add: If True, the callback will be added to the internal callbacks
        """
        if not (add == "+" or add is True):
            raise ValueError("'add' argument can only be '+' or True to preserve internal callbacks")
        self._lbl_text.bind(sequence, command, add=True)
        self._check_label.bind(sequence, command, add=True)

    def switch_state(self, _event) -> None:
        """
        Switches the state of the checkbutton
        :param _event: Event that triggered the callback
        """
        value = bool(self._var.get())
        self._var.set(not value)
        self._update_state()

    def set_content(self, content=''):
        """
        Sets the content of the widget. True, 'True' and '1' will be considered as True, everything else will be considered as False
        :param content: content to set
        """
        try:
            content = str(content).capitalize()
            if content is True or (content == 'True') or (content == '1'):
                self._var.set(True)
            else:
                # noinspection PyUnresolvedReferences
                self._var.set(False)
            self._update_state()
        except (AttributeError, tk.TclError) as error:
            log_warning(f'Failed to set content of {self} to {content}: {error!r}')

    def get_content(self) -> bool:
        """
        Gets the content of the widget.
        :return: True if the checkbutton is checked, False otherwise
        """

        try:
            content = self._var.get()
            if content is True or (content == 'True') or (content == '1'):
                return True
            else:
                return False
        except (AttributeError, tk.TclError) as error:
            log_warning(f'Failed to get content of {self}: {error!r}')
            return False


root = tk.Tk()

custom_checkbutton = ExtendedCheckButton(root, text="ExtendedCheckButton", images_folder='../../UEVaultManager/assets/')
custom_checkbutton.pack()

custom_checkbutton.bind("<Button-1>", lambda _event: print(f'Clicked on the checkbutton value= {custom_checkbutton.get_content()}'))
root.mainloop()
