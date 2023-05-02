import tkinter as tk
from tkinter import ttk
import threading
import time



class ProgressWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Progress Bar Example")

        self.progress = ttk.Progressbar(self, orient=tk.HORIZONTAL, length=300, mode='determinate')
        self.progress.pack(pady=10)

        self.label = tk.Label(self, text="0%")
        self.label.pack(pady=5)

        self.stop_button = tk.Button(self, text="Stop", command=self.stop_execution)
        self.stop_button.pack(pady=5)

        self.stop_requested = False

    def stop_execution(self):
        self.stop_requested = True


def loop_with_delay(val1, val2, progress_window=None):
    result = {}
    for i in range(val1, val2):
        if progress_window is not None:
            if progress_window.stop_requested:
                break

            progress_window.progress['value'] = i
            progress_window.label.config(text=f"{i}%")
            progress_window.update_idletasks()

        # Add a small delay to simulate processing time
        time.sleep(0.1)

        # Store the value in the result dictionary
        result[i] = i * 2

    return result


if __name__ == '__main__':
    window = ProgressWindow()

    def run_thread():
        thread_result = loop_with_delay(1, 100, window)
        print(thread_result)

    # Start the execution in a separate thread
    thread = threading.Thread(target=run_thread)
    thread.start()

    window.mainloop()

    # Wait for the execution thread to finish
    thread.join()
