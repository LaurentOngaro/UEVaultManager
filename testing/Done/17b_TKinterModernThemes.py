import TKinterModernThemes as TKMT
from TKinterModernThemes.WidgetFrame import Widget
from tkinter import ttk
import tkinter as tk


class App(TKMT.ThemedTKinterFrame):

    def __init__(self, theme, mode, usecommandlineargs=True, usethemeconfigfile=True):
        super().__init__(str("TITLE"), theme, mode, usecommandlineargs, usethemeconfigfile)

        # Labels
        label = ttk.Label(text="This is old text")
        label.config(text="This is new text")
        label.pack()

        # Buttons
        def action():
            print("Do something")

        # calls action() when pressed
        button = ttk.Button(text="Click Me", command=action)
        button.pack()

        # Entries
        entry = ttk.Entry(width=30)
        # Add some text to begin with
        entry.insert(tk.END, string="Some text to begin with.")
        # Gets text in entry
        print(entry.get())
        entry.pack()

        # Text
        text = tk.Text(height=5, width=30)
        # Puts cursor in textbox.
        text.focus()
        # Adds some text to begin with.
        text.insert(tk.END, "Example of multi-line text entry.")
        # Get's current value in textbox at line 1, character 0
        print(text.get("1.0", tk.END))
        text.pack()

        # Spinbox
        def spinbox_used():
            # gets the current value in spinbox.
            print(spinbox.get())

        spinbox = ttk.Spinbox(from_=0, to=10, width=5, command=spinbox_used)
        spinbox.pack()

        # Scale
        # Called with current scale value.
        def scale_used(value):
            print(value)

        scale = ttk.Scale(from_=0, to=100, command=scale_used)
        scale.pack()

        # Checkbutton
        def checkbutton_used():
            # Prints 1 if On button checked, otherwise 0.
            print(checked_state.get())

        # variable to hold on to checked state, 0 is off, 1 is on.
        checked_state = tk.IntVar()
        checkbutton = ttk.Checkbutton(text="Is On?", variable=checked_state, command=checkbutton_used)
        checked_state.get()
        checkbutton.pack()

        # Radiobutton
        def radio_used():
            print(radio_state.get())

        # Variable to hold on to which radio button value is checked.
        radio_state = tk.IntVar()
        radiobutton1 = ttk.Radiobutton(text="Option1", value=1, variable=radio_state, command=radio_used)
        radiobutton2 = ttk.Radiobutton(text="Option2", value=2, variable=radio_state, command=radio_used)
        radiobutton1.pack()
        radiobutton2.pack()

        # Listbox
        def listbox_used(event):
            # Gets current selection from listbox
            print(listbox.get(listbox.curselection()))

        listbox = tk.Listbox(height=4)
        fruits = ["Apple", "Pear", "Orange", "Banana"]
        for item in fruits:
            listbox.insert(fruits.index(item), item)
        listbox.bind("<<ListboxSelect>>", listbox_used)
        listbox.pack()


if __name__ == "__main__":
    main = App(str("sun-valley"), str("light"))
    main.run()
