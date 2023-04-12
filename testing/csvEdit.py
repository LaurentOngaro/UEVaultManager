import pandas as pd
from tkinter import *
from tkinter import ttk
from pandastable import Table, TableModel

bg_frame_color = '#BBBBFF'
main_title = "Unreal Engine Assets Table"


class EditableTable(Table):

    def __init__(self, parent=None, file=None, **kwargs):
        self.file = file
        self.rows_per_page = 30
        self.current_page = 0
        self.total_pages = 0
        self.data = None

        self.load_data()
        Table.__init__(self, parent, dataframe=self.data, **kwargs)
        # self.bind('<Double-Button-1>', self.edit_row)
        self.bind('<Double-Button-1>', self.edit_cell)

        self.edit_row_popup_width = 400
        self.edit_row_popup_height = 600
        self.edit_row_popup_title = 'Edit current row'

        self.edit_cell_popup_width = 300
        self.edit_cell_popup_height = 200
        self.edit_cell_popup_title = 'Edit current cell value'

    def show_page(self, page):
        start = page * self.rows_per_page
        end = start + self.rows_per_page
        data = self.data.iloc[start:end]
        self.updateModel(TableModel(data))
        self.redraw()
        self.current_page = page

    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.show_page(self.current_page + 1)

    def prev_page(self):
        if self.current_page > 0:
            self.show_page(self.current_page - 1)

    def load_data(self):
        self.data = pd.read_csv(self.file)
        self.total_pages = (len(self.data) - 1) // self.rows_per_page + 1

    def reload_data(self):
        self.load_data()
        self.show_page(self.current_page)

    def save_data(self):
        self.model.df.to_csv(self.file, index=False)

    def edit_row(self):
        def on_close():
            edit_row_popup.quit()

        row_selected = self.getSelectedRow()
        if row_selected is None:
            return
        row_data = self.model.df.iloc[row_selected].to_dict()
        edit_row_popup = Toplevel()
        edit_row_popup.overrideredirect(True)
        x = self.master.winfo_rootx()
        y = self.master.winfo_rooty()

        edit_row_popup.geometry(f'{self.edit_row_popup_width}x{self.edit_row_popup_height}+{x}+{y}')
        edit_row_popup.minsize(self.edit_row_popup_height, self.edit_row_popup_height)
        # configure the grid
        edit_row_popup.columnconfigure(0, weight=1)
        edit_row_popup.columnconfigure(1, weight=5)

        # row 1
        # editable values
        edit_frame = ttk.Frame(edit_row_popup, padding="3 3 12 12")
        edit_frame.pack(fill=X)

        entries = {}
        i = 0
        for i, (key, value) in enumerate(row_data.items()):
            Label(edit_frame, text=key).grid(row=i, column=0)
            entry = Entry(edit_frame)
            entry.insert(0, value)
            entry.grid(row=i, column=1, sticky=W + E)
            entries[key] = entry

        # row 2
        # scrollbar
        xscrollbar = Scrollbar(edit_frame, orient=HORIZONTAL, command=edit_frame.xview)
        xscrollbar.grid(row=1, column=0)
        edit_frame.configure(xscrollcommand=xscrollbar.set)

        # row 3
        # buttons
        button_frame = Frame(edit_row_popup)
        button_frame.pack(fill=X)
        ttk.Button(button_frame, text='Save', command=lambda: self.save_row(row_selected, entries, edit_row_popup)).grid(row=i + 1, column=0)
        ttk.Button(button_frame, text='Cancel', command=edit_row_popup.destroy).grid(row=i + 1, column=1)

    def save_row(self, row_index, entries, popup):
        for key, entry in entries.items():
            self.model.df.at[row_index, key] = entry.get()
        self.redraw()
        popup.destroy()

    def edit_cell(self, event):
        row_clicked = self.get_row_clicked(event)
        col_clicked = self.get_col_clicked(event)
        if row_clicked is None or col_clicked is None:
            return
        col_name = self.model.df.columns[col_clicked]
        cell_value = self.model.df.iat[row_clicked, col_clicked]
        edit_cell_popup = Toplevel()
        edit_cell_popup.title = self.edit_cell_popup_title
        edit_cell_popup.overrideredirect(True)
        edit_cell_popup.geometry(f'{self.edit_cell_popup_width}x{self.edit_cell_popup_height}+{event.x_root}+{event.y_root}')
        edit_cell_popup.resizable(False, False)
        Label(edit_cell_popup, text=col_name).grid(row=0, column=0)
        entry = Entry(edit_cell_popup)
        entry.insert(0, cell_value)
        entry.grid(row=0, column=1, sticky=W + E)
        ttk.Button(edit_cell_popup, text='Save',
                   command=lambda: self.save_cell(row_clicked, col_clicked, entry, edit_cell_popup)).grid(row=1, column=0)
        ttk.Button(edit_cell_popup, text='Cancel', command=edit_cell_popup.destroy).grid(row=1, column=1)

    def save_cell(self, row_index, col_index, entry, popup):
        self.model.df.iat[row_index, col_index] = entry.get()
        self.redraw()
        popup.destroy()


def show_table(file):

    def on_close():
        main.quit()

    def on_key_press(event):
        if event.keysym == 'Escape':
            on_close()
        elif event.keysym == 'Return':
            table.edit_row()

    main = Tk()
    main.title(main_title)
    main.geometry('1200x800')
    main.iconbitmap('../UEVaultManager/assets/main.ico')

    # UI options
    paddings = {'padx': 5, 'pady': 5}
    entry_font = {'font': ('Helvetica', 11)}

    # configure the grid
    # root.columnconfigure(0, weight=1)
    # root.columnconfigure(1, weight=3)

    # first row
    # title bar
    title_frame = ttk.Frame(main, relief='raised')
    title_frame.pack(fill=X)

    title_label = ttk.Label(title_frame, text=main_title)
    title_label.pack(side=LEFT)

    #close_button = ttk.Button(title_frame, text="X", command=on_close)
    #close_button.pack(side=RIGHT)

    # second row
    # datatable
    data_frame = ttk.Frame(main, padding="3 3 12 12")
    data_frame.pack(fill=X)

    table = EditableTable(data_frame, file=file)
    table.show()

    main.bind('<Key>', on_key_press)

    for child in data_frame.winfo_children():
        child.grid_configure(padx=5, pady=5)

    # third row
    # scrollbar
    xscrollbar = Scrollbar(data_frame, orient=HORIZONTAL, command=table.xview)
    xscrollbar.grid(row=1, column=0)
    table.configure(xscrollcommand=xscrollbar.set)

    # 4th row
    # buttons
    button_frame = Frame(main)
    button_frame.pack(fill=X)
    ttk.Button(button_frame, text='Prev Page', command=table.prev_page).pack()
    ttk.Button(button_frame, text='Next Page', command=table.next_page).pack()
    ttk.Button(button_frame, text='Edit Row', command=table.edit_row).pack()
    ttk.Button(button_frame, text='Reload Content', command=table.reload_data).pack()
    ttk.Button(button_frame, text='Save Changes', command=table.save_data).pack()

    main.mainloop()


show_table("../results/list.csv")
