# coding=utf-8
"""
GUI module for UEVaultManager
this can be run directly by executing this script
or by the --edit command option for the UEVaultManager cli application, for instance by running `cli --edit --input <my_source_file>'
"""
import os.path

import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.cls.EditableTableClass import DataSourceType
from UEVaultManager.tkgui.modules.cls.UEVMGuiClass import UEVMGui
from UEVaultManager.tkgui.modules.functions import log_error

test_only_mode = True  # add some limitations to speed up the dev process - Set to True for debug Only


def init_gui(open_mainwindow=True, use_db=False) -> str:
    """
    Main function for the GUI
    :param open_mainwindow: if True, the main window will be opened (default mode).
            Set to False for running the GUI initialization only, useful if called from cli.py
    :param use_db: if True, the database will be used instead of the csv file
    :return: the path to the csv file to use at startup. It's used when the window is opened from the cli.py script
    """
    gui_g.s.app_icon_filename = gui_fn.path_from_relative_to_absolute(gui_g.s.app_icon_filename)
    rebuild = False
    if use_db:
        data_source = gui_fn.path_from_relative_to_absolute(gui_g.s.sqlite_filename)
        data_source_type = DataSourceType.SQLITE
        if not os.path.isfile(data_source):
            log_error(f'Database File {data_source} not found. Exiting...')
            exit(1)
    else:
        data_source_type = DataSourceType.FILE
        data_source = gui_fn.path_from_relative_to_absolute(gui_g.s.csv_filename)
        if not os.path.isfile(data_source):
            _, data_source = gui_fn.create_empty_file(data_source)
            rebuild = True
    if open_mainwindow:
        main_window = UEVMGui(
            title=gui_g.s.app_title,
            icon=gui_g.s.app_icon_filename,
            screen_index=0,
            data_source_type=data_source_type,
            data_source=data_source,
            rebuild_data=rebuild
        )
        main_window.mainloop()

    return data_source


if __name__ == '__main__':
    init_gui(open_mainwindow=True, use_db=not test_only_mode)
