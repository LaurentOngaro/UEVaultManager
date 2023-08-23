# coding=utf-8
"""
Implementation for:
"""
import datetime
import os
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
from UEVaultManager.models.UEAssetDbHandlerClass import UEAssetDbHandler


class DBFW_Settings:
    """
    Settings for the app.
    """
    folder_for_csv_files = 'K:/UE/UEVM/scraping/csv'
    db_path = 'K:/UE/UEVM/scraping/assets.db'
    title = 'Database Import/Export Window'


class DbFilesWindowClass(tk.Toplevel):
    """
    This app processes JSON files and stores some data in a database.
    :param title: the title.
    :param width: the width.
    :param height: the height.
    :param icon: the icon.
    :param screen_index: the screen index.
    :param folder_for_csv_files: the path to the folder with files for tags.
    :param db_path: the path to the database.
    """

    value_for_all: str = 'All'
    suffix_separator: str = '_##'
    must_reload: bool = False

    def __init__(
        self,
        title: str = 'Database Import/Export Window',
        width: int = 400,
        height: int = 420,
        icon=None,
        screen_index: int = 0,
        folder_for_csv_files: str = '',
        db_path: str = ''
    ):

        super().__init__()
        self.title(title)
        self.geometry(gui_fn.center_window_on_screen(screen_index, width, height))
        gui_fn.set_icon_and_minmax(self, icon)
        self.folder_for_csv_files = os.path.normpath(folder_for_csv_files)
        self.db_path = os.path.normpath(db_path)
        self.db_handler = UEAssetDbHandler(database_name=self.db_path)
        self.control_frame = self.ControlFrame(self)
        self.control_frame.pack(ipadx=0, ipady=0, padx=0, pady=0)

    class ControlFrame(ttk.Frame):
        """
        The frame that contains the control buttons.
        :param container: the container.
        """

        def __init__(self, container):
            super().__init__(container)
            self.container: DbFilesWindowClass = container
            self.processing: bool = False

            self.label = tk.Label(self, text='Database Import/Export Window', font=('Helvetica', 16, 'bold'))
            self.label.pack(pady=10)

            self.goal_label = tk.Label(
                self, text="This window import or export data of the database'stables in CSV files.", wraplength=300, justify='center'
            )
            self.goal_label.pack(pady=5)

            var_table_names = container.db_handler.get_table_names()
            var_table_names.insert(0, container.value_for_all)
            self.cb_table = ttk.Combobox(self, values=var_table_names, state='readonly')
            self.cb_table.pack(fill=tk.X, padx=10, pady=1)
            self.var_add_suffix = tk.BooleanVar(value=True)
            self.ck_add_suffix = tk.Checkbutton(self, text='Add a datetime suffix when exporting', variable=self.var_add_suffix)
            self.ck_add_suffix.pack(fill=tk.X, padx=2, pady=1, anchor=tk.W)
            self.var_delete_content = tk.BooleanVar(value=False)
            self.ck_delete_content = tk.Checkbutton(self, text='Delete content before import', variable=self.var_delete_content)
            self.ck_delete_content.pack(fill=tk.X, padx=2, pady=1, anchor=tk.W)

            self.button_frame = tk.Frame(self)
            self.button_frame.pack(pady=5)
            self.import_button = ttk.Button(self.button_frame, text='Import from files', command=self.import_data)
            self.import_button.pack(side=tk.LEFT, padx=5)
            self.export_button = ttk.Button(self.button_frame, text='Export to files', command=self.export_data)
            self.export_button.pack(side=tk.LEFT, padx=5)

            self.result_label = tk.Label(self, text='Result Window: Clic into to copy content to clipboard', fg='green')
            self.result_label.pack(padx=1, pady=1, anchor=tk.CENTER)
            self.text_result = tk.Text(self, fg='blue', height=8, width=53, font=('Helvetica', 10))
            self.text_result.pack(padx=5, pady=5)
            self.text_result.bind('<Button-1>', self.copy_to_clipboard)

            self.status_label = tk.Label(self, text='', fg='green')
            self.status_label.pack(padx=5, pady=5)

        def copy_to_clipboard(self, _event):
            """
            Copy text to the clipboard.
            :param _event: event
            """
            self.clipboard_clear()
            content = self.text_result.get('1.0', 'end-1c')
            self.clipboard_append(content)
            messagebox.showinfo('Info', 'Content copied to the clipboard.')

        def add_result(self, text: str, set_status: bool = False) -> None:
            """
            Add text to the result label.
            :param text: text to add
            :param set_status: True for setting the status label, False otherwise
            """
            if set_status:
                self.set_status(text)
            self.text_result.insert('end', text + '\n')
            self.text_result.see('end')

        def set_status(self, text: str) -> None:
            """
            Set the status label.
            :param text: text to set
            """
            self.status_label.config(text=text)
            self.update()

        def import_data(self) -> None:
            """
            Import data from CSV files to the database.
            """
            if self.processing:
                messagebox.showinfo('Info', 'Processing is already running.')
                return
            self.processing = True
            self.set_status('Processing...')
            self.add_result('Processing...')
            self.update()
            delete_content = self.var_delete_content.get()
            table_name = self.cb_table.get()
            if table_name == self.container.value_for_all:
                table_name = ''
            files, must_reload = self.container.db_handler.import_from_csv(
                self.container.folder_for_csv_files, table_name, suffix_separator=self.container.suffix_separator, delete_content=delete_content
            )
            self.add_result('Importing data from files:')
            for file in files:
                self.add_result(file)
            self.add_result('Import finished.')
            self.set_status('Import finished.')
            self.container.must_reload = must_reload
            self.processing = False

        def export_data(self) -> None:
            """
            Export data from the database to CSV files.
            """
            if self.processing:
                messagebox.showinfo('Info', 'Processing is already running.')
                return
            self.processing = True
            self.set_status('Processing...')
            self.add_result('Processing...')
            self.update()
            table_name = self.cb_table.get()
            if table_name == self.container.value_for_all:
                table_name = ''
            suffix = datetime.datetime.now().strftime('%Y%m%d-%H%M%S') if self.var_add_suffix.get() else ''
            files = self.container.db_handler.export_to_csv(
                self.container.folder_for_csv_files, table_name, suffix_separator=self.container.suffix_separator, suffix=suffix
            )
            self.add_result('Exporting data to files:')
            for file in files:
                self.add_result(file)
            self.add_result('Export finished.')
            self.set_status('Export finished.')
            self.processing = False


if __name__ == '__main__':
    st = DBFW_Settings()
    main = tk.Tk()
    main.title('FAKE MAIN Window')
    main.geometry('200x100')
    app = DbFilesWindowClass(title=st.title, db_path=st.db_path, folder_for_csv_files=st.folder_for_csv_files)
    main.mainloop()
