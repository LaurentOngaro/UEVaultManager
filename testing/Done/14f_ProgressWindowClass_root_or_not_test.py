import os
import time
import tkinter as tk
from tkinter import ttk, messagebox

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.ProgressWindowsClass import ProgressWindow

import tkinter as tk
from tkinter import ttk
import time


def create_dict(*args, **kwargs):
    result_dict = {}
    print(f"args: {args}")
    print(f"kwargs: {kwargs}")
    l_max_value = kwargs.get('max_value')
    parent_window = kwargs.get('parent_window')
    for i in range(l_max_value):
        key = f"key_{i}"
        value = f"value_{i}"
        result_dict[key] = value
        time.sleep(0.1)
        parent_window.set_value(i)

        if not parent_window.continue_execution:
            break

    return result_dict


if __name__ == "__main__":
    # this code works if there is a root window or not
    # If there is no root window the stop button and all other GUI elements are inactive
    # because the GUI needs to be run in another thread to be updated

    use_main_window = True
    max_value = 40

    if use_main_window:
        main_window = tk.Tk()
        main_window.title("Main Window")
        main_window.geometry("300x150")
        main_window.withdraw()

    progress_window = ProgressWindow(
        title="Creating Dictionary", width=300, height=150, max_value=max_value, show_start_button=True, show_stop_button=False, show_progress=True
    )

    progress_window.set_max_value(max_value)
    progress_window.set_function(create_dict)
    progress_window.set_function_parameters({'parent_window': progress_window, 'max_value': max_value})

    if use_main_window:
        # main_window.deiconify()
        main_window.mainloop()
    else:
        progress_window.mainloop()
