import datetime
import os
import time
import tkinter as tk
import requests
from io import BytesIO
from tkinter.messagebox import showinfo
from PIL import ImageTk, Image
from screeninfo import get_monitors
from UEVaultManager.tkgui.modules.settings import *


def todo_message():
    msg = 'Not implemented yet'
    showinfo(title=app_title, message=msg)


def log_info(msg):
    # will be replaced by a logger when integrated in UEVaultManager
    print(msg)


def log_debug(msg):
    if not debug_mode:
        return  # temp bypass
    # will be replaced by a logger when integrated in UEVaultManager
    print(msg)


def log_warning(msg):
    # will be replaced by a logger when integrated in UEVaultManager
    print(msg)


def log_error(msg):
    # will be replaced by a logger when integrated in UEVaultManager
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
        return datetime.datetime.strptime(value, csv_datetime_format)
    except ValueError:
        return ''


def resize_and_show_image(image, canvas, new_height, new_width):
    image = image.resize((new_width, new_height), Image.LANCZOS)
    canvas.config(width=new_width, height=new_height, image=None)
    canvas.image = ImageTk.PhotoImage(image)
    canvas.create_image(0, 0, anchor=tk.NW, image=canvas.image)


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


def show_asset_image(image_url, canvas_preview=None):
    if canvas_preview is None or image_url == '':
        return
    try:
        # noinspection DuplicatedCode
        if not os.path.isdir(cache_folder):
            os.mkdir(cache_folder)

        image_filename = os.path.join(cache_folder, os.path.basename(image_url))

        # Check if the image is already cached
        if os.path.isfile(image_filename) and (time.time() - os.path.getmtime(image_filename)) < cache_max_time:
            # Load the image from the cache folder
            image = Image.open(image_filename)
        else:
            response = requests.get(image_url)
            image = Image.open(BytesIO(response.content))

            with open(image_filename, "wb") as f:
                f.write(response.content)

        # Calculate new dimensions while maintaining the aspect ratio
        width_ratio = preview_max_width / float(image.width)
        height_ratio = preview_max_height / float(image.height)
        ratio = min(width_ratio, height_ratio, 1)
        new_width = min(int(image.width * ratio), preview_max_width)
        new_height = min(int(image.height * ratio), preview_max_height)
        log_debug(f'Image size: {image.width}x{image.height} -> {new_width}x{new_height} ratio: {ratio}')
        # noinspection PyTypeChecker
        resize_and_show_image(image, canvas_preview, new_height, new_width)

    except Exception as error:
        log_error(f"Error showing image: {error}")


def show_default_image(canvas_preview=None):
    if canvas_preview is None:
        return
    try:
        # Load the default image
        if os.path.isfile(default_image_filename):
            def_image = Image.open(default_image_filename)
            # noinspection PyTypeChecker
            resize_and_show_image(def_image, canvas_preview, preview_max_width, preview_max_height)
    except Exception as error:
        log_warning(f"Error showing default image {default_image_filename} cwd:{os.getcwd()}: {error}")
