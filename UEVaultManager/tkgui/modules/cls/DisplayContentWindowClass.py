# coding=utf-8
"""
Implementation for:
- DCW_Settings: settings for the class when running as main.
- DisplayContentWindow: window to display a text content.
"""
import os
import tkinter as tk
from tkinter import filedialog as fd
from tkinter import ttk

from tkhtmlview import HTMLScrolledText
from ttkbootstrap import WARNING

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.cls.ExtendedWidgetClasses import ExtendedText


class DCW_Settings:
    """
    Settings for the class when running as main.
    """
    title = 'Display a text'
    use_html: bool = True
    text = '<html><body><h3>THIS IS HTML</h3><p>This is a demonstration</p><p>of the <b>HTML</b> capabilities</p></body></html>'


class DisplayContentWindow(tk.Toplevel):
    """
    Window to display a text content.
    :param title: title of the window.
    :param width: width of the window.
    :param height: height of the window.
    :param icon: icon of the window.
    :param screen_index: index of the screen on which the window will be displayed.
    :param quit_on_close: whether to quit the application when the window is closed.
    """

    def __init__(
        self,
        title: str,
        width: int = 600,
        height: int = 430,
        icon=None,
        screen_index: int = -1,
        quit_on_close: bool = False,
        text: str = '',
        result_filename: str = 'UEVM_output.txt',
        use_html: bool = False,
    ):
        super().__init__()
        self.title(title)
        try:
            # an error can occur here AFTER a tool window has been opened and closed (ex: db "import/export")
            self.style = gui_fn.set_custom_style(gui_g.s.theme_name, gui_g.s.theme_font)
            # get the root window
            root = gui_g.WindowsRef.uevm_gui or self
            self.screen_index: int = screen_index if screen_index >= 0 else int(root.winfo_screen()[1])
            self.geometry(gui_fn.center_window_on_screen(self.screen_index, width, height))
        except Exception as error:
            gui_f.log_warning(f'Error in DisplayContentWindow: {error!r}')
        gui_fn.set_icon_and_minmax(self, icon)
        self.resizable(True, False)
        self._keep_existing: bool = False  # whether to keep the existing content when adding a new one
        self.quit_on_close: bool = quit_on_close
        self.result_filename: str = result_filename
        self.use_html: bool = use_html
        self.frm_content = self.ContentFrame(self)
        self.frm_control = self.ControlFrame(self)

        self.frm_control.pack(ipadx=5, ipady=5, padx=5, pady=5, fill=tk.X)
        self.frm_content.pack(ipadx=5, ipady=5, padx=5, pady=5, fill=tk.X)

        self.bind('<Tab>', self._focus_next_widget)
        self.bind('<Control-Tab>', self._focus_next_widget)
        self.bind('<Shift-Tab>', self._focus_prev_widget)
        self.bind('<Key>', self.on_key_press)
        self.bind('<Button-3>', self.on_right_click)
        self.protocol('WM_DELETE_WINDOW', self.on_close)
        self.text: str = ''
        if text:
            self.display(text)
        gui_g.WindowsRef.display_content = self
        # gui_f.make_modal(self)  # could cause issue if done in the init of the class. better to be done by the caller

    @property
    def keep_existing(self) -> bool:
        """
        Get wether to keep the existing content when adding a new one.
        :return: True if keep_existing.
        """
        return self._keep_existing

    @keep_existing.setter
    def keep_existing(self, value: bool):
        """
        Set wether to keep the existing content when adding a new one.
        :param value: value to set.
        """
        self._keep_existing = value

    @staticmethod
    def _focus_next_widget(event):
        event.widget.tk_focusNext().focus()
        return 'break'

    @staticmethod
    def _focus_prev_widget(event):
        event.widget.tk_focusPrev().focus()
        return 'break'

    def on_right_click(self, event=None) -> None:
        """
        When the right mouse button is clicked, show the selected row in the quick edit frame.
        :param event: event that triggered the call.
        """
        gui_f.copy_widget_value_to_clipboard(self, event)

    class ContentFrame(ttk.Frame):
        """
        The frame containing the content of the window.
        :param container: container of the frame.
        """

        def __init__(self, container):
            super().__init__(container)
            pack_def_options = {'ipadx': 3, 'ipady': 3}
            if container.use_html:
                text_content = HTMLScrolledText(self, font=gui_g.s.theme_font)
            else:
                text_content = ExtendedText(self)
                scrollbar = ttk.Scrollbar(self)
                scrollbar.config(command=text_content.yview)
                text_content.config(yscrollcommand=scrollbar.set)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y, **pack_def_options)
            text_content.pack(fill=tk.BOTH, expand=True, **pack_def_options)
            self.text_content = text_content

    class ControlFrame(ttk.Frame):
        """
        The frame containing the control buttons of the window.
        :param container: container of the frame.
        """

        def __init__(self, container):
            super().__init__(container)
            self.container = container
            pack_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.BOTH, 'expand': False}
            lblf_def_options = {'ipadx': 1, 'ipady': 1, 'expand': True, 'fill': tk.X}
            lblf_commands = ttk.LabelFrame(self, text='Commands')
            lblf_commands.pack(**lblf_def_options)
            ttk.Button(lblf_commands, text='Clean content', command=container.clean).pack(**pack_def_options, side=tk.LEFT)
            ttk.Button(lblf_commands, text='Copy to clipboard', command=container.copy_to_clipboard).pack(**pack_def_options, side=tk.LEFT)
            ttk.Button(lblf_commands, text='Save To File', command=container.save_changes).pack(**pack_def_options, side=tk.LEFT)
            # noinspection PyArgumentList
            # (bootstyle is not recognized by PyCharm)
            ttk.Button(lblf_commands, text='Close', command=container.on_close, bootstyle=WARNING).pack(**pack_def_options, side=tk.RIGHT)

    # noinspection DuplicatedCode
    def on_key_press(self, event):
        """
                Event when a key is pressed.
                :param event: event that triggered the call of this function.
                """
        control_pressed = event.state == 4 or event.state & 0x00004 != 0
        if event.keysym == 'Escape':
            self.on_close()
        elif control_pressed and (event.keysym == 's' or event.keysym == 'S'):
            self.save_changes()
        return 'break'

    def on_close(self, _event=None) -> None:
        """
        Event when the window is closing.
        :param _event: event that triggered the call of this function.
        """
        self.close_window()

    def close_window(self) -> None:
        """
        Close the window.
        """
        gui_g.WindowsRef.display_content = None
        if self.quit_on_close:
            self.quit()
        else:
            self.destroy()

    def fit_height(self) -> None:
        """
        Fit the height of the window to the content.

        Notes:
            It replaces the content of the fit_height() method of the tkhtmlview.HTMLScrolledText class because it does not work properly.
        """
        widget = self.frm_content.text_content
        for h in range(1, 4):
            widget.config(height=h)
            self.update()
            if widget.yview()[1] >= 1:
                break
        else:
            widget.config(height=2 + 3 / widget.yview()[1])

    def display(self, content='', keep_mode=True) -> None:
        """
        Display the content in the window. By default, i.e. keep_mode==True, each new call adds the content to the existing content with a new line.
        :param content: text to print.
        :param keep_mode: whether to keep the existing content when a new one is added.
        """
        widget = self.frm_content.text_content  # shortcut
        try:
            if self.use_html:
                self.text = content if not self._keep_existing else self.text + '<br/>' + content
                widget.set_html(self.text)
                self.fit_height()
            else:
                self.text = content if not self._keep_existing else self.text + '\n' + content
                widget.delete('1.0', tk.END)
                widget.insert(tk.END, self.text)
            # set the mode at the end to allow using display() to be used to change the mode for the next call
            self._keep_existing = keep_mode
            self.update()
            self.focus_set()
        except tk.TclError:
            # gui_f.log_warning(f'Error in display_content_window: {error!r})  # will flood because it occurs frequently
            pass

    def clean(self) -> None:
        """ Clean the content of the window. """
        self.text = ''
        if self.use_html:
            self.frm_content.text_content.set_html('')
        else:
            self.frm_content.text_content.delete('1.0', tk.END)
        self.update()

    def save_changes(self) -> str:
        """
        Save the content displayed to a file.
        :return: the filename where the content has been saved.
        """
        initial_dir = gui_g.s.last_opened_folder
        filename, ext = os.path.splitext(self.result_filename)
        if self.use_html:
            filename += '.html'
        else:
            filename += '.txt'
        filename = fd.asksaveasfilename(
            title='Choose a file to save data to',
            initialdir=initial_dir,
            filetypes=gui_g.s.data_filetypes_html if self.use_html else gui_g.s.data_filetypes_text,
            initialfile=filename
        )
        if filename:
            filename = os.path.normpath(filename)
            with open(filename, 'w', encoding='utf-8') as file:
                file.write(self.text)
            gui_f.box_message(f'Content Saved to {filename}')
        return filename

    def set_focus(self) -> None:
        """ Set the focus on the window. """
        self.focus_set()
        self.grab_set()
        self.wait_window()

    def copy_to_clipboard(self) -> None:
        """ Copy text to the clipboard. """
        self.clipboard_clear()
        self.clipboard_append(self.text)
        gui_f.notify('Content copied to the clipboard.')


if __name__ == '__main__':
    st = DCW_Settings()
    main = tk.Tk()
    main.title('FAKE MAIN Window')
    main.geometry('200x100')
    DisplayContentWindow(title=st.title, text=st.text, use_html=st.use_html)
    main.mainloop()
