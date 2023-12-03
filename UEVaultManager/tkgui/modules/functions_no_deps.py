# coding=utf-8
"""
Utilities functions and tools
These functions DO NOT depend on the globals.py module and be freely imported.
"""
import ast
import ctypes as ct
import datetime
import os
import subprocess
import sys
import uuid
from typing import Optional

import ttkbootstrap as ttk
from screeninfo import get_monitors
from ttkbootstrap.publisher import Publisher

from UEVaultManager.lfs.utils import path_join


def log(message: str) -> None:
    """
    Log a message in the console.
    :param message: message to log.
    """
    # keep this function as simple as possible to avoid circular import
    print(message)


def path_from_relative_to_absolute(path: str) -> str:
    """
    Build the path of the file to reference relative to the currently running script.
    :param path: relative path to the file. If the path is already absolute, it is returned as is.
    :return: absolute path of the file.
    """
    if os.path.isabs(path):
        return os.path.normpath(path)

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

    absolute_path = path_join(current_script_directory, path)
    return os.path.normpath(absolute_path)


def center_window_on_screen(screen_index: int, width: int, height: int, set_size: bool = True) -> str:
    """
    Calculate the geometry of the window to display in the center of the given screen.
    :param screen_index: index of the screen to use.
    :param width: width of the window.
    :param height: height of the window.
    :param set_size: wether to set the size of the window or not.
    :return: geometry string to use to display the window in the center of the screen.
    """
    x, y = get_center_screen_positions(screen_index, width, height)
    x = f'+{x}'  # keep the sign !
    y = f'+{y}'  # keep the sign !
    geometry: str = f'{width}x{height}{x}{y}' if set_size else f'{x}{y}'
    return geometry


def get_screen_positions(screen_index: int) -> (int, int, int, int):
    """
    Return the x and y positions of the given screen.
    :param screen_index: index of the screen to use.
    :return: (x, y, w, h) positions of the given screen.
    """
    monitors = get_monitors()
    if screen_index > len(monitors):
        log(f'The screen #{screen_index} is not available. Using 0 as screen index.')  # no use of log functions here to prevent circular import
        screen_index = 0
    target_screen = monitors[screen_index]
    return target_screen.x, target_screen.y, target_screen.width, target_screen.height


def get_center_screen_positions(screen_index: int, width: int, height: int) -> (int, int):
    """
    Return the x and y positions of the window to display in the center of the given screen.
    :param screen_index: index of the screen to use.
    :param width: width of the window.
    :param height: height of the window.
    :return: (x, y) positions of the window to display in the center of the given screen.
    """
    screen_x, screen_y, screen_w, screen_h = get_screen_positions(screen_index)
    x = screen_x + (screen_w - width) // 2
    y = screen_y + (screen_h - height) // 2
    return x, y


def set_custom_style(theme_name='lumen', font=('Arial', 10, 'normal')):
    """
    Set the custom style for the application.
    :return: Style object.
    """
    try:
        style = ttk.Style(theme_name)
    except (Exception, ):
        # free the subscriber widgets to the Style. As it, it could be used by other window without issue
        Publisher.clear_subscribers()
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
    # see https://stackoverflow.com/questions/2969870/removing-minimize-maximize-buttons-in-tkinter.
    :param tk_window: tkinter window.
    """
    try:
        set_window_pos = ct.windll.user32.SetWindowPos
        set_window_long = ct.windll.user32.SetWindowLongPtrW
        get_window_long = ct.windll.user32.GetWindowLongPtrW
        get_parent = ct.windll.user32.GetParent
    except AttributeError:
        # Non-windows OS
        log('Non-windows OS detected. No need to remove the minimize and maximize buttons from the window.')
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
    Set the icon and remove the min/max buttons of the window if no icon is provided.
    :param tk_window: tkinter window.
    :param icon: path of the icon to use.
    """
    if icon is None:
        # remove the min/max buttons of the window
        # this code works on Window only
        # tk_window.attributes('-toolwindow', True)
        tk_window.after(300, lambda: set_toolbar_style(tk_window))
    else:
        # windows only (remove the minimize/maximize buttons and the icon)
        icon = path_from_relative_to_absolute(icon)
        if icon and os.path.isfile(icon):
            try:
                tk_window.iconbitmap(icon)
            except Exception as error:
                # in linux, the ico can exist but not be readable
                log(f'Error while setting the icon: {error!r}')


def create_empty_file(file_path: str) -> (bool, str):
    """
    Create an empty file.
    :param file_path: path of the file to create.
    :return: (True if path was valid, the corrected path of the file).
    """
    path, file = os.path.split(file_path)
    is_valid, path = check_and_get_folder(path)
    file_path = path_join(path, file)
    open(file_path, 'w').close()
    return is_valid, file_path


