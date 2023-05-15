import tkinter as tk


class App(tk.Tk):

    def __init__(self):
        super().__init__()

        self.title('Tkinter LabelFrame Example')

        self.outer_frame = tk.Frame(self)
        self.outer_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.label_frame = tk.LabelFrame(self.outer_frame, text="My Label Frame")
        self.label_frame.pack(fill=tk.X, expand=True)

        self.entry = tk.Entry(self.label_frame)
        self.entry.grid(row=0, column=0, columnspan=3, sticky='ew')

        self.button1 = tk.Button(self.label_frame, text="Button 1")
        self.button1.grid(row=1, column=0, sticky='ew')

        self.button2 = tk.Button(self.label_frame, text="Button 2")
        self.button2.grid(row=1, column=1, sticky='ew')

        self.button3 = tk.Button(self.label_frame, text="Button 3")
        self.button3.grid(row=1, column=2, sticky='ew')

        # Configure columns to have equal weight
        self.label_frame.columnconfigure(0, weight=1)
        self.label_frame.columnconfigure(1, weight=1)
        self.label_frame.columnconfigure(2, weight=1)


if __name__ == '__main__':
    app = App()
    app.mainloop()
