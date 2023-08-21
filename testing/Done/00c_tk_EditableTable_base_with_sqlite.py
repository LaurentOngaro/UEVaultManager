import tkinter as tk
import pandas as pd
from pandastable import Table

import tkinter as tk
import pandas as pd
import sqlite3
from pandastable import Table

db_name = 'K:/UE/UEVM/scraping/assets.db'


def columns_to_CSV_heading(word: str) -> str:
    heading = ' '.join(x for x in word.split('_'))
    heading = heading.capitalize()
    return heading


class EditableTable(tk.Frame):

    def __init__(self, parent: tk.Tk, db_name: str) -> None:
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.parent.geometry('1200x880')
        self.parent.title('Table app')
        self.current_page: int = 0
        self.rows_per_page: int = 35
        self.pagination_enabled: bool = True
        self.df: pd.DataFrame = self.load_data_from_db(db_name)
        self.df_filtered: pd.DataFrame = self.df
        f = tk.Frame(self.parent)
        f.pack(fill=tk.BOTH, expand=1)
        self.table: Table = Table(f, dataframe=self.df.iloc[0:0], showtoolbar=True, showstatusbar=True)
        self.table.show()

        # Add pagination buttons
        self.prev_btn = tk.Button(self.parent, text='<< Prev', command=self.prev_page)
        self.prev_btn.pack(side='left')
        self.next_btn = tk.Button(self.parent, text='Next >>', command=self.next_page)
        self.next_btn.pack(side='right')
        self.page_label = tk.Label(self.parent, text=f'Page {self.current_page + 1}')
        self.page_label.pack(side='bottom')
        # Add pagination toggle button
        self.pagination_btn = tk.Button(self.parent, text='Toggle Pagination', command=self.toggle_pagination)
        self.pagination_btn.pack(side='bottom')

        self.update_table()

    def load_data_from_db(self, db_name: str) -> pd.DataFrame:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM assets")

        rows = cursor.fetchall()
        column_names = [description[0] for description in cursor.description]

        df = pd.DataFrame(rows, columns=column_names)

        cursor.close()
        conn.close()

        # Convert column names to CamelCase
        df.columns = [columns_to_CSV_heading(col) for col in df.columns]

        return df

    def update_table(self) -> None:
        if self.pagination_enabled:
            start_idx: int = self.current_page * self.rows_per_page
            end_idx: int = start_idx + self.rows_per_page
            self.table.model.df = self.df_filtered.iloc[start_idx:end_idx]
        else:
            self.table.model.df = self.df_filtered
        self.table.redraw()
        self.page_label.config(text=f'Page {self.current_page + 1}')

    def toggle_pagination(self) -> None:
        self.pagination_enabled = not self.pagination_enabled
        self.update_table()

    def prev_page(self) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            self.update_table()

    def next_page(self) -> None:
        last_page: int = len(self.df_filtered) // self.rows_per_page
        if self.current_page < last_page:
            self.current_page += 1
            self.update_table()


app = EditableTable(tk.Tk(), db_name)
app.mainloop()