def check_and_get_folder(folder_path: str) -> (bool, str):
    """
    Check if the folder exists. If not, create it or use the default one.
    :param folder_path: path of the folder to check.
    :return: (True if path was valid, the corrected path of the folder).
    """
    path = folder_path
    is_valid = True
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except (OSError, PermissionError) as error:
            is_valid = False
            log(f'Error while creating the directory {path}: {error!r}')
            if home_dir := os.environ.get('XDG_CONFIG_HOME'):
                path = path_join(home_dir, 'UEVaultManager')
            else:
                path = os.path.expanduser('~/.config/UEVaultManager')
            if not os.path.exists(path):
                os.makedirs(path)
            path = os.path.normpath(path)
            log(f'The following folder {path} will be used as default')
    return is_valid, path


def convert_to_bool(value) -> bool:
    """
    Convert a value to a boolean. Useful for None values.
    :param value: value to convert. If the value is not a boolean, it will be converted to a string and then to a boolean.
    :return: boolean value.
    """
    try:
        if str(value).lower() in ('1', '1.0', 'true', 'yes', 'y', 't'):
            return True
        else:
            return False
    except (TypeError, ValueError):
        return False


def convert_to_int(value, prefix: str = '') -> int:
    """
    Convert a value to an integer.
    :param value: value to convert.
    :param prefix: prefix to remove from the value before converting it to an integer.
    :return: integer value or 0 if the value is None or not an integer.
    """
    # remove prefix if any
    if prefix and isinstance(value, str) and value.startswith(prefix):
        value = value[len(prefix):]
    try:
        value = int(value)
        return value
    except (TypeError, ValueError):
        return 0


def convert_to_float(value) -> float:
    """
    Convert a value to a float. Useful for None values.
    :param value: value to convert.
    :return: float value or 0.0 if the value is None or not a float.
    """
    try:
        value = float(value)
        return value
    except (TypeError, ValueError):
        return 0.0


def convert_to_datetime(value: str, formats_to_use='%Y-%m-%d %H:%M:%S', default=None) -> datetime.datetime:
    """
    Convert a value to a datetime object.
    :param value: value to convert. If the value is not a datetime, it will be converted to a string and then to a datetime.
    :param formats_to_use: list of format to use to trye to convert the value. They will be tried in order.
    :param default: default value to return if the conversion fails. If None, the default value is 1970-01-01 00:00:00.
    :return: datetime value.
    """
    if default is None:
        default = datetime.datetime(1970, 1, 1)
    if not value:
        return default
    if not isinstance(formats_to_use, list):
        formats_to_use = [formats_to_use]
    for date_format in formats_to_use:
        try:
            value_date = datetime.datetime.strptime(value, date_format)
            if value_date != datetime.datetime(1970, 1, 1):
                return value_date
        except (TypeError, ValueError, AttributeError):
            continue

    return default


def convert_to_str_datetime(value, date_format='%Y-%m-%d %H:%M:%S', default=None) -> str:
    """
    Convert a value to a datetime string.
    :param value: value to convert. If the value is not a datetime.
    :param date_format: format of value.
    :param default: default value to return if the conversion fails. If None, the default value is 1970-01-01 00:00:00.
    :return: string value of the datetime.
    """
    # we convert only datetime object
    if isinstance(value, str):
        return value

    if default is None:
        default = datetime.datetime(1970, 1, 1).strftime(date_format)
    if not value:
        return default
    try:
        return value.strftime(date_format)
    except (TypeError, ValueError, AttributeError):
        return default


def is_an_int(value, prefix: str = '', prefix_is_mandatory: bool = False) -> bool:
    """
    Check if a value is an integer.
    :param value: value to check.
    :param prefix: prefix to remove from the value before checking if it is an integer.
    :param prefix_is_mandatory: wether the prefix is mandatory or not.
    :return: True if the value is an integer, False otherwise.
    """
    # check prefix if any
    if prefix and isinstance(value, str) and value.startswith(prefix):
        value = value[len(prefix):]
    elif prefix_is_mandatory:
        return False
    try:
        float_n = float(value)
        int_n = int(float_n)
    except (Exception, ):
        return False
    else:
        return float_n == int_n


def create_uid() -> str:
    """
    Create a unique id.
    :return: unique id.
    """
    return str(uuid.uuid4())[:8]


# def create_id_from_origin(string: str) -> str:
#     """
#     Create a hash from a string.
#     :return: unique hash.
#     """
#     # hash may return different values for same string, as PYTHONHASHSEED Value will change everytime you run your program. You may want to set it to some fixed value. Read here
#     # ignoring 1st character as it may be the negative sign.
#     return str(hash(string))[1:13]


def shorten_text(url: str, limit: int = 30, prefix: str = '...') -> str:
    """
    Shorten an url. Get its last part
    :param url:  the url to shorten.
    :param limit: limit of characters to keep.
    :param prefix: prefix to add to the shorted url (if it has been shorted).
    :return: shortened url.
    """
    if len(url) < limit:
        return url
    else:
        return prefix + url[-limit:]


def extract_variables_from_url(url: str) -> dict:
    """
    Extract variables from an url.
    :param url: url to extract variables from.
    :return: dict containing the variable.
    """
    result = {}
    url_parts = url.split('?')
    if len(url_parts) == 2:
        url_params = url_parts[1].split('&')
        extracted_data = {}
        for param in url_params:
            key, value = param.split('=')
            extracted_data[key] = value
        result = extracted_data
    return result


