import tkinter as tk
from tkinter import ttk


class ExampleApp(tk.Tk):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Example App")
        self.geometry("300x200")

        self.label_frame = ttk.LabelFrame(self, text="Input Fields")
        self.label_frame.pack(padx=10, pady=10)

        for i in range(3):
            label = ttk.Label(self.label_frame, text=f"Label {i+1}")
            label.grid(row=i, column=0, padx=5, pady=5)
            label.tag = f"label_{i+1}"

            entry = ttk.Entry(self.label_frame)
            entry.grid(row=i, column=1, padx=5, pady=5)
            entry.tag = f"entry_{i+1}"

        self.print_button = ttk.Button(self, text="Print Children", command=self.print_children)
        self.print_button.pack(pady=10)

    def print_children(self):
        children = self.label_frame.winfo_children()
        for child in children:
            print(f"{child.__class__.__name__}: {child}, Tag: {child.tag}")

    def get_child_by_tag(self, tag):
        for child in self.label_frame.winfo_children():
            if hasattr(child, "tag") and child.tag == tag:
                return child
        return None


if __name__ == "__main__":
    app = ExampleApp()
    app.mainloop()
