import tkinter as tk
from tkinter import ttk
import threading
import time

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.ProgressWindowsClass import ProgressWindow


def loop_with_delay(start=0, end=100, progress_window: ProgressWindow = None):
    if progress_window is None:
        return {}
    result = {}
    for i in range(start, end):
        if progress_window is not None:
            if not progress_window.update_and_check(i):
                break
            progress_window.set_text(f"progress {i}")
        # Add a small delay to simulate processing time
        time.sleep(0.1)
        # print(f'Progress: {i}/{val2}')
        result[i] = i * 2
    return result


if __name__ == '__main__':
    max_value = 23
    min_value = 1
    progress_window = ProgressWindow("progress in a loop", 300, 150, max_value=max_value)
    progress_window.set_function(loop_with_delay)
    # window.set_function_parameters({min_value, max_value})  # could also be a dict
    progress_window.set_function_parameters({'start': min_value, 'end': max_value})  # could also be a list

    progress_window.start_execution()
    progress_window.mainloop()
    # progress_window.thread.join()
    print(f'#############################\nRESULTS\n{progress_window.execution_return_value}')
