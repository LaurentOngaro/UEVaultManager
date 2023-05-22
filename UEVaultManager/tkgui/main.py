# coding=utf-8
"""
GUI module for UEVaultManager
this can be run directly by executing this script
or by the --edit command option for the UEVaultManager cli application, for instance by running `cli --edit --input <my_source_file>'
"""
import os.path

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.UEVMGuiClass import UEVMGui

if __name__ == '__main__':
    app_icon_filename = gui_f.path_from_relative_to_absolute(gui_g.s.app_icon_filename)
    csv_filename = gui_f.path_from_relative_to_absolute(gui_g.s.csv_filename)
    rebuild = False
    if not os.path.isfile(csv_filename):
        gui_f.create_empty_file(csv_filename)
        rebuild = True
    main_window = UEVMGui(
        title=gui_g.s.app_title, width=gui_g.s.app_width, height=gui_g.s.app_height, icon=app_icon_filename, screen_index=0, file=csv_filename, rebuild_data=rebuild
    )
    main_window.mainloop()
