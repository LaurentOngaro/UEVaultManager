# coding=utf-8
"""
Implementation for:
- GUISettings: a class that contains all the settings for the GUI.
"""
import json
import os

from termcolor import colored

# we can't import the following modules here because of circular dependencies
# UEVaultManager.tkgui.modules.functions_no_deps
import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn
from UEVaultManager import __codename__, __name__, __version__
from UEVaultManager.lfs.utils import clean_filename, path_join
from UEVaultManager.models.config import AppConf
from UEVaultManager.tkgui.modules.functions import update_loggers_level


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
    path: str = ''
    config_file_gui: str = ''  # config file path for gui part (tkgui)
    config_file: str = ''  # config file path for cli part (cli). Set by the cli part

    def __init__(self, config_file=None):
        self.config = AppConf(comment_prefixes='/', allow_no_value=True)

        self.init_gui_config_file(config_file)

        self.config_vars = self.read_config_properties()
        self._config_vars_deserialized = {}  # will store config_vars after they have been deserialized from json
        # the following folders are relative to the current file location
        # they must be used trought path_from_relative_to_absolute
        # following vars are not set as properties to avoid storing absolute paths in the config file
        self.cache_folder: str = gui_fn.path_from_relative_to_absolute(self.config_vars['cache_folder'])
        self.results_folder: str = gui_fn.path_from_relative_to_absolute(self.config_vars['results_folder'])
        self.scraping_folder: str = gui_fn.path_from_relative_to_absolute(self.config_vars['scraping_folder'])

        # Folder for assets (aka. images, icon... not "UE assets") used for the GUI. THIS IS NOT A SETTING THAT CAN BE CHANGED BY THE USER
        self.assets_folder: str = gui_fn.path_from_relative_to_absolute('../../assets')

        self.default_filename = 'assets'
        self.app_icon_filename: str = path_join(self.assets_folder, 'main.ico')
        self.default_image_filename: str = path_join(self.assets_folder, 'UEVM_200x200.png')

        if self.config_vars['reopen_last_file'] and os.path.isfile((self.config_vars['last_opened_file'])):
            self.csv_filename: str = self.config_vars['last_opened_file']
        else:
            self.csv_filename: str = path_join(self.results_folder, self.default_filename+'.csv')

        self.sqlite_filename: str = path_join(self.scraping_folder, self.default_filename+'.db')

        self.app_monitor: int = 1
        # self.csv_options = {'on_bad_lines': 'warn', 'encoding': 'utf-8', 'keep_default_na': True, 'na_values': ['None', 'nan', 'NA', 'NaN'], } # fill "empty" cells with the nan value
        self.csv_options = {'on_bad_lines': 'warn', 'encoding': 'utf-8', 'keep_default_na': False}
        # if a file extension is in this tuple, the parent folder is considered as a valid UE folder
        self.ue_valid_file_content = ('.uplugin', '.uproject')  # MUST BE LOWERCASE for comparison
        # if a folder is in this tuple, the parent folder is considered as a valid ue folder
        self.ue_valid_folder_content = ('content', '')  # must be a tuple. MUST BE LOWERCASE for comparison
        # if a folder is in this tuple, the parent folder is considered as a valid ue folder for a manifest file
        self.ue_valid_manifest_content = ('data', '')  # must be a tuple. MUST BE LOWERCASE for comparison
        # if a folder is in this tuple, the folder won't be scanned to find ue folders
        self.ue_invalid_folder_content = (
            'binaries', 'build', 'deriveddatacache', 'intermediate', 'saved', 'data'
        )  # must be a tuple. MUST BE LOWERCASE for comparison
        # if a folder is in this tuple, the folder could be a valid folder but with an incomplete structure
        self.ue_possible_folder_content = ('blueprints', 'maps', 'textures', 'materials')  # must be a tuple. MUST BE LOWERCASE for comparison

        self.assets_data_folder: str = path_join(self.scraping_folder, 'assets', 'marketplace')
        self.owned_assets_data_folder: str = path_join(self.scraping_folder, 'assets', 'owned')
        self.assets_global_folder: str = path_join(self.scraping_folder, 'global')
        self.assets_csv_files_folder: str = path_join(self.scraping_folder, 'csv')
        self.filters_folder = path_join(self.path, 'filters')
        self.csv_datetime_format: str = '%Y-%m-%d %H:%M:%S'
        self.epic_datetime_format: str = '%Y-%m-%dT%H:%M:%S.%fZ'
        self.data_filetypes = (
            ('csv file', '*.csv'), ('tcsv file', '*.tcsv'), ('json file', '*.json'), ('text file', '*.txt'), ('SQlite file', '*.db')
        )

        self.preview_max_width: int = 150
        self.preview_max_height: int = 150
        self.default_global_search: str = 'Text to search...'
        self.default_value_for_all: str = 'All'
        # self.empty_cell: str = 'None'
        self.cell_is_empty_list = ['None', 'nan', 'NA', 'NaN', 'False', '0', '0.0']
        self.empty_cell: str = ''
        self.empty_row_prefix: str = 'dummy_row_'
        self.tag_prefix = 't_'
        self.expand_columns_factor: int = 20
        self.contract_columns_factor: int = 20
        # ttkbootstrap themes:
        # light themes : "cosmo", "flatly", "litera", "minty", "lumen", "sandstone", "yeti", "pulse", "united", "morph", "journal", "simplex", "cerculean"
        # dark themes: "darkly", "superhero", "solar", "cyborg", "vapor"
        self.theme_name: str = 'lumen'
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
        self.engine_version_for_obsolete_assets: str = '4.26'  # fallback value when cli.core.engine_version_for_obsolete_assets is not available without import
        self.index_copy_col_name = 'Index copy'  # name of the column that will be used to store the index in datatables. It will be added by default to the hidden columns list

        # keep at the end
        self._app_title_long: str = ''  # use a getter to upddate the value in live
        self.app_title: str = __name__
        self.offline_mode = False

    def _get_serialized(self, var_name: str = '', is_dict=False, force_reload=False):
        """
        Getter for a serialized config vars
        :param var_name: name of the config var to get
        :param is_dict: True if the value is a dict, False if it's a list
        :param force_reload: True to force reloading the value from the config file and update the deserialized value
        :return: List or Dict
        """
        default = {} if is_dict else []
        if not force_reload and self._config_vars_deserialized.get(var_name, None) is not None:
            # it could be a dict, a list a str to decode
            read_value = self._config_vars_deserialized[var_name]
        else:
            read_value = self.config_vars[var_name]

        if read_value == '':
            return default
        if isinstance(read_value, dict) or isinstance(read_value, list):
            if len(read_value) > 0:
                return read_value
            elif not force_reload:
                # the "len(read_value) < 0" we have and "empty dict issue" after storing a bad value in self._config_vars_deserialized[var_name]
                # so we force reloading the value from the config file
                return self._get_serialized(var_name, is_dict=is_dict, force_reload=True)
        try:
            values = json.loads(read_value)
        except json.decoder.JSONDecodeError:
            log_info(f'Failed to decode json string for {var_name} in config file. Using default value')
            values = default
        self._config_vars_deserialized[var_name] = values
        return values

    def _set_serialized(self, var_name: str = '', values=None):
        """
        Setter for a serialized config vars
        :param var_name: name of the config var to get
        :param values: List or Dict to serialize
        """
        if values is None or values == {} or values == []:
            json_str = ''
        else:
            json_str = json.dumps(values, skipkeys=True, allow_nan=True)
        self._config_vars_deserialized[var_name] = json_str
        self.config_vars[var_name] = json_str

    @property
    def app_title_long(self) -> str:
        """ Getter for app_title_long """
        self._app_title_long: str = f'{__name__} Gui v{__version__} ({__codename__})'
        self._app_title_long += f' - SWITCH VALUE {self.testing_switch} ' if self.testing_switch > 0 else ''
        self._app_title_long += ' - DEBUG MODE' if self.debug_mode else ''
        self._app_title_long += ' - OFFLINE MODE' if self.offline_mode else ''
        return self._app_title_long

    @property
    def rows_per_page(self) -> int:
        """ Getter for rows_per_page """
        return gui_fn.convert_to_int(self.config_vars['rows_per_page'])

    @rows_per_page.setter
    def rows_per_page(self, value):
        """ Setter for rows_per_page """
        self.config_vars['rows_per_page'] = value

    @property
    def filters_filename(self) -> dict:
        """ Getter for filters_filename """
        return self.config_vars['filters_filename']

    @filters_filename.setter
    def filters_filename(self, value: str):
        """ Setter for filters_filename """
        self.config_vars['filters_filename'] = value

    @property
    def x_pos(self) -> int:
        """ Getter for x_pos """
        return gui_fn.convert_to_int(self.config_vars['x_pos'])

    @x_pos.setter
    def x_pos(self, value):
        """ Setter for x_pos """
        self.config_vars['x_pos'] = value

    @property
    def y_pos(self) -> int:
        """ Getter for y_pos """
        return gui_fn.convert_to_int(self.config_vars['y_pos'])

    @y_pos.setter
    def y_pos(self, value):
        """ Setter for y_pos """
        self.config_vars['y_pos'] = value

    @property
    def width(self) -> int:
        """ Getter for width """
        return gui_fn.convert_to_int(self.config_vars['width'])

    @width.setter
    def width(self, value):
        """ Setter for width """
        self.config_vars['width'] = value

    @property
    def height(self) -> int:
        """ Getter for height """
        return gui_fn.convert_to_int(self.config_vars['height'])

    @height.setter
    def height(self, value):
        """ Setter for height """
        self.config_vars['height'] = value

    @property
    def debug_mode(self) -> bool:
        """ Getter for debug_mode """
        return gui_fn.convert_to_bool(self.config_vars['debug_mode'])

    @debug_mode.setter
    def debug_mode(self, value):
        """ Setter for debug_mode """
        self.config_vars['debug_mode'] = value
        update_loggers_level(debug_value=value)

    @property
    def never_update_data_files(self) -> bool:
        """ Getter for never_update_data_files """
        return gui_fn.convert_to_bool(self.config_vars['never_update_data_files'])

    @never_update_data_files.setter
    def never_update_data_files(self, value):
        """ Setter for never_update_data_files """
        self.config_vars['never_update_data_files'] = value

    @property
    def reopen_last_file(self) -> bool:
        """ Getter for reopen_last_file """
        return gui_fn.convert_to_bool(self.config_vars['reopen_last_file'])

    @reopen_last_file.setter
    def reopen_last_file(self, value):
        """ Setter for reopen_last_file """
        self.config_vars['reopen_last_file'] = value

    @property
    def use_colors_for_data(self) -> bool:
        """ Getter for use_colors_for_data """
        return gui_fn.convert_to_bool(self.config_vars['use_colors_for_data'])

    @use_colors_for_data.setter
    def use_colors_for_data(self, value):
        """ Setter for use_colors_for_data """
        self.config_vars['use_colors_for_data'] = value

    @property
    def image_cache_max_time(self) -> int:
        """ Getter for image_cache_max_time """
        return gui_fn.convert_to_int(self.config_vars['image_cache_max_time'])

    @image_cache_max_time.setter
    def image_cache_max_time(self, value):
        """ Setter for image_cache_max_time """
        self.config_vars['image_cache_max_time'] = value

    @property
    def last_opened_file(self) -> str:
        """ Getter for last_opened_file """
        return self.config_vars['last_opened_file']

    @last_opened_file.setter
    def last_opened_file(self, value):
        """ Setter for last_opened_file """
        self.config_vars['last_opened_file'] = value

    @property
    def folders_to_scan(self) -> list:
        """ Getter for folders_to_scan """
        return self._get_serialized('folders_to_scan')

    @folders_to_scan.setter
    def folders_to_scan(self, values):
        """ Setter for folders_to_scan """
        self._set_serialized('folders_to_scan', values)

    @property
    def minimal_fuzzy_score_by_name(self) -> dict:
        """ Getter for minimal_fuzzy_score_by_name """
        return self._get_serialized('minimal_fuzzy_score_by_name')

    @minimal_fuzzy_score_by_name.setter
    def minimal_fuzzy_score_by_name(self, values: dict):
        """ Setter for minimal_fuzzy_score_by_name """
        self._set_serialized('minimal_fuzzy_score_by_name', values)

    @property
    def column_infos(self) -> dict:
        """ Getter for columns infos """
        return self._get_serialized('column_infos')

    @column_infos.setter
    def column_infos(self, values: dict):
        """ Setter for columns infos """
        self._set_serialized('column_infos', values)

    @property
    def use_threads(self) -> bool:
        """ Getter for use_threads """
        return gui_fn.convert_to_bool(self.config_vars['use_threads'])

    @use_threads.setter
    def use_threads(self, value):
        """ Setter for use_threads """
        self.config_vars['use_threads'] = value

    @property
    def hidden_column_names(self) -> list:
        """ Getter for hidden_column_names """
        return self._get_serialized('hidden_column_names')

    @hidden_column_names.setter
    def hidden_column_names(self, values):
        """ Setter for hidden_column_names """
        self._set_serialized('hidden_column_names', values)

    @property
    def testing_switch(self) -> int:
        """ Getter for testing_switch """
        return gui_fn.convert_to_int(self.config_vars['testing_switch'])

    @testing_switch.setter
    def testing_switch(self, value):
        """ Setter for testing_switch """
        self.config_vars['testing_switch'] = value

    @property
    def assets_order_col(self) -> int:
        """ Getter for assets_order_col """
        return self.config_vars['assets_order_col']

    @assets_order_col.setter
    def assets_order_col(self, value):
        """ Setter for assets_order_col """
        self.config_vars['assets_order_col'] = value

    @property
    def check_asset_folders(self) -> bool:
        """ Getter for check_asset_folders """
        return gui_fn.convert_to_bool(self.config_vars['check_asset_folders'])

    @check_asset_folders.setter
    def check_asset_folders(self, value):
        """ Setter for check_asset_folders """
        self.config_vars['check_asset_folders'] = value

    @property
    def browse_when_add_row(self) -> bool:
        """ Getter for browse_when_add_row """
        return gui_fn.convert_to_bool(self.config_vars['browse_when_add_row'])

    @browse_when_add_row.setter
    def browse_when_add_row(self, value):
        """ Setter for browse_when_add_row """
        self.config_vars['browse_when_add_row'] = value

    @property
    def last_opened_folder(self) -> str:
        """ Getter for last_opened_folder """
        return self.config_vars['last_opened_folder']

    @last_opened_folder.setter
    def last_opened_folder(self, value):
        """ Setter for last_opened_folder """
        self.config_vars['last_opened_folder'] = value

    @property
    def last_opened_project(self) -> str:
        """ Getter for last_opened_project """
        return self.config_vars['last_opened_project']

    @last_opened_project.setter
    def last_opened_project(self, value):
        """ Setter for last_opened_project """
        self.config_vars['last_opened_project'] = value

    @property
    def last_opened_engine(self) -> str:
        """ Getter for last_opened_engine """
        return self.config_vars['last_opened_engine']

    @last_opened_engine.setter
    def last_opened_engine(self, value):
        """ Setter for last_opened_engine """
        self.config_vars['last_opened_engine'] = value

    # noinspection PyPep8
    def init_gui_config_file(self, config_file: str = '') -> None:
        """
        Initialize the config file for the gui.
        :param config_file: the path to the config file to use.
        """
        if config_path := os.environ.get('XDG_CONFIG_HOME'):
            self.path = path_join(config_path, 'UEVaultManager')
        else:
            self.path = os.path.expanduser('~/.config/UEVaultManager')
        if not os.path.isdir(self.path):
            os.makedirs(self.path)
        if config_file:
            if os.path.exists(config_file):
                self.config_file_gui = os.path.abspath(config_file)
            else:
                self.config_file_gui = path_join(self.path, clean_filename(config_file))
            log_info(f'UEVMGui is using non-default config file "{self.config_file_gui}"')
        else:
            self.config_file_gui = path_join(self.path, 'config_gui.ini')

        # try loading config
        try:
            self.config.read(self.config_file_gui)
        except Exception as error:
            log_info(f'Failed to read configuration file, please ensure that file is valid!:Error: {error!r}')
            log_info('Continuing with blank config in safe-mode...')
            self.config.read_only = True
        config_defaults = {
            'rows_per_page': {
                'comment':
                'Number of Rows displayed or scraped per page.If this value is changed all the scraped files must be updated to match the new value',
                'value': 37
            },
            'filters_filename': {
                'comment': 'Name of the file to read filters from. Should ONLY contain the file name with no the path. The folder that contain the file is fixed',
                'value': ''
            },
            'x_pos': {
                'comment': 'X position of the main windows. Set to 0 to center the window. Automatically saved on quit',
                'value': 0
            },
            'y_pos': {
                'comment': 'Y position of the main windows. Set to 0 to center the window. Automatically saved on quit',
                'value': 0
            },
            'width': {
                'comment': 'Width of the main windows. Automatically saved on quit',
                'value': 1880
            },
            'height': {
                'comment': 'Height of the main windows. Automatically saved on quit',
                'value': 960
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
                'comment': 'File name of the last opened file. Automatically saved on quit',
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
            'hidden_column_names': {
                'comment':
                'List of columns names that will be hidden when applying columns width. Note that the "Index_copy" will be hidden by default',
                'value': ['Uid']
            },
            # minimal score required when looking for an url file comparing to an asset name.
            # some comparison are more fuzzy than others, so we can set a different score for each comparison
            # The key is a string that must be in the url file name or asset name
            # default value if no key is found
            'minimal_fuzzy_score_by_name': {
                'comment': 'Minimal score required when looking for an url file comparing to an asset name. MUST BE LOWERCASE',
                'value': {
                    'default': 80,
                    'brushify': 80,
                    'elite_landscapes': 90
                }
            },
            'use_threads': {
                'comment': 'Set to True to use multiple threads when scraping/grabing data for UE assets',
                'value': 'True'
            },
            'column_infos': {
                'comment': 'Infos about columns of the table. Automatically saved on quit. Leave empty for default',
                'value': ''
            },
            'testing_switch': {
                'comment':
                'DEV ONLY. NO CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Value that can be changed in live to switch some behaviours whithout quitting.',
                'value': 0
            },
            'assets_order_col': {
                'comment': 'DEV ONLY. NO CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Column used to order the assets list from the database.',
                'value': 'date_added_in_db'
            },
            'check_asset_folders': {
                'comment': 'Set to True to check and clean invalid asset folders when scraping or rebuilding data for UE assets',
                'value': 'True'
            },
            'browse_when_add_row': {
                'comment': 'Set to True to browse for a folder when adding a new row. If false, an empty row will be added',
                'value': 'True'
            },
            'last_opened_folder': {
                'comment': 'The last opened Folder name. Automatically saved when browsing a folder',
                'value': ''
            },
            'last_opened_project': {
                'comment': 'The last opened project name. Automatically saved when browsing a project folder',
                'value': ''
            },
            'last_opened_engine': {
                'comment': 'The last opened Folder name. Automatically saved when browsing an engine folder',
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
            'rows_per_page': self.config.getint('UEVaultManager', 'rows_per_page'),
            'filters_filename': self.config.get('UEVaultManager', 'filters_filename'),
            'x_pos': self.config.getint('UEVaultManager', 'x_pos'),
            'y_pos': self.config.getint('UEVaultManager', 'y_pos'),
            'width': self.config.getint('UEVaultManager', 'width'),
            'height': self.config.getint('UEVaultManager', 'height'),
            'debug_mode': self.config.getboolean('UEVaultManager', 'debug_mode'),
            'never_update_data_files': self.config.getboolean('UEVaultManager', 'never_update_data_files'),
            'reopen_last_file': self.config.getboolean('UEVaultManager', 'reopen_last_file'),
            'use_colors_for_data': self.config.getboolean('UEVaultManager', 'use_colors_for_data'),
            'image_cache_max_time': self.config.getint('UEVaultManager', 'image_cache_max_time'),
            'last_opened_file': self.config.get('UEVaultManager', 'last_opened_file'),
            'cache_folder': self.config.get('UEVaultManager', 'cache_folder'),
            'results_folder': self.config.get('UEVaultManager', 'results_folder'),
            'scraping_folder': self.config.get('UEVaultManager', 'scraping_folder'),
            'folders_to_scan': self.config.get('UEVaultManager', 'folders_to_scan'),
            'column_infos': self.config.get('UEVaultManager', 'column_infos'),
            'minimal_fuzzy_score_by_name': self.config.get('UEVaultManager', 'minimal_fuzzy_score_by_name'),
            'use_threads': self.config.getboolean('UEVaultManager', 'use_threads'),
            'hidden_column_names': self.config.get('UEVaultManager', 'hidden_column_names'),
            'testing_switch': self.config.getint('UEVaultManager', 'testing_switch'),
            'assets_order_col': self.config.get('UEVaultManager', 'assets_order_col'),
            'check_asset_folders': self.config.getboolean('UEVaultManager', 'check_asset_folders'),
            'browse_when_add_row': self.config.getboolean('UEVaultManager', 'browse_when_add_row'),
            'last_opened_folder': self.config.get('UEVaultManager', 'last_opened_folder'),
            'last_opened_project': self.config.get('UEVaultManager', 'last_opened_project'),
            'last_opened_engine': self.config.get('UEVaultManager', 'last_opened_engine'),
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
        if os.path.exists(self.config_file_gui):
            if (mod_time := int(os.stat(self.config_file_gui).st_mtime)) != self.config.mod_time:
                new_filename = f'config.{mod_time}.ini.BAK'
                log_info(
                    f'Configuration file has been modified while UEVaultManager was running\nUser-modified config will be renamed to "{new_filename}"...'
                )
                os.rename(self.config_file_gui, path_join(os.path.dirname(self.config_file_gui), new_filename))

        with open(self.config_file_gui, 'w') as cf:
            self.config.write(cf)
