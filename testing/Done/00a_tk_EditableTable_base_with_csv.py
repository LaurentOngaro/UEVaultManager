import tkinter as tk
import pandas as pd
from pandastable import Table

file = '../../results/list.csv'


class EditableTable(tk.Frame):

    def __init__(self, parent: tk.Tk, file: str) -> None:
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.parent.geometry('1200x880')
        self.parent.title('Table app')
        self.current_page: int = 0
        self.rows_per_page: int = 35
        self.pagination_enabled: bool = True
        self.df: pd.DataFrame = pd.read_csv(file)
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

        self.update_table()

    def update_table(self) -> None:
        start_idx: int = self.current_page * self.rows_per_page
        end_idx: int = start_idx + self.rows_per_page
        self.table.model.df = self.df_filtered.iloc[start_idx:end_idx]
        self.table.redraw()
        self.page_label.config(text=f'Page {self.current_page + 1}')

    def prev_page(self) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            self.update_table()

    def next_page(self) -> None:
        last_page: int = len(self.df_filtered) // self.rows_per_page
        if self.current_page < last_page:
            self.current_page += 1
            self.update_table()


app = EditableTable(tk.Tk(), file)
app.mainloop()
