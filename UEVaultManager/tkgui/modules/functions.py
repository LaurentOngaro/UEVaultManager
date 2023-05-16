# coding=utf-8
"""
Utilities functions and tools
"""
import datetime
import os
import time
import tkinter as tk
from io import BytesIO
from tkinter import messagebox

import requests
import ttkbootstrap as ttk
from PIL import ImageTk, Image
from screeninfo import get_monitors
from termcolor import colored

from UEVaultManager.tkgui.modules import globals as gui_g


def log_format_message(name: str, levelname: str, message: str) -> str:
    """
    Format the log message
    :param name: the name of the logger
    :param levelname: the level of log
    :param message: the message to format
    :return: the formatted message
    """
    return f'[{name}] {levelname}: {message}'


def box_message(msg: str, level='info'):
    """
    Display a message box with the given message
    :param msg: the message to display
    :param level: the level of the message (info, warning, error)
    """
    level = level.lower()
    if level == 'warning':
        log_warning(msg)
        messagebox.showwarning(title=gui_g.s.app_title, message=msg)
    elif level == 'error':
        messagebox.showerror(title=gui_g.s.app_title, message=msg)
        log_error(msg)
        # done in log_error
        # exit(1)
    else:
        log_info(msg)
        messagebox.showinfo(title=gui_g.s.app_title, message=msg)


def box_yesno(msg: str) -> bool:
    """
    Display a message box with the given message and return True if the user clicked on Yes, False otherwise
    :param msg: the message to display 
    :return:  True if the user clicked on Yes, False otherwise
    """
    return messagebox.askyesno(title=gui_g.s.app_title, message=msg)


def todo_message() -> None:
    """
    Display a message box with a message saying that the feature is not implemented yet
    """
    msg = 'Not implemented yet'
    msg = log_format_message(gui_g.s.app_title, 'info', colored(msg, 'yellow'))
    print(msg)
    messagebox.showinfo(title=gui_g.s.app_title, message=msg)


def from_cli_only_message() -> None:
    """
    Display a message box with a message saying that the feature is only accessible when running the app using the UEVM cli command options
    """
    msg = 'This feature is only accessible when running these app using the UEVM cli command options. Once the UEVaultManager package installed, Type UEVaultManager -h for more help'
    msg = log_format_message(gui_g.s.app_title, 'info', colored(msg, 'yellow'))
    print(msg)
    messagebox.showinfo(title=gui_g.s.app_title, message=msg)


def log_info(msg: str) -> None:
    """
    Log an info message
    :param msg: the message to log
    """
    if gui_g.UEVM_log_ref is not None:
        gui_g.UEVM_log_ref.info(msg)
    else:
        msg = log_format_message(gui_g.s.app_title, 'info', colored(msg, 'blue'))
        print(msg)


def log_debug(msg: str) -> None:
    """
    Log a debug message. Note that this message will only be logged if the debug mode is enabled
    :param msg: the message to log
    """
    if not gui_g.s.debug_mode:
        return
    if gui_g.UEVM_log_ref is not None:
        gui_g.UEVM_log_ref.debug(msg)
    else:
        msg = log_format_message(gui_g.s.app_title, 'Debug', colored(msg, 'light_grey'))
        print(msg)


def log_warning(msg: str) -> None:
    """
    Log a warning message
    :param msg: the message to log
    """
    if gui_g.UEVM_log_ref is not None:
        gui_g.UEVM_log_ref.info(msg)
    else:
        msg = log_format_message(gui_g.s.app_title, 'Warning', colored(msg, 'orange'))
        print(msg)


def log_error(msg: str) -> None:
    """
    Log an error message
    :param msg: the message to log. Note that the app will exit after logging the message
    """
    if gui_g.UEVM_log_ref is not None:
        gui_g.UEVM_log_ref.error(msg)
    else:
        msg = log_format_message(gui_g.s.app_title, 'Error', colored(msg, 'red', 'bold'))
        print(msg)
    exit(1)


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


def convert_to_datetime(value: str) -> datetime.datetime:
    """
    Convert a value to a datetime
    :param value: the value to convert. If the value is not a datetime, it will be converted to a string and then to a datetime.
    :return: the datetime value
    """
    try:
        return datetime.datetime.strptime(value, gui_g.s.csv_datetime_format)
    except ValueError:
        return datetime.datetime.today()


