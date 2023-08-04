# coding=utf-8
"""
Utilities functions and tools
These functions depend on the globals.py module and can generate circular dependencies when imported.
"""
import logging
import os
import sys
import time
import tkinter as tk
from io import BytesIO
from tkinter import messagebox

import requests
from PIL import ImageTk, Image
from termcolor import colored

from UEVaultManager.tkgui.modules import globals as gui_g


def log_format_message(name: str, levelname: str, message: str) -> str:
    """
    Format the log message.
    :param name: the name of the logger.
    :param levelname: the level of log.
    :param message: the message to format.
    :return: the formatted message.
    """
    return f'[{name}] {levelname}: {message}'


def box_message(msg: str, level='info'):
    """
    Display a message box with the given message.
    :param msg: the message to display.
    :param level: the level of the message (info, warning, error).
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
    Display a YES/NO message box with the given message.
    :param msg: the message to display .
    :return:  True if the user clicked on Yes, False otherwise.
    """
    return messagebox.askyesno(title=gui_g.s.app_title, message=msg)


def box_okcancel(msg: str) -> bool:
    """
    Display an OK/CANCEL message box with the given message.
    :param msg: the message to display.
    :return:  True if the user clicked on Yes, False otherwise.
    """
    return messagebox.askokcancel(title=gui_g.s.app_title, message=msg)


def todo_message() -> None:
    """
    Display a message box with a message saying that the feature is not implemented yet.
    """
    msg = 'Not implemented yet'
    print_msg = log_format_message(gui_g.s.app_title, 'info', colored(msg, 'yellow'))
    print(print_msg)
    messagebox.showinfo(title=gui_g.s.app_title, message=msg)


def from_cli_only_message(content='This feature is only accessible') -> None:
    """
    Display a message box with a message saying that the feature is only accessible when running the app using the UEVM cli command options.
    """
    msg = f'{content} when running these app using the UEVM cli command options. Once the UEVaultManager package installed, Type UEVaultManager -h for more help'
    print_msg = log_format_message(gui_g.s.app_title, 'info', colored(msg, 'yellow'))
    print(print_msg)
    messagebox.showinfo(title=gui_g.s.app_title, message=msg)


def log_info(msg: str) -> None:
    """
    Log an info message.
    :param msg: the message to log.
    """
    if gui_g.UEVM_log_ref is not None:
        gui_g.UEVM_log_ref.info(msg)
    else:
        print_msg = log_format_message(gui_g.s.app_title, 'info', colored(msg, 'blue'))
        print(print_msg)


def log_debug(msg: str) -> None:
    """
    Log a debug message. Note that this message will only be logged if the debug mode is enabled.
    :param msg: the message to log.
    """
    if not gui_g.s.debug_mode:
        return
    if gui_g.UEVM_log_ref is not None:
        # ensure that the debug messages will be logged even if the log level not set to DEBUG in the cli
        log_level = gui_g.UEVM_log_ref.level
        if log_level == logging.DEBUG:
            gui_g.UEVM_log_ref.debug(msg)
        else:
            gui_g.UEVM_log_ref.info(msg)
    else:
        print_msg = log_format_message(gui_g.s.app_title, 'Debug', colored(msg, 'light_grey'))
        print(print_msg)


def log_warning(msg: str) -> None:
    """
    Log a warning message.
    :param msg: the message to log.
    """
    if gui_g.UEVM_log_ref is not None:
        gui_g.UEVM_log_ref.info(msg)
    else:
        print_msg = log_format_message(gui_g.s.app_title, 'Warning', colored(msg, 'orange'))
        print(print_msg)


def log_error(msg: str) -> None:
    """
    Log an error message.
    :param msg: the message to log. Note that the app will exit after logging the message.
    """
    if gui_g.UEVM_log_ref is not None:
        gui_g.UEVM_log_ref.error(msg)
    else:
        print_msg = log_format_message(gui_g.s.app_title, 'Error', colored(msg, 'red', 'bold'))
        print(print_msg)
    if gui_g.UEVM_gui_ref is not None:
        gui_g.UEVM_gui_ref.quit()
    sys.exit(1)


def resize_and_show_image(image: Image, canvas: tk.Canvas) -> None:
    """
    Resize the given image and display it in the given canvas.
    :param image: the image to display.
    :param canvas: the canvas to display the image in.
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


def show_asset_image(image_url: str, canvas_image=None) -> None:
    """
    Show the image of the given asset in the given canvas.
    :param image_url: the url of the image to display.
    :param canvas_image: the canvas to display the image in.
    """
    if canvas_image is None or image_url is None or not image_url or str(image_url) == gui_g.s.empty_cell:
        return
    try:
        # noinspection DuplicatedCode
        if not os.path.isdir(gui_g.s.cache_folder):
            os.mkdir(gui_g.s.cache_folder)
        image_filename = os.path.join(gui_g.s.cache_folder, os.path.basename(image_url))
        # Check if the image is already cached
        if os.path.isfile(image_filename) and (time.time() - os.path.getmtime(image_filename)) < gui_g.s.image_cache_max_time:
            # Load the image from the cache folder
            image = Image.open(image_filename)
        else:
            response = requests.get(image_url)
            image = Image.open(BytesIO(response.content))

            with open(image_filename, "wb") as f:
                f.write(response.content)
        resize_and_show_image(image, canvas_image)
    except Exception as error:
        log_warning(f"Error showing image: {error}")


def show_default_image(canvas_image=None) -> None:
    """
    Show the default image in the given canvas.
    :param canvas_image: the canvas to display the image in.
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
        if output_on_gui and gui_g.display_content_window_ref is not None:
            gui_g.display_content_window_ref.display(result)
        else:
            print(result)


def custom_print(text='', keep_mode=True) -> None:
    """
    Print the given text on the GUI if it's available, otherwise print it on the console².
    :param text: the text to print.
    :param keep_mode: whether to keep the existing content when adding a new one.
    """
    if gui_g.display_content_window_ref is not None:
        gui_g.display_content_window_ref.display(content=text + '\n', keep_mode=keep_mode)
    else:
        print(text)
