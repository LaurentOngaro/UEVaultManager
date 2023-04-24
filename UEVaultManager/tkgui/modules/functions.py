import datetime
import os
import tkinter as tk
from tkinter.messagebox import showinfo
from PIL import ImageTk, Image
from UEVaultManager.tkgui.modules.settings import *


# global functions
#
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