# noinspection DuplicatedCode
def resize_and_show_image(image: Image, canvas: tk.Canvas) -> None:
    """
    Resize the given image and display it in the given canvas
    :param image: the image to display
    :param canvas: the canvas to display the image in
    """
    # Resize the image while keeping the aspect ratio
    target_height = gui_g.s.preview_max_height
    aspect_ratio = float(image.width) / float(image.height)
    target_width = int(target_height * aspect_ratio)
    resized_image = image.resize((target_width, target_height), Image.ANTIALIAS)
    tk_image = ImageTk.PhotoImage(resized_image)
    # Calculate center coordinates
    x = (canvas.winfo_width() - tk_image.width()) // 2
    y = (canvas.winfo_height() - tk_image.height()) // 2
    canvas.create_image(x, y, anchor=tk.NW, image=tk_image)
    canvas.image = tk_image


def path_from_relative_to_absolute(relative_path: str) -> str:
    """
    Build the path of the file to reference relative to the currently running script
    :param relative_path: the relative path to the file
    :return: the absolute path of the file
    """
    current_script_path = os.path.abspath(__file__)
    current_script_directory = os.path.dirname(current_script_path)
    absolute_path = os.path.join(current_script_directory, relative_path)
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
        log_warning(f'The screen #{screen_index} is not available. Using 0 as screen index.')
        screen_index = 0
    # Position the window in the center of the screen
    target_screen = monitors[screen_index]
    screen_width = target_screen.width
    screen_height = target_screen.height
    x = target_screen.x + (screen_width-width) // 2
    y = target_screen.y + (screen_height-height) // 2
    geometry: str = f'{width}x{height}+{x}+{y}'
    return geometry


def show_asset_image(image_url: str, canvas_image=None) -> None:
    """
    Show the image of the given asset in the given canvas
    :param image_url: the url of the image to display
    :param canvas_image: the canvas to display the image in
    """
    if canvas_image is None or image_url == '' or str(image_url).lower() == 'nan':
        return
    try:
        # noinspection DuplicatedCode
        if not os.path.isdir(gui_g.s.cache_folder):
            os.mkdir(gui_g.s.cache_folder)
        image_filename = os.path.join(gui_g.s.cache_folder, os.path.basename(image_url))
        # Check if the image is already cached
        if os.path.isfile(image_filename) and (time.time() - os.path.getmtime(image_filename)) < gui_g.s.cache_max_time:
            # Load the image from the cache folder
            image = Image.open(image_filename)
        else:
            response = requests.get(image_url)
            image = Image.open(BytesIO(response.content))

            with open(image_filename, "wb") as f:
                f.write(response.content)
        resize_and_show_image(image, canvas_image)
    except Exception as error:
        log_error(f"Error showing image: {error}")


def show_default_image(canvas_image=None) -> None:
    """
    Show the default image in the given canvas
    :param canvas_image: the canvas to display the image in
    """
    if canvas_image is None:
        return
    try:
        # Load the default image
        if os.path.isfile(gui_g.s.default_image_filename):
            def_image = Image.open(gui_g.s.default_image_filename)
            # noinspection PyTypeChecker
            resize_and_show_image(def_image, canvas_image)
    except Exception as error:
        log_warning(f"Error showing default image {gui_g.s.default_image_filename} cwd:{os.getcwd()}: {error}")


def tag_to_label(tag: str or None) -> str:
    """
    Convert a tag to a label
    :param tag: the tag to convert
    :return: the label
    """
    if tag is None:
        return ''

    return tag.capitalize().replace('_', ' ')


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
    return style


def json_print_key_val(json_obj, indent=4, print_result=True, output_on_gui=False) -> None:
    """
    Pretty prints a JSON object in a simple 'key: value' format.
    :param json_obj:  The JSON object to print.
    :param indent: The number of spaces to indent each level.
    :param print_result: Determines whether to print the result.
    :param output_on_gui: Determines whether to print the result on the GUI.
    :return: The pretty printed JSON object.
    """

    def _process(obj, level=0):
        lines = []
        indent_str = ' ' * indent * level

        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    lines.append(f'{indent_str}{key}:')
                    lines.extend(_process(value, level + 1))
                else:
                    lines.append(f'{indent_str}{key}: {value}')
        elif isinstance(obj, list):
            for item in obj:
                lines.extend(_process(item, level))
        else:
            lines.append(f'{indent_str}{obj}')

        return lines

    result = '\n'.join(_process(json_obj))

    if print_result:
        if output_on_gui and gui_g.UEVM_print_output_ref is not None:
            gui_g.UEVM_print_output_ref.print(result)
        else:
            print(result)
