# coding=utf-8
"""
Implementation for:
- GUISettings: class containing all the settings for the GUI
"""
import os

from termcolor import colored

import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn
from UEVaultManager.lfs.utils import clean_filename
from UEVaultManager.models.config import AppConf

# NOTE : we can't import the following modules here because of circular dependencies
# UEVaultManager.tkgui.modules.functions_no_deps


def log(msg: str) -> None:
    """
    Print a message to the console
    :param msg: the message to log
    """
    msg = colored(msg, 'orange')
    print(msg)


class GUISettings:
    """
    This class contains all the settings for the GUI.
    :param config_file: Path to config file to use instead of default

    """

    def __init__(self, config_file=None):
        self.debug_mode = False
        self.path = ''
        self.config_path = ''
        self.config = AppConf(comment_prefixes='/', allow_no_value=True)

        # the following folders are relative to the current file location
        # they must be used trought path_from_relative_to_absolute
        self.assets_folder = gui_fn.path_from_relative_to_absolute('../../assets')
        self.cache_folder = gui_fn.path_from_relative_to_absolute('../../../cache')
        self.results_folder = gui_fn.path_from_relative_to_absolute('../../../results')

        self.init_gui_config_file(config_file)

        self.app_icon_filename = os.path.join(self.assets_folder, 'main.ico')  # must be used trought path_from_relative_to_absolute
        self.csv_filename = os.path.join(self.results_folder, 'list.csv')
        self.default_image_filename = os.path.join(self.assets_folder, 'UEVM_200x200.png')  # must be used trought path_from_relative_to_absolute

        # speed the update process by not updating the metadata files
        self.never_update_data_files = False  # Debug only
        # enable or not the cell coloring depending on otys content. Enable it could slow down data and display refreshing
        self.use_colors_for_data = True
        self.app_title = 'UEVM Gui'
        self.app_width = 1600
        self.app_height = 935
        self.app_monitor = 1
        self.csv_datetime_format = '%Y-%m-%d %H:%M:%S'
        self.data_filetypes = (('csv file', '*.csv'), ('tcsv file', '*.tcsv'), ('json file', '*.json'), ('text file', '*.txt'))
        self.cache_max_time = 60 * 60 * 24 * 15  # 15 days
        self.preview_max_width = 150
        self.preview_max_height = 150
        self.default_global_search = 'Text to search...'
        self.default_category_for_all = 'All'
        self.empty_cell = 'nan'
        self.expand_columns_factor = 20
        self.contract_columns_factor = 20
        # ttkbootstrap themes:
        # light themes : "cosmo", "flatly", "litera", "minty", "lumen", "sandstone", "yeti", "pulse", "united", "morph", "journal", "simplex", "cerculean"
        # dark themes: "darkly", "superhero", "solar", "cyborg", "vapor"
        self.theme_name = 'lumen'
        self.theme_font = ('Verdana', 8)
        self.datatable_default_pref = {
            'align': 'w',  #
            'cellbackgr': '#F4F4F3',  #
            'cellwidth': 100,  #
            'floatprecision': 2,  #
            'thousandseparator': '',  #
            'font': 'Verdana',  #
            'fontsize': 8,  #
            'fontstyle': '',  #
            'grid_color': '#ABB1AD',  #
            'linewidth': 1,  #
            'rowheight': 22,  #
            'rowselectedcolor': '#E4DED4',  #
            'textcolor': 'black'  #
        }

    def init_gui_config_file(self, config_file: str = '') -> None:
        """
        Initialize the config file for the gui
        :param config_file: the path to the config file to use
        """
        if config_path := os.environ.get('XDG_CONFIG_HOME'):
            self.path = os.path.join(config_path, 'UEVaultManager')
        else:
            self.path = os.path.expanduser('~/.config/UEVaultManager')
        if config_file:
            if os.path.exists(config_file):
                self.config_path = os.path.abspath(config_file)
            else:
                self.config_path = os.path.join(self.path, clean_filename(config_file))
            log(f'UEVMGui is using non-default config file "{self.config_path}"')
        else:
            self.config_path = os.path.join(self.path, 'config_gui.ini')

        # try loading config
        try:
            self.config.read(self.config_path)
        except Exception as error:
            log(f'Unable to read configuration file, please ensure that file is valid! '
                f'(Error: {repr(error)})')
            log('Continuing with blank config in safe-mode...')
            self.config.read_only = True

        # make sure "UEVaultManager" section exists
        has_changed = False
        if 'UEVaultManager' not in self.config:
            self.config.add_section('UEVaultManager')
            has_changed = True

        # Add opt-out options with explainers
        if not self.config.has_option('UEVaultManager', 'start_in_edit_mode'):
            self.config.set('UEVaultManager', '; start the App in Edit mode (since v1.4.4) with the GUI')
            self.config.set('UEVaultManager', 'start_in_edit_mode', 'false')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'disable_update_check'):
            self.config.set('UEVaultManager', '; Disables the automatic update check')
            self.config.set('UEVaultManager', 'disable_update_check', 'false')
            has_changed = True

        if not self.config.has_option('UEVaultManager', 'create_output_backup'):
            self.config.set(
                'UEVaultManager',
                '; Create a backup of the output file (when using the --output option) suffixed by a timestamp before creating a new file'
            )
            self.config.set('UEVaultManager', 'create_output_backup', 'true')
            has_changed = True

        if not self.config.has_option('UEVaultManager', 'verbose_mode'):
            self.config.set('UEVaultManager', '; Print more information during long operations')
            self.config.set('UEVaultManager', 'verbose_mode', 'false')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'ue_assets_max_cache_duration'):
            self.config.set('UEVaultManager', '; Delay (in seconds) when UE assets metadata cache will be invalidated. Default value is 15 days')
            self.config.set('UEVaultManager', 'ue_assets_max_cache_duration', '1296000')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'ignored_assets_filename_log'):
            self.config.set(
                'UEVaultManager', '; Set the file name (and path) for logging issues with assets when running the --list command' + "\n" +
                '; use "~/" at the start of the filename to store it relatively to the user directory'
            )
            self.config.set('UEVaultManager', 'ignored_assets_filename_log', '~/.config/ignored_assets.log')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'notfound_assets_filename_log'):
            self.config.set('UEVaultManager', 'notfound_assets_filename_log', '~/.config/notfound_assets.log')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'bad_data_assets_filename_log'):
            self.config.set('UEVaultManager', 'bad_data_assets_filename_log', '~/.config/bad_data_assets.log')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'engine_version_for_obsolete_assets'):
            self.config.set('UEVaultManager', '; Set the minimal unreal engine version to check for obsolete assets (default is 4.26)')
            self.config.set('UEVaultManager', 'engine_version_for_obsolete_assets', '4.26')
            has_changed = True

        if has_changed:
            self.save_config()

    def save_config(self) -> None:
        """
        Save the config file
        """
        # do not save if in read-only mode or file hasn't changed
        if self.config.read_only or not self.config.modified:
            return
        # if config file has been modified externally, back-up the user-modified version before writing
        if os.path.exists(self.config_path):
            if (mod_time := int(os.stat(self.config_path).st_mtime)) != self.config.mod_time:
                new_filename = f'config.{mod_time}.ini'
                log(
                    f'Configuration file has been modified while UEVaultManager was running, '
                    f'user-modified config will be renamed to "{new_filename}"...'
                )
                os.rename(self.config_path, os.path.join(os.path.dirname(self.config_path), new_filename))

        with open(self.config_path, 'w') as cf:
            self.config.write(cf)
