import UEVaultManager.tkgui.modules.EditCellWindowClass as EditCellWindow
import UEVaultManager.tkgui.modules.EditRowWindowClass as EditRowWindow
from UEVaultManager.tkgui.modules.GUISettingsClass import GUISettings

# reference to global object
#
edit_cell_window_ref: EditCellWindow
edit_row_window_ref: EditRowWindow
# reference to the cli object of the UEVM main app (the main one, it gives all access to all the features)
# if empty, direct access to its features from this script won't be available and a message will be displayed instead
UEVM_cli_ref = None  # avoid importing classes from the UEVM main app here because it can cause circular dependencies when importing the module
#  reference to the log object of the UEVM main app.
#  If empty, log will be message printed in the console
UEVM_log_ref = None  # avoid importing classes from the UEVM main app here because it can cause circular dependencies when importing the module

s = GUISettings()  # using the shortest variable name for GUISettings for convenience
