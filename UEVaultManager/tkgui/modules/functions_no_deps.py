# coding=utf-8
"""
Utilities functions and tools
These functions DO NOT depend on the globals.py module and be freely imported
"""
import ctypes as ct
import os
import sys

import ttkbootstrap as ttk
from screeninfo import get_monitors


def path_from_relative_to_absolute(path: str) -> str:
    """
    Build the path of the file to reference relative to the currently running script
    :param path: the relative path to the file. If the path is already absolute, it is returned as is
    :return: the absolute path of the file
    """

    if os.path.isabs(path):
        return path

    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        # noinspection PyProtectedMember,PyUnresolvedReferences
        # base_path = sys._MEIPASS
        current_script_directory = sys._MEIPASS
        # when launched from pyinstaller, the path has been copied at the root of the folder where the script is run. So we nne to remove all the relative path indicator
        path = os.path.basename(path)
    except AttributeError:
        # base_path = os.path.abspath(".")
        current_script_path = os.path.abspath(__file__)
        current_script_directory = os.path.dirname(current_script_path)

    absolute_path = os.path.join(current_script_directory, path)
    absolute_path = os.path.abspath(absolute_path)
    # messagebox.showinfo('info', 'absolute_path: ' + absolute_path)
    return absolute_path


def center_window_on_screen(screen_index: int, height: int, width: int) -> str:
    """
    Calculate the geometry of the window to display in the center of the given screen
    :param screen_index: the index of the screen to use
    :param height: the height of the window
    :param width: the width of the window
    :return: the geometry string to use to display the window in the center of the screen
    """
    monitors = get_monitors()
    if screen_index > len(monitors):
        print(f'The screen #{screen_index} is not available. Using 0 as screen index.')  # no use of log functions here to prevent circular import
        screen_index = 0
    # Position the window in the center of the screen
    target_screen = monitors[screen_index]
    screen_width = target_screen.width
    screen_height = target_screen.height
    x = target_screen.x + (screen_width-width) // 2
    y = target_screen.y + (screen_height-height) // 2
    geometry: str = f'{width}x{height}+{x}+{y}'
    return geometry


def set_custom_style(theme_name='lumen', font=('Arial', 10, 'normal')):
    """
    Set the custom style for the application
    :return: the style object
    """
    style = ttk.Style(theme_name)
    # option possible for ttk widgets:
    # TButton, TCheckbutton, TCombobox, TEntry, TFrame, TLabel, TLabelFrame, TMenubutton, TNotebook, TProgressbar, TRadiobutton,
    # TScale, TScrollbar, TSeparator, TSizegrip, Treeview, TPanedwindow,
    # Horizontal.TProgressbar or Vertical.TProgressbar (depending on the orient option),
    # Horizontal.TScale or Vertical.TScale (depending on the orient option),
    # Horizontal.TScrollbar or Vertical.TScrollbar (depending on the orient option)
    style.configure('TLabel', font=font, spacing=1, padding=2)
    style.configure('TButton', font=font, spacing=1, padding=2)
    style.configure('TEntry', font=font, spacing=1, padding=2)
    style.configure('TFrame', font=font, spacing=1, padding=1)
    style.configure('TCombobox', font=font, spacing=1, padding=1)
    style.configure('TLabelFrame', font=font, spacing=1, padding=1)
    return style


def set_toolbar_style(tk_window) -> None:
    """
    Remove the minimize and maximize buttons from a tkinter window.
    This version is compatible with Windows AND Non-windows OS
    # see https://stackoverflow.com/questions/2969870/removing-minimize-maximize-buttons-in-tkinter
    :param tk_window: the tkinter window
    """
    try:
        set_window_pos = ct.windll.user32.SetWindowPos
        set_window_long = ct.windll.user32.SetWindowLongPtrW
        get_window_long = ct.windll.user32.GetWindowLongPtrW
        get_parent = ct.windll.user32.GetParent
    except AttributeError:
        # Non-windows OS
        print('Non-windows OS detected. No need to remove the minimize and maximize buttons from the window.')
        return
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


def set_icon_and_minmax(tk_window, icon=None) -> None:
    """
    Set the icon and remove the min/max buttons of the window if no icon is provided
    :param tk_window:
    :param icon:
    """
    if icon is None:
        # remove the min/max buttons of the window
        # this code works on Window only
        # tk_window.attributes('-toolwindow', True)
        tk_window.after(300, lambda: set_toolbar_style(tk_window))
    else:
        # windows only (remove the minimize/maximize buttons and the icon)
        icon = path_from_relative_to_absolute(icon)
        if icon != '' and os.path.isfile(icon):
            tk_window.iconbitmap(icon)


def create_empty_file(file_path: str) -> str:
    """
    Create an empty file
    :param file_path: the path of the file to create
    :return: the path of the file
    """
    path = os.path.dirname(file_path)
    file = os.path.basename(file_path)
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except (OSError, PermissionError) as e:
            print(f'Error while creating the directory {path}: {e}')
            if home_dir := os.environ.get('XDG_CONFIG_HOME'):
                path = os.path.join(home_dir, 'UEVaultManager')
            else:
                path = os.path.expanduser('~/.config/UEVaultManager')
            if not os.path.exists(path):
                os.makedirs(path)
            file_path = os.path.normpath(os.path.join(path, file))
            print(f'The following file {file_path} will be used as default')
    open(file_path, 'a').close()
    return file_path


def convert_to_bool(value) -> bool:
    """
    Convert a value to a boolean
    :param value: the value to convert. If the value is not a boolean, it will be converted to a string and then to a boolean.
    :return:
    """
    try:
        if str(value).lower() in ('1', '1.0', 'true', 'yes', 'y', 't'):
            return True
        else:
            return False
    except ValueError:
        return False
