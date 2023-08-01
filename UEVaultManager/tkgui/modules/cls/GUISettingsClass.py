# coding=utf-8
"""
Implementation for:
- GUISettings: a class that contains all the settings for the GUI.
"""
import json
import os

from termcolor import colored

import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn
from UEVaultManager import __name__, __version__, __codename__
from UEVaultManager.lfs.utils import clean_filename
from UEVaultManager.models.config import AppConf


# NOTE: we can't import the following modules here because of circular dependencies
# UEVaultManager.tkgui.modules.functions_no_deps


def log_info(msg: str) -> None:
    """
    Print a message to the console.
    :param msg: the message to log_info.
    """
    msg = colored(msg, 'orange')
    print(msg)


class GUISettings:
    """
    A class that contains all the settings for the GUI.
    :param config_file: Path to config file to use instead of default
.
    """

    def __init__(self, config_file=None):
        self.path = ''
        self.config_path = ''
        self.config = AppConf(comment_prefixes='/', allow_no_value=True)

        self.init_gui_config_file(config_file)

        self.config_vars = self.read_config_properties()
        # the following folders are relative to the current file location
        # they must be used trought path_from_relative_to_absolute
        # following vars are not set as properties to avoid storing absolute paths in the config file
        self.cache_folder = gui_fn.path_from_relative_to_absolute(self.config_vars['cache_folder'])
        self.results_folder = gui_fn.path_from_relative_to_absolute(self.config_vars['results_folder'])
        self.scraping_folder = gui_fn.path_from_relative_to_absolute(self.config_vars['scraping_folder'])

        # Folder for assets (aka. images, icon... not "UE assets") used for the GUI. THIS IS NOT A SETTING THAT CAN BE CHANGED BY THE USER
        self.assets_folder = gui_fn.path_from_relative_to_absolute('../../assets')

        self.app_icon_filename = os.path.join(self.assets_folder, 'main.ico')
        self.default_image_filename = os.path.join(self.assets_folder, 'UEVM_200x200.png')

        if self.config_vars['reopen_last_file'] and os.path.isfile((self.config_vars['last_opened_file'])):
            self.csv_filename = self.config_vars['last_opened_file']
        else:
            self.csv_filename = os.path.join(self.results_folder, 'list.csv')

        self.sqlite_filename = os.path.join(self.scraping_folder, 'assets.db')

        self.app_title = f'{__name__} Gui v{__version__} ({__codename__})'
        self.app_monitor = 1
        self.csv_options = {'on_bad_lines': 'warn', 'encoding': 'utf-8', 'keep_default_na': True}
        # if a file extension is in this tuple, the parent folder is considered as a valid UE folder
        self.ue_valid_file_content = ('.uplugin', '.uproject')
        # if a folder is in this tuple, the parent folder is considered as a valid ue folder
        self.ue_valid_folder_content = ('content')
        # if a folder is in this tuple, the folder won't be scanned to find ue folders
        self.ue_invalid_folder_content = ('binaries', 'build', 'deriveddatacache', 'intermediate', 'saved')
        # if a folder is in this tuple, the folder could be a valid folder but with an incomplete structure
        self.ue_possible_folder_content = ('blueprints', 'maps', 'textures', 'materials')

        self.csv_datetime_format = '%Y-%m-%d %H:%M:%S'
        self.epic_datetime_format = '%Y-%m-%dT%H:%M:%S.%fZ'
        self.data_filetypes = (
            ('csv file', '*.csv'), ('tcsv file', '*.tcsv'), ('json file', '*.json'), ('text file', '*.txt'), ('sqlite file', '*.db')
        )
        # minimal score required when looking for an url file comparing to an asset name.
        # some comparison are more fuzzy than others, so we can set a different score for each comparison
        # The key is a string that must be in the url file name or asset name
        # default value if no key is found
        self.minimal_fuzzy_score_by_name = {'default': 70, 'brushify': 80}
        self.preview_max_width = 150
        self.preview_max_height = 150
        self.default_global_search = 'Text to search...'
        self.default_value_for_all = 'All'
        self.empty_cell = 'None'
        self.empty_row_prefix = 'dummy_row_'
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
        self.engine_version_for_obsolete_assets = '4.26'  # fallback value when cli.core.engine_version_for_obsolete_assets is not available without import

    def get_rows_per_page(self):
        """ Getter for rows_per_page """
        return gui_fn.convert_to_int(self.config_vars['rows_per_page'])

    def set_rows_per_page(self, value):
        """ Setter for rows_per_page """
        self.config_vars['rows_per_page'] = value

    # used as property for keeping transparent access
    rows_per_page = property(get_rows_per_page, set_rows_per_page)

    def get_data_filters(self):
        """ Getter for data_filters """
        json_str = self.config_vars['data_filters']
        try:
            values_dict = json.loads(json_str)
        except json.decoder.JSONDecodeError:
            values_dict = {}
        return values_dict

    def set_data_filters(self, values_dict):
        """ Setter for data_filters """
        if values_dict is None or values_dict == {}:
            json_str = ''
        else:
            json_str = json.dumps(values_dict, skipkeys=True, allow_nan=True)
        self.config_vars['data_filters'] = json_str

    # used as property for keeping transparent access
    data_filters = property(get_data_filters, set_data_filters)

    def get_x_pos(self):
        """ Getter for x_pos """
        return gui_fn.convert_to_int(self.config_vars['x_pos'])

    def set_x_pos(self, value):
        """ Setter for x_pos """
        self.config_vars['x_pos'] = value

    # used as property for keeping transparent access
    x_pos = property(get_x_pos, set_x_pos)

    def get_y_pos(self):
        """ Getter for y_pos """
        return gui_fn.convert_to_int(self.config_vars['y_pos'])

    def set_y_pos(self, value):
        """ Setter for y_pos """
        self.config_vars['y_pos'] = value

    # used as property for keeping transparent access
    y_pos = property(get_y_pos, set_y_pos)

    def get_width(self):
        """ Getter for width """
        return gui_fn.convert_to_int(self.config_vars['width'])

    def set_width(self, value):
        """ Setter for width """
        self.config_vars['width'] = value

    # used as property for keeping transparent access
    width = property(get_width, set_width)

    def get_height(self):
        """ Getter for height """
        return gui_fn.convert_to_int(self.config_vars['height'])

    def set_height(self, value):
        """ Setter for height """
        self.config_vars['height'] = value

    # used as property for keeping transparent access
    height = property(get_height, set_height)

    def get_debug_mode(self):
        """ Getter for debug_mode """
        return self.config_vars['debug_mode']

    def set_debug_mode(self, value):
        """ Setter for debug_mode """
        self.config_vars['debug_mode'] = value

    # used as property for keeping transparent access
    debug_mode = property(get_debug_mode, set_debug_mode)

    def get_never_update_data_files(self):
        """ Getter for never_update_data_files """
        return gui_fn.convert_to_bool(self.config_vars['never_update_data_files'])

    def set_never_update_data_files(self, value):
        """ Setter for never_update_data_files """
        self.config_vars['never_update_data_files'] = value

    # used as property for keeping transparent access
    never_update_data_files = property(get_never_update_data_files, set_never_update_data_files)

    def get_reopen_last_file(self):
        """ Getter for reopen_last_file """
        return gui_fn.convert_to_bool(self.config_vars['reopen_last_file'])

    def set_reopen_last_file(self, value):
        """ Setter for reopen_last_file """
        self.config_vars['reopen_last_file'] = value

    # used as property for keeping transparent access
    reopen_last_file = property(get_reopen_last_file, set_reopen_last_file)

    def get_use_colors_for_data(self):
        """ Getter for use_colors_for_data """
        return gui_fn.convert_to_bool(self.config_vars['use_colors_for_data'])

    def set_use_colors_for_data(self, value):
        """ Setter for use_colors_for_data """
        self.config_vars['use_colors_for_data'] = value

    # used as property for keeping transparent access
    use_colors_for_data = property(get_use_colors_for_data, set_use_colors_for_data)

    def get_image_cache_max_time(self):
        """ Getter for image_cache_max_time """
        return gui_fn.convert_to_int(self.config_vars['image_cache_max_time'])

    def set_image_cache_max_time(self, value):
        """ Setter for image_cache_max_time """
        self.config_vars['image_cache_max_time'] = value

    # used as property for keeping transparent access
    image_cache_max_time = property(get_image_cache_max_time, set_image_cache_max_time)

    def get_last_opened_file(self):
        """ Getter for last_opened_file """
        return self.config_vars['last_opened_file']

    def set_last_opened_file(self, value):
        """ Setter for last_opened_file """
        self.config_vars['last_opened_file'] = value

    # used as property for keeping transparent access
    last_opened_file = property(get_last_opened_file, set_last_opened_file)

    def get_cache_folder(self):
        """ Getter for cache_folder """
        return self.config_vars['cache_folder']

    def set_cache_folder(self, value):
        """ Setter for cache_folder """
        self.config_vars['cache_folder'] = value

    # not used as property to avoid storing absolute paths in the config file. Getter and setter could be used to store relative paths
    # cache_folder = property(get_cache_folder, set_cache_folder)

    def get_results_folder(self):
        """ Getter for results_folder """
        return self.config_vars['results_folder']

    def set_results_folder(self, value):
        """ Setter for results_folder """
        self.config_vars['results_folder'] = value

    def get_scraping_folder(self):
        """ Getter for scraping_folder """
        return self.config_vars['scraping_folder']

    def set_scraping_folder(self, value):
        """ Setter for scraping_folder """
        self.config_vars['scraping_folder'] = value

    # not used as property to avoid storing absolute paths in the config file. Getter and setter could be used to store relative paths
    # scraping_folder = property(get_scraping_folder, set_scraping_folder)

    def get_folders_to_scan(self):
        """ Getter for folders_to_scan """
        json_str = self.config_vars['folders_to_scan']
        try:
            values = json.loads(json_str)
        except json.decoder.JSONDecodeError:
            values = []
        return values

    def set_folders_to_scan(self, values):
        """ Setter for folders_to_scan """
        if values is None or values == []:
            json_str = ''
        else:
            json_str = json.dumps(values, skipkeys=True, allow_nan=True)
        self.config_vars['folders_to_scan'] = json_str

    folders_to_scan = property(get_folders_to_scan, set_folders_to_scan)

    def get_data_filters(self):
        """ Getter for data_filters """
        json_str = self.config_vars['data_filters']
        try:
            values_dict = json.loads(json_str)
        except json.decoder.JSONDecodeError:
            values_dict = {}
        return values_dict

    def set_data_filters(self, values_dict):
        """ Setter for data_filters """
        if values_dict is None or values_dict == {}:
            json_str = ''
        else:
            json_str = json.dumps(values_dict, skipkeys=True, allow_nan=True)
        self.config_vars['data_filters'] = json_str

    def init_gui_config_file(self, config_file: str = '') -> None:
        """
        Initialize the config file for the gui.
        :param config_file: the path to the config file to use.
        """
        if config_path := os.environ.get('XDG_CONFIG_HOME'):
            self.path = os.path.join(config_path, 'UEVaultManager')
        else:
            self.path = os.path.expanduser('~/.config/UEVaultManager')
        if not os.path.isdir(self.path):
            os.makedirs(self.path)
        if config_file:
            if os.path.exists(config_file):
                self.config_path = os.path.abspath(config_file)
            else:
                self.config_path = os.path.join(self.path, clean_filename(config_file))
            log_info(f'UEVMGui is using non-default config file "{self.config_path}"')
        else:
            self.config_path = os.path.join(self.path, 'config_gui.ini')

        # try loading config
        try:
            self.config.read(self.config_path)
        except Exception as error:
            log_info(f'Unable to read configuration file, please ensure that file is valid!:Error: {error!r}')
            log_info('Continuing with blank config in safe-mode...')
            self.config.read_only = True
        config_defaults = {
            'rows_per_page': {
                'comment':
                'Number of Rows displayed or scraped per page.If this value is changed all the scraped files must be updated to match the new value',
                'value': 36
            },
            'data_filters': {
                'comment': 'Filters to apply to the datatable. Stored in json format',
                'value': ''
            },
            'x_pos': {
                'comment': 'X position of the main windows. Set to 0 to center the window',
                'value': 0
            },
            'y_pos': {
                'comment': 'Y position of the main windows. Set to 0 to center the window',
                'value': 0
            },
            'width': {
                'comment': 'Width of the main windows',
                'value': 1750
            },
            'height': {
                'comment': 'Height of the main windows',
                'value': 940
            },
            'debug_mode': {
                'comment': 'Set to True to print debug information (GUI related only)',
                'value': 'False'
            },
            'never_update_data_files': {
                'comment': 'Set to True to speed the update process by not updating the metadata files. FOR TESTING ONLY',
                'value': 'False'
            },
            'reopen_last_file': {
                'comment': 'Set to True to re-open the last file at startup if no input file is given',
                'value': 'True'
            },
            'use_colors_for_data': {
                'comment': 'Set to True to enable cell coloring depending on its content.It could slow down data and display refreshing',
                'value': 'True'
            },
            'last_opened_file': {
                'comment': 'File name of the last opened file',
                'value': ''
            },
            'image_cache_max_time': {
                'comment': 'Delay in seconds when image cache will be invalidated. Default value represent 15 days',
                'value': str(60 * 60 * 24 * 15)
            },
            'cache_folder': {
                'comment': 'Folder (relative or absolute) to store cached data for assets (mainly preview images)',
                'value': '../../../cache'
            },
            'results_folder': {
                'comment': 'Folder (relative or absolute) to store result files to read and save data from',
                'value': '../../../results'
            },
            'scraping_folder': {
                'comment': 'Folder (relative or absolute) to store the scraped files for the assets in markeplace',
                'value': '../../../scraping'
            },
            'folders_to_scan': {
                'comment': 'List of Folders to scan for assets. Their content will be added to the list',
                'value': ''
            },
        }

        has_changed = False
        if 'UEVaultManager' not in self.config:
            self.config.add_section('UEVaultManager')
            has_changed = True

        for option, content in config_defaults.items():
            if not self.config.has_option('UEVaultManager', option):
                self.config.set('UEVaultManager', f';{content["comment"]}')
                self.config.set('UEVaultManager', option, content['value'])
                has_changed = True

        if has_changed:
            self.save_config_file(save_config_var=False)

    def read_config_properties(self) -> dict:
        """
        Read the properties from the config file.
        :return:
        """
        # ##### start of properties stored in config file
        # store all the properties that must be saved in config file
        # no need of fallback values here, they are set in the config file by default
        config_vars = {
            'rows_per_page': gui_fn.convert_to_int(self.config.get('UEVaultManager', 'rows_per_page')),
            'data_filters': self.config.get('UEVaultManager', 'data_filters'),
            'x_pos': gui_fn.convert_to_int(self.config.get('UEVaultManager', 'x_pos')),
            'y_pos': gui_fn.convert_to_int(self.config.get('UEVaultManager', 'y_pos')),
            'width': gui_fn.convert_to_int(self.config.get('UEVaultManager', 'width')),
            'height': gui_fn.convert_to_int(self.config.get('UEVaultManager', 'height')),
            'debug_mode': gui_fn.convert_to_bool(self.config.get('UEVaultManager', 'debug_mode')),
            'never_update_data_files': gui_fn.convert_to_bool(self.config.get('UEVaultManager', 'never_update_data_files')),
            'reopen_last_file': gui_fn.convert_to_bool(self.config.get('UEVaultManager', 'reopen_last_file')),
            'use_colors_for_data': gui_fn.convert_to_bool(self.config.get('UEVaultManager', 'use_colors_for_data')),
            'image_cache_max_time': gui_fn.convert_to_int(self.config.get('UEVaultManager', 'image_cache_max_time')),
            'last_opened_file': self.config.get('UEVaultManager', 'last_opened_file'),
            'cache_folder': self.config.get('UEVaultManager', 'cache_folder'),
            'results_folder': self.config.get('UEVaultManager', 'results_folder'),
            'scraping_folder': self.config.get('UEVaultManager', 'scraping_folder'),
            'folders_to_scan': self.config.get('UEVaultManager', 'folders_to_scan'),
        }
        return config_vars

    def store_config_properties(self) -> None:
        """
        store the properties in the config file.
        """
        for key, value in self.config_vars.items():
            self.config.set('UEVaultManager', key, str(value))

    def save_config_file(self, save_config_var=True) -> None:
        """
        Save the config file.
        """
        if save_config_var:
            self.store_config_properties()
            self.config.modified = True

        # do not save if in read-only mode or file hasn't changed
        if self.config.read_only or not self.config.modified:
            return

        # if config file has been modified externally, back-up the user-modified version before writing
        if os.path.exists(self.config_path):
            if (mod_time := int(os.stat(self.config_path).st_mtime)) != self.config.mod_time:
                new_filename = f'config.{mod_time}.ini'
                log_info(
                    f'Configuration file has been modified while UEVaultManager was running\nUser-modified config will be renamed to "{new_filename}"...'
                )
                os.rename(self.config_path, os.path.join(os.path.dirname(self.config_path), new_filename))

        with open(self.config_path, 'w') as cf:
            self.config.write(cf)
