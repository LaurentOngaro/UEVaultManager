"""
working file for the GUI integration in UEVaultManager

Bugs to confirm:

Bugs to fix:
- the url column is nan

To Do:
- add features and buttons to refresh csv file by calling UEVaultManager cli (WIP)
- integrate the code into the UEVaultManager code base (WIP)
- add more info about the current row (at least comment, review...) in the preview frame
- edit users fields (comment, alternative...) in the main windows (in the preview frame ?)
- save and load for tcsv files
- save and load for json files
- document the new features
- update the PyPi package

"""
import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.UEVMGuiClass import UEVMGui

if __name__ == '__main__':
    app_icon_filename = gui_f.path_from_relative_to_absolute(gui_g.s.app_icon_filename)
    csv_filename = gui_f.path_from_relative_to_absolute(gui_g.s.csv_filename)
    main_window = UEVMGui(
        title=gui_g.s.app_title, width=gui_g.s.app_width, height=gui_g.s.app_height, icon=app_icon_filename, screen_index=0, file=csv_filename
    )
    main_window.mainloop()
