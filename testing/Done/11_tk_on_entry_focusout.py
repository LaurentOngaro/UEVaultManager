import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import showinfo

entry_var = None


def valid_entry(_event=None):
    global entry_var
    showinfo('entry value', f'current value: {entry_var.get()}')


def copy_entry_to_label(label):
    global entry_var
    label.config(text=entry_var.get())


def main():
    global entry_var

    root = tk.Tk()
    root.title("Set Entry Value Example")

    main_frame = ttk.Frame(root, padding=20)
    main_frame.grid(column=0, row=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    entry_var = tk.StringVar()

    entry = ttk.Entry(main_frame, textvariable=entry_var)
    entry.grid(column=0, row=0, padx=10, pady=10, sticky=(tk.W, tk.E))

    button1_1 = ttk.Button(main_frame, text="Valid", command=valid_entry)
    button1_1.grid(column=0, row=1, padx=10, pady=10)

    button1_2 = ttk.Button(main_frame, text="Copy Entry to label", command=lambda: copy_entry_to_label(test_label))
    button1_2.grid(column=1, row=1, padx=10, pady=10)

    test_label = ttk.Label(main_frame, text="Test Label")
    test_label.grid(column=0, row=2, padx=10, pady=10)

    main_frame.columnconfigure(0, weight=1)

    entry.bind("<FocusOut>", valid_entry)
    entry.bind("<Return>", valid_entry)

    root.mainloop()


if __name__ == "__main__":
    main()
