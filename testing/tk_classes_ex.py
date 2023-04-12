import tkinter as tk
from tkinter import ttk


class MainDataFrame(ttk.Frame):

    def __init__(self, container):
        super().__init__(container)
        # set up the grid layout manager
        self.columnconfigure(0, weight=1)
        self.columnconfigure(0, weight=3)

        self.__create_widgets()

    def __create_widgets(self):
        # Find what
        ttk.Label(self, text='Find what:').grid(column=0, row=0, sticky=tk.W)
        keyword = ttk.Entry(self, width=30)
        keyword.focus()
        keyword.grid(column=1, row=0, sticky=tk.W)

        # Replace with:
        ttk.Label(self, text='Replace with:').grid(column=0, row=1, sticky=tk.W)
        replacement = ttk.Entry(self, width=30)
        replacement.grid(column=1, row=1, sticky=tk.W)

        # Match Case checkbox
        match_case = tk.StringVar()
        match_case_check = ttk.Checkbutton(self, text='Match case', variable=match_case, command=lambda: print(match_case.get()))
        match_case_check.grid(column=0, row=2, sticky=tk.W)

        # Wrap Around checkbox
        wrap_around = tk.StringVar()
        wrap_around_check = ttk.Checkbutton(self, variable=wrap_around, text='Wrap around', command=lambda: print(wrap_around.get()))
        wrap_around_check.grid(column=0, row=3, sticky=tk.W)

        for widget in self.winfo_children():
            widget.grid(padx=0, pady=5)


class MainButtonFrame(ttk.Frame):

    def __init__(self, container):
        super().__init__(container)
        # set up the grid layout manager
        self.rowconfigure(0, weight=1)

        self.__create_widgets()

    def __create_widgets(self):
        ttk.Button(self, text='Find Next').grid(row=0, column=0)
        ttk.Button(self, text='Replace').grid(row=0, column=1)
        ttk.Button(self, text='Replace All').grid(row=0, column=2)
        ttk.Button(self, text='Cancel').grid(row=0, column=3)

        for widget in self.winfo_children():
            widget.grid(padx=0, pady=3)


class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title('Replace')
        self.geometry('400x150')
        self.resizable(False, False)
        # windows only (remove the minimize/maximize button)
        self.attributes('-toolwindow', True)

        # layout on the root window
        self.rowconfigure(0, weight=4)
        self.rowconfigure(1, weight=1)

        self.__create_widgets()

    def __create_widgets(self):
        # create the input frame
        input_frame = MainDataFrame(self)
        input_frame.grid(column=0, row=0)

        # create the button frame
        button_frame = MainButtonFrame(self)
        button_frame.grid(column=0, row=1)


if __name__ == "__main__":
    app = App()
    app.mainloop()
