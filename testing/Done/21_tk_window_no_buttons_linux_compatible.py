import ctypes as ct
from tkinter import *


# see https://stackoverflow.com/questions/2969870/removing-minimize-maximize-buttons-in-tkinter
def set_toolbar_style(tk_window) -> None:
    """
    Remove the minimize and maximize buttons from a tkinter window
    :param tk_window: the tkinter window
    """
    set_window_pos = ct.windll.user32.SetWindowPos
    set_window_long = ct.windll.user32.SetWindowLongPtrW
    get_window_long = ct.windll.user32.GetWindowLongPtrW
    get_parent = ct.windll.user32.GetParent
    # Identifiers
    gwl_style = -16
    ws_minimizebox = 131072
    ws_maximizebox = 65536
    swp_nozorder = 4
    swp_nomove = 2
    swp_nosize = 1
    swp_framechanged = 32
    hwnd = get_parent(tk_window.winfo_id())
    old_style = get_window_long(hwnd, gwl_style)  # Get the style
    new_style = old_style & ~ws_maximizebox & ~ws_minimizebox  # New style, without max/min buttons
    set_window_long(hwnd, gwl_style, new_style)  # Apply the new style
    set_window_pos(hwnd, 0, 0, 0, 0, 0, swp_nomove | swp_nosize | swp_nozorder | swp_framechanged)  # Updates


window = Tk()
Button(window, text="button").pack()  # add your widgets here.
# call to change style after the mainloop started.
# Directly call set_toolbar_style will not work.
window.after(100, lambda: set_toolbar_style(window))
window.mainloop()
