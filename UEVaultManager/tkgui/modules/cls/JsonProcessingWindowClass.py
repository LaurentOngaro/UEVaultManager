# coding=utf-8
"""
Implementation for:
- JsonProcessingWindow: the window to process JSON files.
"""
import json
import os
import sqlite3
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
from UEVaultManager.lfs.utils import path_join


class JSPW_Settings:
    """
    Settings for the app.
    """
    folder_for_tags_path = 'K:/UE/UEVM/scraping/assets/marketplace'
    folder_for_rating_path = 'K:/UE/UEVM/scraping/global'
    db_path = 'K:/UE/UEVM/scraping/assets.db'
    title = 'Json Files Data Processing'


class JsonProcessingWindow(tk.Toplevel):
    """
    This window processes JSON files and stores some data in a database.
    :param title: the title.
    :param width: the width.
    :param height: the height.
    :param icon: the icon.
    :param screen_index: the screen index.
    :param folder_for_tags_path: the path to the folder with files for tags.
    :param folder_for_rating_path: the path to the folder with files for  ratings.
    :param db_path: the path to the database.
    """

    def __init__(
        self,
        title: str = 'Json Processing Window',
        width: int = 400,
        height: int = 400,
        icon=None,
        screen_index: int = 0,
        folder_for_tags_path: str = '',
        folder_for_rating_path: str = '',
        db_path: str = ''
    ):
        super().__init__()
        self.title(title)
        self.geometry(gui_fn.center_window_on_screen(screen_index, width, height))
        gui_fn.set_icon_and_minmax(self, icon)
        self.folder_for_tags_path = os.path.normpath(folder_for_tags_path)
        self.folder_for_rating_path = os.path.normpath(folder_for_rating_path)
        self.db_path = os.path.normpath(db_path)

        self.updated = 0
        self.added = 0

        self.frm_control = self.ControlFrame(self)
        self.frm_control.pack(ipadx=0, ipady=0, padx=0, pady=0)
        # make_modal(self)  # could cause issue if done in the init of the class. better to be done by the caller

    class ControlFrame(ttk.Frame):
        """
        The frame that contains the control buttons.
        :param container: the container.
        """

        def __init__(self, container):
            super().__init__(container)
            self.container: JsonProcessingWindow = container
            self.processing: bool = False

            self.lbl_title = tk.Label(self, text='File Data Processing Window', font=('Helvetica', 16, 'bold'))
            self.lbl_title.pack(pady=10)

            self.lbl_goal = tk.Label(
                self, text='This window processes JSON files and stores some data in a database.', wraplength=350, justify='center'
            )
            self.lbl_goal.pack(pady=5)

            self.frm_inner = tk.Frame(self)
            self.frm_inner.pack(pady=5)
            self.btn_close = ttk.Button(self.frm_inner, text='Close Window', command=self.close_window)
            self.btn_close.pack(side=tk.RIGHT, padx=5)
            self.btn_start = ttk.Button(self.frm_inner, text='Start Processing', command=self.start_processing)
            self.btn_start.pack(side=tk.LEFT, padx=5)
            self.btn_stop = ttk.Button(self.frm_inner, text='Stop Processing', command=self.stop_processing, state='disabled')
            self.btn_stop.pack(side=tk.LEFT, padx=5)

            self.progress_bar = ttk.Progressbar(self, mode='determinate')
            self.progress_bar.pack(fill=tk.X, padx=10, pady=15)

            self.lbl_result = tk.Label(self, text='Result Window: Clic into to copy content to clipboard', fg='green')
            self.lbl_result.pack(padx=1, pady=1, anchor=tk.CENTER)
            self.text_result = tk.Text(self, fg='blue', height=8, width=53, font=('Helvetica', 10))
            self.text_result.pack(padx=5, pady=5)
            self.text_result.bind('<Button-1>', self.copy_to_clipboard)

            self.lbl_status = tk.Label(self, text='', fg='green')
            self.lbl_status.pack(padx=5, pady=5)

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
            self.lbl_status.config(text=text)
            self.update()

        def close_window(self) -> None:
            """
            Close the window.
            """
            self.container.destroy()

        def activate_processing(self, for_start=True):
            """
            Activate or deactivate processing.
            :param for_start: True for enabling Start, False otherwise
            """

            if for_start:
                self.add_result('Processing started...')
                self.btn_start.config(state='disabled')
                self.btn_stop.config(state='normal')
                self.progress_bar['value'] = 0
            else:
                self.add_result('Processing stopped.')
                self.btn_start.config(state='normal')
                self.btn_stop.config(state='disabled')
                self.progress_bar['value'] = 0
            self.update()

        def start_processing(self) -> None:
            """
            Start processing.
            """
            if not self.processing:
                self.activate_processing()
                self.add_result('Processing data for RATINGS.', True)
                self.update()
                self.container.process_json_files('ratings')

                self.activate_processing()
                self.add_result('Processing data for TAGS.', True)
                self.update()
                self.container.process_json_files('tags')

                self.activate_processing(False)

        def stop_processing(self) -> None:
            """
            Stop processing.
            """
            self.processing = False
            self.activate_processing(False)
            self.progress_bar['value'] = 0
            self.update()

    def process_json_files(self, data_type='') -> None:
        """
        Process JSON files and stores data in the database.
        :param data_type: type of data to process. Can be 'tags' or 'ratings'
        """
        folder = ''
        query = ''

        if data_type == 'tags':
            folder = self.folder_for_tags_path
            query = 'CREATE TABLE IF NOT EXISTS tags (id TEXT PRIMARY KEY, name TEXT)'
        elif data_type == 'ratings':
            folder = self.folder_for_rating_path
            query = 'CREATE TABLE IF NOT EXISTS ratings (id TEXT, averageRating REAL, total INTEGER)'

        if not folder or not query:
            self.frm_control.activate_processing(False)
            return

        file_paths = [path_join(folder, filename) for filename in os.listdir(folder) if filename.endswith('.json')]
        if not file_paths:
            self.frm_control.activate_processing(False)
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query)

        total_files = len(file_paths)
        self.updated = 0
        self.added = 0
        self.frm_control.progress_bar['value'] = 0
        self.frm_control.progress_bar['maximum'] = total_files
        self.frm_control.processing = True
        try:
            conn.execute('BEGIN TRANSACTION')
            for i, file_path in enumerate(file_paths, start=1):
                if not self.frm_control.processing:
                    break
                self.frm_control.progress_bar['value'] = i
                self.update()
                with open(file_path, 'r') as json_file:
                    try:
                        json_data = json.load(json_file)
                    except json.decoder.JSONDecodeError:
                        self.frm_control.add_result(f'{file_path} is invalid')
                    else:
                        if data_type == 'tags':
                            self.extract_and_save_tags(cursor, json_data)
                        elif data_type == 'ratings':
                            self.extract_and_save_ratings(cursor, json_data)
            conn.commit()
            status_text = f'{data_type.title()} has been stored in the database. Updated: {self.updated}, Added: {self.added}'
            self.frm_control.add_result(status_text, True)

        except sqlite3.Error as error:
            conn.rollback()
            self.frm_control.add_result(f'An error occurred: {error!r}')

        finally:
            conn.close()
            self.frm_control.processing = False

    def extract_and_save_tags(self, cursor, json_data: dict) -> None:
        """
        Extract tags from JSON data and saves them in the database.
        :param cursor: database cursor
        :param json_data: JSON data
        """
        tags = json_data.get('tags', [])
        for tag in tags:
            if isinstance(tag, dict):
                uid = tag.get('id')
                tag_name = tag.get('name')
                is_existing = cursor.execute('SELECT id FROM tags WHERE id = ?', (uid, )).fetchone()
                if is_existing:
                    self.updated += 1
                    cursor.execute("UPDATE tags SET name = ? WHERE id=?", (tag_name, uid))

                    self.frm_control.add_result(f'Tag with id {uid} updated')
                else:
                    self.added += 1
                    cursor.execute('INSERT INTO tags (id, name) VALUES (?, ?)', (uid, tag_name))
                    self.frm_control.add_result(f'New Tag with id {uid} saved')

            # else:
            #     self.add_result(f'No data to save in the tag value {tag}')
            #     self.update()

    def extract_and_save_ratings(self, cursor, json_data: dict) -> None:
        """
        Extract ratings from JSON data and saves them in the database.
        :param cursor: database cursor
        :param json_data: JSON data
        """
        if 'data' in json_data and 'elements' in json_data['data']:
            for index, element in enumerate(json_data['data']['elements']):
                if isinstance(element, dict):
                    try:
                        uid = element['id']
                        rating_data = element['rating']
                        average_rating = rating_data['averageRating']
                        total_rating = rating_data['total']
                        is_existing = cursor.execute('SELECT id FROM ratings WHERE id = ?', (uid, )).fetchone()
                        if is_existing:
                            self.updated += 1
                            cursor.execute("UPDATE ratings SET averageRating = ?, total = ? WHERE id=?", (average_rating, total_rating, uid))
                            self.frm_control.add_result(f'Rating with id {uid} updated')
                        else:
                            self.added += 1
                            cursor.execute("INSERT INTO ratings (id, averageRating, total) VALUES (?, ?, ?)", (uid, average_rating, total_rating))
                            self.frm_control.add_result(f'New Rating with id {uid} saved')
                            self.update()
                    except KeyError:
                        pass
                # else:
                #     self.add_result(f'No data to save in element #{index}')
                #     self.update()


if __name__ == '__main__':
    st = JSPW_Settings()
    main = tk.Tk()
    main.title('FAKE MAIN Window')
    main.geometry('200x100')
    window = JsonProcessingWindow(
        title=st.title, db_path=st.db_path, folder_for_tags_path=st.folder_for_tags_path, folder_for_rating_path=st.folder_for_rating_path
    )
    main.mainloop()
