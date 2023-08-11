import os
import json
import sqlite3
import tkinter as tk
from tkinter import ttk


class FileProcessingApp:

    def __init__(self, parent):
        self.parent = parent
        self.parent.title('File Processing')
        self.parent.geometry('400x250')

        self.folder_path = 'K:/UE/UEVM/scraping/assets/marketplace'
        self.db_path = 'K:/UE/UEVM/scraping/assets.db'

        self.label = tk.Label(self.parent, text='File Processing App', font=('Helvetica', 16, 'bold'))
        self.label.pack(pady=10)

        self.goal_label = tk.Label(
            self.parent, text='This app processes JSON files and stores tag data in a database.', wraplength=350, justify='center'
        )
        self.goal_label.pack(pady=5)

        self.button_frame = tk.Frame(self.parent)
        self.button_frame.pack(pady=10)

        self.start_button = ttk.Button(self.button_frame, text='Start Processing', command=self.start_processing)
        self.start_button.pack(side='left', padx=5)

        self.stop_button = ttk.Button(self.button_frame, text='Stop Processing', command=self.stop_processing, state='disabled')
        self.stop_button.pack(side='left', padx=5)

        self.progress_bar = ttk.Progressbar(self.parent, mode='determinate')
        self.progress_bar.pack(fill='x', padx=10, pady=15)

        self.status_label = tk.Label(self.parent, text='', fg='green')
        self.status_label.pack(pady=5)

        self.processing = False
        self.updated_tags = 0
        self.added_tags = 0

    def activate_processing(self, for_start=True):
        if for_start:
            self.status_label.config(text='Processing started...')
            self.start_button.config(state='disabled')
            self.stop_button.config(state='normal')
        else:
            self.status_label.config(text='Processing stopped.')
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')

    def start_processing(self):
        if not self.processing:
            self.processing = True
            self.progress_bar['value'] = 0
            self.updated_tags = 0
            self.added_tags = 0
            self.activate_processing()
            self.process_tags()

    def stop_processing(self):
        self.processing = False
        self.activate_processing(False)
        self.progress_bar['value'] = 0
        self.parent.update()

    def process_tags(self):
        file_paths = [os.path.join(self.folder_path, filename) for filename in os.listdir(self.folder_path) if filename.endswith('.json')]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('CREATE TABLE IF NOT EXISTS tags (id TEXT PRIMARY KEY, name TEXT)')

        total_files = len(file_paths)
        self.progress_bar['maximum'] = total_files

        try:
            conn.execute('BEGIN TRANSACTION')

            for i, file_path in enumerate(file_paths, start=1):
                if not self.processing:
                    break

                self.progress_bar['value'] = i
                self.parent.update()

                with open(file_path, 'r') as json_file:
                    data = json.load(json_file)
                    tags = data.get('tags', [])

                    for tag in tags:
                        tag_id = tag.get('id')
                        tag_name = tag.get('name')

                        existing_tag = cursor.execute('SELECT id FROM tags WHERE id = ?', (tag_id, )).fetchone()
                        if existing_tag:
                            self.updated_tags += 1
                        else:
                            self.added_tags += 1
                            cursor.execute('INSERT INTO tags (id, name) VALUES (?, ?)', (tag_id, tag_name))

            conn.commit()
            status_text = f'Data has been stored in the database. Updated: {self.updated_tags}, Added: {self.added_tags}'
            self.status_label.config(text=status_text)

        except sqlite3.Error as e:
            conn.rollback()
            self.status_label.config(text=f'An error occurred: {e}')

        finally:
            conn.close()
            self.processing = False


if __name__ == '__main__':
    root = tk.Tk()
    app = FileProcessingApp(root)
    root.mainloop()
