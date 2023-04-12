import tkinter as tk
from tkinter import ttk
from tkinter import filedialog as fd

# Root window
root = tk.Tk()
root.title('Display a Text File')
root.resizable(False, False)
root.geometry('550x250')

# Text editor
text = tk.Text(root, height=12)
text.grid(column=0, row=0, sticky='nsew')


def open_text_file():
    # file type
    filetypes = (('text files', '*.txt'), ('All files', '*.*'))
    # show the open file dialog
    f = fd.askopenfile(filetypes=filetypes)
    # read the text file and show its content on the Text
    text.insert('1.0', f.readlines())


# open file button
open_button = ttk.Button(root, text='Open a File', command=open_text_file)

open_button.grid(column=0, row=1, sticky='w', padx=10, pady=10)

root.mainloop()
