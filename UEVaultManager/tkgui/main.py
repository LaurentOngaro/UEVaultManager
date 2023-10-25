# coding=utf-8
"""
GUI module for UEVaultManager
this can be run directly by executing this script
or by the --edit command option for the UEVaultManager cli application, for instance by running cli --edit --input <my_source_file>.
"""
import os.path

import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.cls.UEVMGuiClass import UEVMGui
from UEVaultManager.tkgui.modules.functions import log_error
from UEVaultManager.tkgui.modules.types import DataSourceType


def init_gui(open_gui_window=True, use_db=False) -> str:
    """
    Main function for the GUI.
    :param open_gui_window: whether the main window will be opened (default mode).
            Set to False for running the GUI initialization only, useful if called from cli.py.
    :param use_db: whether the database will be used instead of the csv file.
    :return: path to the csv file to use at startup. It's used when the window is opened from the cli.py script.
    """
    gui_g.s.app_icon_filename = gui_fn.path_from_relative_to_absolute(gui_g.s.app_icon_filename)
    rebuild = False
    if use_db:
        data_source = gui_fn.path_from_relative_to_absolute(gui_g.s.sqlite_filename)
        data_source_type = DataSourceType.DATABASE
        if not os.path.isfile(data_source):
            log_error(f'Database File {data_source} not found. Application will be closed')
            exit(1)
    else:
        data_source_type = DataSourceType.FILE
        data_source = gui_fn.path_from_relative_to_absolute(gui_g.s.csv_filename)
        if not os.path.isfile(data_source):
            _, data_source = gui_fn.create_empty_file(data_source)
            rebuild = True
    if open_gui_window:
        gui_windows = UEVMGui(
            title=gui_g.s.app_title_long,
            icon=gui_g.s.app_icon_filename,
            screen_index=0,
            data_source_type=data_source_type,
            data_source=data_source,
        )
        # we delay the setup method because it could create a progressWindow, and it MUST be created AFTER the mainloop to avoid a "main thread is not in main loop" message
        gui_windows.after(500, lambda : gui_windows.setup(rebuild_data=rebuild))
        gui_windows.mainloop()

    return data_source


if __name__ == '__main__':
    init_gui(open_gui_window=True, use_db=gui_g.s.testing_switch <= 0)
