# coding=utf-8
"""
GUI module for UEVaultManager
this can be run directly by executing this script
or by the --edit command option for the UEVaultManager cli application, for instance by running `cli --edit --input <my_source_file>'
"""
import os.path

import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.UEVMGuiClass import UEVMGui


def init_gui(open_mainwindow=True) -> str:
    """
    Main function for the GUI
    :param open_mainwindow: if True, the main window will be opened (default mode).
            Set to False for running the GUI initialization only, useful if called from cli.py
    :return: the path to the csv file to use at startup. It's used when the window is opened from the cli.py script
    """
    app_icon_filename = gui_fn.path_from_relative_to_absolute(gui_g.s.app_icon_filename)
    csv_filename = gui_fn.path_from_relative_to_absolute(gui_g.s.csv_filename)
    rebuild = False
    if not os.path.isfile(csv_filename):
        gui_fn.create_empty_file(csv_filename)
        rebuild = True
    if open_mainwindow:
        main_window = UEVMGui(
            title=gui_g.s.app_title,
            width=gui_g.s.app_width,
            height=gui_g.s.app_height,
            icon=app_icon_filename,
            screen_index=0,
            file=csv_filename,
            rebuild_data=rebuild
        )
        main_window.mainloop()

    return csv_filename


if __name__ == '__main__':
    init_gui()
