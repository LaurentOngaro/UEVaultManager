import tkinter as tk
from tkinter import ttk
import time
import threading
import os


class gui_g:

    def __init__(self):
        self.progress_bar: ProgressBarApp = None


class ProgressBarApp(tk.Tk):

    def __init__(self, title, width, height, callable_function, max_value=100, icon_path=None):
        if callable_function is None:
            return

        super().__init__()

        self.title(title)
        self.geometry(f"{width}x{height}")

        if icon_path and os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        self.max_value = max_value
        self.continue_execution = True

        content_frame = ttk.Frame(self)
        content_frame.pack(fill='x', padx=5, pady=5)

        function_name_label = ttk.Label(content_frame, text='Running function: ' + callable_function.__name__)
        function_name_label.pack(fill=tk.X, padx=5, pady=5)

        progress_var = tk.IntVar()
        progress_bar = ttk.Progressbar(content_frame, orient="horizontal", mode="determinate", variable=progress_var, maximum=max_value)
        progress_bar.pack(fill='x', padx=5, pady=5)

        button_frame = ttk.Frame(self)
        button_frame.pack(padx=5, pady=5)

        start_button = ttk.Button(button_frame, text="Start", command=self.start_execution)
        start_button.pack(side='left', padx=5, pady=5)

        stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_execution, state=tk.DISABLED)
        stop_button.pack(side='left', padx=5, pady=5)

        self.stop_button = stop_button
        self.start_button = start_button
        self.progress_var = progress_var
        self.progress_bar = progress_bar
        self.called_function = callable_function
        gui_g.progress_bar = self

        self.activate()

    def start_execution(self) -> None:
        self.continue_execution = True
        threading.Thread(target=self.called_function).start()
        self.deactivate()

    def stop_execution(self) -> None:
        self.continue_execution = False
        self.activate()

    def activate(self) -> None:
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def deactivate(self) -> None:
        self.stop_button.config(state=tk.NORMAL)
        self.start_button.config(state=tk.DISABLED)

    def update_and_check(self, value) -> bool:
        self.progress_var.set(value)
        return self.continue_execution


def test_function():
    # Simulating a time-consuming task
    steps = 200
    for i in range(steps + 1):
        if not gui_g.progress_bar.update_and_check(i):
            break
        time.sleep(0.1)


if __name__ == "__main__":
    app = ProgressBarApp(title="Progress Bar with Stop Button Example", width=300, height=150, callable_function=test_function, max_value=200)
    app.mainloop()
