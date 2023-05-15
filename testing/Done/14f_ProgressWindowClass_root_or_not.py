import os
import time
import tkinter as tk
from tkinter import ttk, messagebox

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.ProgressWindowsClass import ProgressWindow


def create_dict(*args, **kwargs):
    result_dict = {}
    # print(f"args: {args}")
    # print(f"kwargs: {kwargs}")
    l_max_value = kwargs.get('max_value')
    parent_window = gui_g.progress_window_ref
    for i in range(l_max_value):
        print(f"value: {i}")
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
    # The GUI issues are solved by running the function in a thread
    use_main_window = False
    max_value = 40

    if use_main_window:
        main_window = tk.Tk()
        main_window.title("Main Window")
        main_window.geometry("300x150")
        main_window.withdraw()

    progress_window = ProgressWindow(
        title="Creating Dictionary",
        width=300,
        height=150,
        max_value=max_value,
        show_start_button=True,
        show_stop_button=True,
        function=create_dict,
        function_parameters={'max_value': max_value}
    )

    progress_window.mainloop()
    print(f'progress_window.execution_return_value: {progress_window.get_result()}')
