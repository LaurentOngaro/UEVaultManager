import tkinter as tk
import pandas as pd
from pandastable import Table

file = 'K:/UE/UEVM/Results//list.csv'


class EditableTable(tk.Frame):

    def __init__(self, parent: tk.Tk, file: str) -> None:
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.parent.geometry('1200x880')
        self.parent.title('Table app')
        self.current_page: int = 0
        self.rows_per_page: int = 35
        self.pagination_enabled: bool = True
        self._data: pd.DataFrame = pd.read_csv(file)
        self._data_filtered: pd.DataFrame = self._data
        f = tk.Frame(self.parent)
        f.pack(fill=tk.BOTH, expand=1)
        self.table: Table = Table(f, dataframe=self._data.iloc[0:0], showtoolbar=True, showstatusbar=True)
        self.table.show()

        self.pagination_enabled = False
        self.btn_pagination = tk.Button(self.parent, text="Enable Pagination", command=self.toggle_pagination)
        self.btn_pagination.pack(side='left')
        self.btn_add_row = tk.Button(self.parent, text='Add Row', command=self.add_row)
        self.btn_remove_row = tk.Button(self.parent, text='Remove Row', command=self.remove_row)
        self.btn_add_row.pack(side='left')
        self.btn_remove_row.pack(side='left')
        self.btn_last = tk.Button(self.parent, text='Last', command=self.last_page)
        self.btn_last.pack(side='right')
        self.btn_next = tk.Button(self.parent, text='Next >>', command=self.next_page)
        self.btn_next.pack(side='right')
        self.btn_prev = tk.Button(self.parent, text='<< Prev', command=self.prev_page)
        self.btn_prev.pack(side='right')
        self.btn_first = tk.Button(self.parent, text='First', command=self.first_page)
        self.btn_first.pack(side='right')
        self.page_label = tk.Label(self.parent, text=f'Page {self.current_page + 1}')
        self.page_label.pack(side='bottom')

        self.update_table()

    def toggle_pagination(self, forced=None) -> None:
        if forced is not None:
            self.pagination_enabled = forced
        else:
            self.pagination_enabled = not self.pagination_enabled
        btn_text = "Disable Pagination" if self.pagination_enabled else "Enable Pagination"
        self.btn_pagination.config(text=btn_text)  # Update the button text
        self.update_table()

    def update_table(self) -> None:
        if self.pagination_enabled:
            # Pagination is enabled
            start_idx: int = self.current_page * self.rows_per_page
            end_idx: int = start_idx + self.rows_per_page
            self.table.model.df = self._data_filtered.iloc[start_idx:end_idx]
            state = tk.DISABLED
            state_inversed = tk.NORMAL

        else:
            self.table.model.df = self._data_filtered
            state = tk.NORMAL
            state_inversed = tk.DISABLED

        # Disable or Enable the navigation buttons based on the pagination status
        for btn in [self.btn_next, self.btn_prev, self.btn_first, self.btn_last]:
            btn.config(state=state_inversed)
        for btn in [self.btn_add_row, self.btn_remove_row]:
            btn.config(state=state)

        self.table.redraw()
        self.page_label.config(text=f'Page {self.current_page + 1}')

    def first_page(self) -> None:
        self.current_page = 0
        self.update_table()

    def prev_page(self) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            self.update_table()

    def next_page(self) -> None:
        last_page: int = len(self._data_filtered) // self.rows_per_page
        if self.current_page < last_page:
            self.current_page += 1
            self.update_table()

    def last_page(self) -> None:
        last_page: int = len(self._data_filtered) // self.rows_per_page
        self.current_page = last_page
        self.update_table()

    def add_row(self) -> None:
        """Add a new row to the DataFrame with NaN values."""
        # add the new row at the end of the DataFrame
        self.toggle_pagination(False)  # to avoid issues with row index

        empty_row = [pd.NA] * len(self._data_filtered.columns)
        self._data_filtered.loc[len(self._data_filtered)] = empty_row
        self.update_table()
        # move the scrollbar to the end
        # don't know how to do that
        # so enable pagination, and go to the last page
        self.toggle_pagination(True)
        self.last_page()

    def remove_row(self) -> None:
        """Remove the selected row from the DataFrame."""
        selected_index = self.table.getSelectedRow()
        if not self._data_filtered.empty and selected_index is not None and 0 <= selected_index < len(self._data_filtered):
            self._data_filtered.drop(self._data_filtered.index[selected_index], inplace=True)
            self.update_table()


app = EditableTable(tk.Tk(), file)
app.mainloop()