def open_folder_in_file_explorer(folder_path) -> bool:
    """
    Open a folder in the file explorer.
    :param folder_path: path of the folder to open.
    """
    if os.path.exists(folder_path):
        try:
            # For Windows
            if os.name == 'nt':
                # if we use check = True, it will raise an error even if the folder is opened, because this command always return 1 on windows
                process = subprocess.run(['explorer', folder_path], check=False)
                result = process.returncode == 0 or process.returncode == 1
            # For macOS
            elif os.name == 'posix':
                process = subprocess.run(['open', folder_path], check=False)
                result = process.returncode == 0
            # For Linux
            else:
                process = subprocess.run(['xdg-open', folder_path], check=False)
                result = process.returncode == 0
            return result
        except subprocess.CalledProcessError as error:
            log(f'Failed to open {folder_path} in file explorer.Error code: {error!r}')
            return False
    else:
        return False


def append_no_duplicate(list_to_append: list, items: any, ok_if_exists: object = False) -> bool:
    """
    Append some items value to a list. Could raise an error if an object is already in the list.
    :param list_to_append: list to append to.
    :param items: items to append to the list. Could be a single object or a list of items.
    :param ok_if_exists: wether no error will be raised if an object is already in the list.
    :return: True if all the items were appended, False if at least one was already in the list.
    """
    if not isinstance(items, list):
        items = [items]
    for item in items:
        if item not in list_to_append:
            list_to_append.append(item)
        else:
            if not ok_if_exists:
                raise ValueError(f'append_no_duplicate method: Value {item} already in list {list_to_append}')
            return False
    return True


def merge_lists_or_strings(list_to_merge, list_to_append) -> list:
    """
    Merge 2 lists (or strings) without duplicates.
    :param list_to_merge: list to merge. Could be a list or a string of values separated by commas.
    :param list_to_append: list to append Could be a list or a string of values separated by commas.
    :return: merged list.
    """
    if isinstance(list_to_merge, str):
        list_to_merge = list_to_merge.split(',') if list_to_merge else []
    if isinstance(list_to_append, str):
        list_to_append = list_to_append.split(',') if list_to_append else []
    # merge the 2 lists without duplicates
    # old method
    # for folder in set(list_to_merge + list_to_append):
    #     if folder not in list_to_merge:
    #         list_to_merge.append(folder)
    # return list_to_merge
    # shorter method
    return list(set(list_to_merge + list_to_append))  # no sorting here because the order could stay first In first Out


def remove_last_suffix(string: str, separator: str = '_') -> str:
    """
    Remove the last suffix from a string.
    :param string: String to remove the suffix from.
    :param separator: separator to use to split the string.
    :return: string without the last suffix.
    """
    parts = string.split(separator)
    if len(parts) > 1:
        parts.pop()
        return separator.join(parts)
    return string


def format_size(size: int, precision: int = 1) -> str:
    """
    Format a size in bytes to a human-readable string.
    :param size: size to format.
    :param precision: number of digits after the decimal point.
    :return: formatted size.
    """
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
    suffix_index = 0
    while size > 1024 and suffix_index < 4:
        suffix_index += 1  # increment the index of the suffix
        size /= 1024.0  # apply the division
    return f'{size:.{precision}f}{suffixes[suffix_index]}'


def check_and_convert_list_to_str(str_or_list) -> str:
    """
    Check if the given parameter is a list and convert it to a string, else return the given parameter.
    :param str_or_list: string or list to convert.
    :return: converted string or the given parameter.
    """
    result = str_or_list
    # Note: can not use isinstance because 'Index', 'ndarray' and 'dict_values' are not recognized as types
    if type(str_or_list).__name__ in ('list', 'dict_values', 'Index', 'ndarray'):
        result = ','.join([str(value) for value in str_or_list])
    return result


def get_and_check_release_info(data_to_check, empty_values: list = None) -> Optional[list]:
    """
    Check if the given data is a list of release info.
    :param data_to_check: data to check.
    :param empty_values: list of values to consider as empty.
    :return: list of release info or None if the data is not valid.
    """
    if not data_to_check or (empty_values and data_to_check in empty_values):
        return []
    try:
        max_tries = 3
        tries = 0
        # Note:
        #   here we use ast.literal_eval instead of json.loads because it can raise an error if the string came from a datatable and uses ' instead of " for string literals
        while '[{\"id\":' in str(data_to_check) and tries < max_tries:
            # fix a multiple encoding issue. Should not occur
            # data_to_check = json.loads(data_to_check)
            tries += 1
            data_to_check = ast.literal_eval(data_to_check)
        if isinstance(data_to_check, str):
            # data_to_check = json.loads(data_to_check)
            data_to_check = ast.literal_eval(data_to_check)
        if not isinstance(data_to_check, list):
            return None
        return list(data_to_check)
    except (Exception, ):
        return None
