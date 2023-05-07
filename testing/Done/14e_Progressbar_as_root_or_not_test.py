import tkinter as tk
from tkinter import ttk
import time


def create_dict(*args, **kwargs):
    result_dict = {}
    print(f"args: {args}")
    print(f"kwargs: {kwargs}")
    max_value = kwargs.get('max_value')
    parent_window = kwargs.get('parent_window')
    for i in range(max_value):
        key = f"key_{i}"
        value = f"value_{i}"
        result_dict[key] = value
        time.sleep(0.1)
        parent_window.set_value(i)

        if not parent_window.continue_execution:
            break

    return result_dict


class ProgressWindow(tk.Toplevel if tk._default_root else tk.Tk):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Progress Window")

        self.entry = tk.Entry(self)
        self.entry.pack(pady=10)

        self.progress = ttk.Progressbar(self, orient="horizontal", length=200, mode="determinate")
        self.progress.pack(pady=10)

        self.start_button = ttk.Button(self, text="Start!", command=self.start_execution)
        self.start_button.pack(pady=10)

        self.stop_button = ttk.Button(self, text="Stop", command=self.stop_execution)
        self.stop_button.pack(pady=10)

        self.continue_execution = True
        self.function_name = None
        self.function_params = {}

    def set_value(self, value):
        self.progress["value"] = value
        self.update_idletasks()

    def set_max_value(self, new_max_value):
        if new_max_value:
            self.progress["maximum"] = new_max_value

    def set_function(self, function_name):
        self.function_name = function_name

    def set_function_parameters(self, params: {}):
        self.function_params = params

    def start_execution(self):
        self.continue_execution = True
        self.start_button.pack_forget()
        if self.function_name is not None:
            function = globals().get(self.function_name)
            if function:
                function(self, **self.function_params)
        print(f"Quitting {self.__class__.__name__} ")
        self.quit()

    def stop_execution(self):
        print("Stop execution")
        self.continue_execution = False

    def update_progress(self, value):
        self.progress["value"] = value
        self.progress.update_idletasks()
        self.update_idletasks()


if __name__ == "__main__":
    # this code works if there is a root window or not
    # If there is no root window the stop button and all other GUI elements are inactive
    # because the GUI needs to be run in another thread to be updated

    use_main_window = True

    if use_main_window:
        main_window = tk.Tk()
        main_window.title("Main Window")
        main_window.geometry("300x150")
        main_window.withdraw()

    max_value = 40
    app = ProgressWindow()
    app.set_max_value(max_value)
    app.set_function("create_dict")
    app.set_function_parameters({'parent_window': app, 'max_value': max_value})

    if use_main_window:
        # main_window.deiconify()
        main_window.mainloop()
    else:
        app.mainloop()
