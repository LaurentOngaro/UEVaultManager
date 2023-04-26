import UEVaultManager.tkgui.modules.EditCellWindowClass as EditCellWindow
import UEVaultManager.tkgui.modules.EditRowWindowClass as EditRowWindow
from UEVaultManager.cli import UEVaultManagerCLI
from UEVaultManager.tkgui.modules.GUISettingsClass import GUISettings

# global variables
#
edit_cell_window_ref: EditCellWindow
edit_row_window_ref: EditRowWindow
cli_ref: UEVaultManagerCLI

s = GUISettings()  # using the shortest variable name for GUISettings for convenience
