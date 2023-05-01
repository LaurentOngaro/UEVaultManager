import UEVaultManager.tkgui.modules.EditCellWindowClass as EditCellWindow
import UEVaultManager.tkgui.modules.EditRowWindowClass as EditRowWindow
from UEVaultManager.tkgui.modules.GUISettingsClass import GUISettings
from UEVaultManager.tkgui.modules.UtilityClasses import SaferDict
from UEVaultManager.tkgui.modules.ProgressWindowsClass import ProgressWindow

# references to global objects
#
edit_cell_window_ref: EditCellWindow = None
edit_row_window_ref: EditRowWindow = None
progress_window_ref: ProgressWindow = None
# reference to the cli object of the UEVM main app (the main one, it gives all access to all the features)
# if empty, direct access to its features from this script won't be available and a message will be displayed instead
UEVM_cli_ref = None  # avoid importing classes from the UEVM main app here because it can cause circular dependencies when importing the module
UEVM_cli_args: SaferDict = None
#  reference to the log object of the UEVM main app.
#  If empty, log will be message printed in the console
UEVM_log_ref = None

s = GUISettings()  # using the shortest variable name for GUISettings for convenience
