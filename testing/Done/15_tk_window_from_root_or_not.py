import tkinter as tk
from tkinter import ttk
import time
import threading
import os


class ProgressBarApp(tk.Toplevel if tk._default_root else tk.Tk):

    def __init__(self, title, width, height, icon_path=None):
        super().__init__()

        self.title(title)
        self.geometry(f"{width}x{height}")

        if icon_path and os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill='x', padx=5, pady=5)

        self.function_name_label = ttk.Label(self.content_frame, text="Time-consuming Function")
        self.function_name_label.pack(fill='x', padx=5, pady=5)

        self.progress_var = tk.IntVar()
        self.progress_bar = ttk.Progressbar(self.content_frame, orient="horizontal", mode="determinate", variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill='x', padx=5, pady=5)

        self.button_frame = ttk.Frame(self)
        self.button_frame.pack(padx=5, pady=5)

        self.start_button = ttk.Button(self.button_frame, text="Start", command=self.start_time_consuming_function)
        self.start_button.pack(side='left', padx=5, pady=5)

        self.stop_button = ttk.Button(self.button_frame, text="Stop", command=self.stop_time_consuming_function, state=tk.DISABLED)
        self.stop_button.pack(side='left', padx=5, pady=5)

        self.continue_execution = True

    def time_consuming_function(self):
        steps = 100
        for i in range(steps + 1):
            if not self.continue_execution:
                break
            time.sleep(0.1)  # Simulating a time-consuming task
            self.progress_var.set(i)
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def start_time_consuming_function(self):
        self.continue_execution = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        threading.Thread(target=self.time_consuming_function).start()

    def stop_time_consuming_function(self):
        self.continue_execution = False
        self.stop_button.config(state=tk.DISABLED)


if __name__ == "__main__":

    main_window = tk.Tk()

    app = ProgressBarApp(title="Progress Bar with Stop Button Example", width=300, height=150, icon_path="icon.ico")
    app.mainloop()
