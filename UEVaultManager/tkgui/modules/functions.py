import datetime
import os
import time
import tkinter as tk
from io import BytesIO
from tkinter import messagebox

import requests
from PIL import ImageTk, Image
from screeninfo import get_monitors
from termcolor import colored

import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience


def log_format_message(name, levelname, message):
    return f'[{name}] {levelname}: {message}'


def box_message(msg, level='info'):
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


def box_yesno(msg):
    return messagebox.askyesno(title=gui_g.s.app_title, message=msg)


def todo_message():
    msg = 'Not implemented yet'
    msg = log_format_message(gui_g.s.app_title, 'info', colored(msg, 'yellow'))
    print(msg)
    messagebox.showinfo(title=gui_g.s.app_title, message=msg)


def from_cli_only_message():
    msg = 'This feature is only accessible when running these app using the UEVM cli command options. Once the UEVaultManager package installed, Type UEVaultManager -h for more help'
    msg = log_format_message(gui_g.s.app_title, 'info', colored(msg, 'yellow'))
    print(msg)
    messagebox.showinfo(title=gui_g.s.app_title, message=msg)


def log_info(msg):
    if gui_g.UEVM_log_ref is not None:
        gui_g.UEVM_log_ref.info(msg)
    else:
        msg = log_format_message(gui_g.s.app_title, 'info', colored(msg, 'blue'))
        print(msg)


def log_debug(msg):
    if not gui_g.s.debug_mode:
        return
    if gui_g.UEVM_log_ref is not None:
        gui_g.UEVM_log_ref.debug(msg)
    else:
        msg = log_format_message(gui_g.s.app_title, 'Debug', colored(msg, 'light_grey'))
        print(msg)


def log_warning(msg):
    if gui_g.UEVM_log_ref is not None:
        gui_g.UEVM_log_ref.info(msg)
    else:
        msg = log_format_message(gui_g.s.app_title, 'Warning', colored(msg, 'orange'))
        print(msg)


def log_error(msg):
    if gui_g.UEVM_log_ref is not None:
        gui_g.UEVM_log_ref.error(msg)
    else:
        msg = log_format_message(gui_g.s.app_title, 'Error', colored(msg, 'red', 'bold'))
        print(msg)
    exit(1)


def convert_to_bool(x):
    try:
        if str(x).lower() in ('1', '1.0', 'true', 'yes', 'y', 't'):
            return True
        else:
            return False
    except ValueError:
        return False


# convert x to a datetime using the format in csv_datetime_format
def convert_to_datetime(value):
    try:
        return datetime.datetime.strptime(value, gui_g.s.csv_datetime_format)
    except ValueError:
        return ''


# noinspection DuplicatedCode
def resize_and_show_image(image, canvas):
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


# Build the path of the file to reference relative to the currently running script
def path_from_relative_to_absolute(relative_path):
    current_script_path = os.path.abspath(__file__)
    current_script_directory = os.path.dirname(current_script_path)
    absolute_path = os.path.join(current_script_directory, relative_path)
    return absolute_path


def center_window_on_screen(screen_index, height, width):
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


def show_asset_image(image_url, canvas_image=None):
    if canvas_image is None or image_url == '':
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


def show_default_image(canvas_image=None):
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
