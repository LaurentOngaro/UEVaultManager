# coding=utf-8
"""
global variables and references to global objects.
"""
# circular import error
# import UEVaultManager.tkgui.modules.DisplayContentWindowClass as DisplayContentWindow
import UEVaultManager.tkgui.modules.cls.EditCellWindowClass as EditCellWindow
import UEVaultManager.tkgui.modules.cls.EditRowWindowClass as EditRowWindow
from UEVaultManager.tkgui.modules.cls.GUISettingsClass import GUISettings
from UEVaultManager.tkgui.modules.cls.ProgressWindowClass import ProgressWindow
from UEVaultManager.tkgui.modules.cls.SaferDictClass import SaferDict

# references to global objects
edit_cell_window_ref: EditCellWindow = None
edit_row_window_ref: EditRowWindow = None
# circular import error
# display_content_window_ref: DisplayContentWindow = None
display_content_window_ref = None
# noinspection PyTypeChecker
progress_window_ref: ProgressWindow = None
tool_window_ref = None
# reference to the cli object of the UEVM main app (the main one, it gives all access to all the features)
# if empty, direct access to its features from this script won't be available and a message will be displayed instead
# noinspection PyTypeChecker
UEVM_cli_ref = None  # avoid importing classes from the UEVM main app here because it can cause circular dependencies when importing the module
# noinspection PyTypeChecker
UEVM_gui_ref = None  # avoid importing classes from the UEVM GUI class here because it can cause circular dependencies when importing the module
#  reference to the log object of the UEVM main app.
#  If empty, log will be message printed in the console
UEVM_log_ref = None
#  reference to the default command line parser (used for help button in gui).
UEVM_parser_ref = None

# global variables
# noinspection PyTypeChecker
UEVM_cli_args: SaferDict = {}
UEVM_filter_category = ''
UEVM_logger_names = []  # list of logger names used by UEVM classes

s = GUISettings()  # using the shortest variable name for GUISettings for convenience


# options that can be changed in the GUI
def set_args_force_refresh(value: bool) -> None:
    """
    Set the value of the argument force_refresh. Mandadory fot the associated ttk.ckbutton to work.
    :param value: True or False.
    """
    UEVM_cli_args['force_refresh'] = value


def set_args_offline(value: bool) -> None:
    """
    Set the value of the argument offline. Mandadory fot the associated ttk.ckbutton to work.
    :param value:  True or False.
    """
    UEVM_cli_args['offline'] = value


def set_args_debug(value: bool) -> None:
    """
    Set the value of the argument debug. Mandadory fot the associated ttk.ckbutton to work.
    :param value: True or False.
    """
    UEVM_cli_args['debug'] = value


def set_args_auth_delete(value: bool) -> None:
    """
    Set the value of the argument auth_delete. Mandadory fot the associated ttk.ckbutton to work.
    :param value: True or False.
    """
    UEVM_cli_args['auth_delete'] = value


def set_args_delete_metadata(value: bool) -> None:
    """
    Set the value of the argument delete_metadata. Mandadory fot the associated ttk.ckbutton to work.
    :param value:  True or False.
    """
    UEVM_cli_args['delete_metadata'] = value


def set_args_delete_extra_data(value: bool) -> None:
    """
    Set the value of the argument delete_extra_data. Mandadory fot the associated ttk.ckbutton to work.
    :param value:  True or False.
    """
    UEVM_cli_args['delete_extra_data'] = value


def set_args_delete_scraping_data(value: bool) -> None:
    """
    Set the value of the argument delete_scraping_data. Mandadory fot the associated ttk.ckbutton to work.
    :param value:  True or False.
    """
    UEVM_cli_args['delete_scraping_data'] = value


def set_use_threads(value: bool) -> None:
    """
    Set the value of the settings use_threads. Mandadory fot the associated ttk.ckbutton to work.
    :param value: True or False.
    """
    s.use_threads = value


# def set_testing_switch_var(value: bool) -> None:
#   Use method UEVMGuiOptionFrame.update_gui_options() instead because it also updates the gui

# def set_debug_gui_var(value: bool) -> None:
#   Use method UEVMGuiOptionFrame.update_gui_options() instead because it also updates the gui


def set_check_asset_folders(value: bool) -> None:
    """
    Set the value of the settings check_asset_folders. Mandadory fot the associated ttk.ckbutton to work.
    :param value: True or False.
    """
    s.check_asset_folders = value


def set_browse_when_add_row(value: bool) -> None:
    """
    Set the value of the settings browse_when_add_row. Mandadory fot the associated ttk.ckbutton to work.
    :param value: True or False.
    """
    s.browse_when_add_row = value
