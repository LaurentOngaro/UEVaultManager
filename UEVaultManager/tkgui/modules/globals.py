import UEVaultManager.tkgui.modules.EditCellWindowClass as EditCellWindow
import UEVaultManager.tkgui.modules.EditRowWindowClass as EditRowWindow
from UEVaultManager.tkgui.modules.GUISettingsClass import GUISettings

# global variables
#
edit_cell_window_ref: EditCellWindow
edit_row_window_ref: EditRowWindow
UEVM_cli_ref = None  # can not import the UEVaultManagerCLI class here because of circular dependencies if importing the module

s = GUISettings()  # using the shortest variable name for GUISettings for convenience
