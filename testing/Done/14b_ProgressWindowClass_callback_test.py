import os
import time
import tkinter as tk
from tkinter import ttk, messagebox

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.ProgressWindowsClass import ProgressWindow


def test_callback():
    # Simulating a time-consuming task
    if gui_g.progress_window_ref is None:
        return
    steps = 200
    for i in range(steps + 1):
        if not gui_g.progress_window_ref.update_and_check(i):
            break
        time.sleep(0.1)
        print(f'Progress: {i}/{steps}')


if __name__ == "__main__":
    # Create a base window for testing purposes
    # windows = tk.Tk()
    # frame = tk.Frame(windows)
    # frame.pack(fill='both', expand=True)
    # tk_label = tk.Label(frame, text="This is just a windows for testing purposes")
    # tk_label.pack(fill='both', expand=True)
    # progress_window = ProgressWindow(title="Progress Bar Example", width=300, height=150, threaded_function=test_callback, max_value=200)

    windows = ProgressWindow(title="Progress Bar Example", width=300, height=150, threaded_function=test_callback, max_value=200)
    windows.mainloop()
