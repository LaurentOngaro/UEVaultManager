# coding=utf-8
"""
Implementation for:
- GUISettings: class that contains all the settings for the GUI.
"""
import json
import os

# we can't import the following modules here because of circular dependencies
# UEVaultManager.tkgui.modules.functions_no_deps
import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn
from UEVaultManager import __codename__, __name__, __version__
from UEVaultManager.lfs.utils import clean_filename, path_join
from UEVaultManager.models.AppConfigClass import AppConfig
from UEVaultManager.tkgui.modules.types import DataSourceType
from UEVaultManager.utils.cli import check_and_create_folder


class GUISettings:
    """
    A class that contains all the settings for the GUI.
    :param config_file: path to config file to use instead of default.
    """
    path: str = ''
    config_file_gui: str = ''  # config file path for gui part (tkgui)
    config_file: str = ''  # config file path for cli part (cli). Set by the cli part
    data_filetypes_jpg = (('Jpeg image', '*.jpg'), )
    data_filetypes_png = (('PNG image', '*.png'), )
    data_filetypes_all = (('all files', '*.*'), )
    data_filetypes_text = (('text file', '*.txt'), )
    data_filetypes_html = (('html file', '*.html'), )
    data_filetypes_json = (('json file', '*.json'), )
    data_filetypes_db = (('SQlite file', '*.db'), )
    data_filetypes_csv = (('csv file', '*.csv'), ('tcsv file', '*.tcsv'))
    data_filetypes = data_filetypes_all + data_filetypes_text + data_filetypes_json + data_filetypes_db + data_filetypes_csv

    def __init__(self, config_file=None):
        self.config = AppConfig(comment_prefixes='/', allow_no_value=True)

        self.init_gui_config_file(config_file)

        self.config_vars = self.read_config_properties()
        self._config_vars_deserialized = {}  # will store config_vars after they have been deserialized from json

        # the following folders are relative to the current file location
        # they must be used trought path_from_relative_to_absolute
        # following vars are not set as properties to avoid storing absolute paths in the config file
        self.asset_images_folder: str = gui_fn.path_from_relative_to_absolute(self.config_vars['asset_images_folder'])
        self.results_folder: str = gui_fn.path_from_relative_to_absolute(self.config_vars['results_folder'])
        self.scraping_folder: str = gui_fn.path_from_relative_to_absolute(self.config_vars['scraping_folder'])

        # Folder for assets (aka. images, icon... not "UE assets") used for the GUI. THIS IS NOT A SETTING THAT CAN BE CHANGED BY THE USER
        self.assets_folder: str = gui_fn.path_from_relative_to_absolute('../../assets')
        self.assets_data_folder: str = path_join(self.scraping_folder, 'assets', 'marketplace')
        self.owned_assets_data_folder: str = path_join(self.scraping_folder, 'assets', 'owned')
        self.assets_global_folder: str = path_join(self.scraping_folder, 'global')
        self.assets_csv_files_folder: str = path_join(self.scraping_folder, 'csv')
        self.filters_folder: str = path_join(self.path, 'filters')
        self.backups_folder: str = path_join(self.scraping_folder, 'backups')
        self.backup_file_ext: str = '.BAK'
        self.default_filename: str = 'assets'
        # if a file extension is in this tuple, the parent folder is considered as a valid UE folder
        self.ue_valid_file_ext = ('.uplugin', '.uproject')  # MUST BE LOWERCASE for comparison
        # if a folder is in this tuple, the parent folder is considered as a valid ue folder
        self.ue_valid_asset_subfolder = ('content', 'Content')  # must be a tuple.
        # if a folder is in this tuple, the parent folder is considered as a valid ue folder for a manifest file
        self.ue_valid_manifest_subfolder = ('data', 'Data')  # must be a tuple.
        # subfolder to store an ASSET content for an installation or a download or a scan (same value)
        self.ue_asset_content_subfolder: str = 'Content'
        # subfolder to store a PLUGIN for a download in the vaultCache folder
        self.ue_plugin_vaultcache_subfolder: str = 'data'
        # subfolder to store a PLUGIN for a download in the vaultCache folder
        self.ue_plugin_project_subfolder: str = 'Plugins'
        # subfolder to store a PLUGIN for an installation in an ENGINE folder (relativelly to the base folder of the engine).
        # USE '/' as separator ! important for path_join
        self.ue_plugin_install_subfolder: str = 'Engine/Plugins/Marketplace'
        # file name of a UE manifest file
        self.ue_manifest_filename: str = 'manifest'
        # value in orgin column for a marketplace asset
        self.origin_marketplace = 'Marketplace'

        self.index_copy_col_name: str = 'Index copy'
        self.group_col_name: str = 'In group'  # could not be 'group' because it's a reserved word in sqlite
        # if a folder is in this tuple, the folder won't be scanned to find ue folders
        self.ue_invalid_content_subfolder = (
            'binaries', 'build', 'deriveddatacache', 'intermediate', 'saved', 'data'
        )  # must be a tuple. MUST BE LOWERCASE for comparison
        # if a folder is in this tuple, the folder could be a valid folder but with an incomplete structure
        self.ue_possible_asset_subfolder = ('blueprints', 'maps', 'textures', 'materials')  # must be a tuple. MUST BE LOWERCASE for comparison

        self.app_icon_filename: str = path_join(self.assets_folder, 'main.ico')
        self.default_image_filename: str = path_join(self.assets_folder, 'UEVM_200x200.png')

        if self.config_vars['reopen_last_file'] and os.path.isfile((self.config_vars['last_opened_file'])):
            self.csv_filename: str = self.config_vars['last_opened_file']
        else:
            self.csv_filename: str = path_join(self.results_folder, self.default_filename + '.csv')

        self.sqlite_filename: str = path_join(self.scraping_folder, self.default_filename + '.db')

        # Notes on testing_switch vamues:
        # 0: normal mode, no changes in code
        # 1: testing mode, limit the number of assets to process in several actions
        # 2: fix the value and limit the number of folders to scan for assets
        self.testing_assets_limit: int = 300  # when testing (ie testing_switch==1) , limit the number of assets to process to this value
        # self.csv_options = {'on_bad_lines': 'warn', 'encoding': 'utf-8', 'keep_default_na': True, 'na_values': ['None', 'nan', 'NA', 'NaN'], } # fill "empty" cells with the nan value
        self.csv_options = {'on_bad_lines': 'warn', 'encoding': 'utf-8', 'keep_default_na': False}
        # self.scraped_assets_per_page: int = 75  # since 2023-10-31 a value bigger than 75 will COULD be refused by UE API and return a 'common.server_error' error (http 431)
        self.scraped_assets_per_page: int = 100  # using the UC browser is slower BUT the number of assets can be bigger
        self.app_monitor: int = 1
        self.preview_max_width: int = 150
        self.preview_max_height: int = 150
        self.default_global_search: str = 'Text to search...'
        self.default_value_for_all: str = 'All'
        self.keyword_query_string = 'QUERY'  # use this keyword in a CALLABLE filter to replace the value by the in the search field
        self.cell_is_nan_list = ['NA', 'None', 'nan', 'NaN', 'NULL', 'null', 'Null']  # keep 'NA' value at first position
        self.cell_is_empty_list = self.cell_is_nan_list + ['False', '0', '0.0', '']
        self.empty_cell: str = ''
        self.empty_row_prefix: str = 'new_id_'
        self.duplicate_row_prefix: str = 'local_id_'
        self.temp_id_prefix: str = 'temp_id_'
        self.unknown_size: str = 'yes'
        self.tag_prefix: str = 't_'
        self.expand_columns_factor: int = 20
        self.contract_columns_factor: int = 20
        self.warning_limit_for_batch_op: int = 20
        self.engine_version_for_obsolete_assets: str = '4.26'  # fallback value when cli.core.engine_version_for_obsolete_assets is not available without import
        # The list off all the possible value for the field 'category'. It should be updated if necessary
        self.missing_category = 'Incomplete Asset'
        self.asset_categories = [
            '2D Assets', 'Animations', 'Architectural Visualization', 'Blueprints', 'Characters', 'Code Plugins', 'Environments', 'Epic Content',
            'Materials', 'Megascans', 'Music', 'Props', 'Sound Effects', 'Textures', 'UE Feature Samples', 'UE Game Samples', 'UE Legacy Samples',
            'UE Online Learning', 'Visual Effects', 'Weapons', 'local/Asset', 'local/Manifest', 'local/Plugin', self.missing_category
        ]
        self.notification_time = 10000  # time in ms to keep notification window on screen

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
        self.license_types = {
            # key is the license type (in the License column), value is the text to search in the asset data, see _parse_data() method in UEAssetClass.
            # for now, only ue_only is significant
            'Unknown': '',  # 'Unknown' is used when the license type is not found in the asset data
            'UE-Only': 'UE-Only Content',
        }
        folders = [
            self.assets_folder, self.assets_data_folder, self.owned_assets_data_folder, self.assets_global_folder, self.assets_csv_files_folder,
            self.filters_folder, self.backups_folder, self.asset_images_folder, self.results_folder, self.scraping_folder
        ]
        for folder in folders:
            check_and_create_folder(folder)

        # keep at the end
        self._app_title_long: str = ''  # use a getter to update the value in live
        self.app_title: str = __name__
        self._offline_mode: bool = False

    @staticmethod
    def _log(message):
        """ print a colored message."""
        # cause issue when run in a console, not in IDE
        # message = colored(message, 'orange')
        print(message)

    def _get_serialized(self, var_name: str = '', is_dict=False, force_reload=False):
        """
        Getter for a serialized config vars
        :param var_name: name of the config var to get.
        :param is_dict: True if the value is a dict, False if it's a list.
        :param force_reload: True to force reloading the value from the config file and update the deserialized value.
        :return: list or dict.
        """
        default = {} if is_dict else []
        if not force_reload and self._config_vars_deserialized.get(var_name, None) is not None:
            # it could be a dict, a list a str to decode
            read_value = self._config_vars_deserialized[var_name]
        else:
            read_value = self.config_vars[var_name]

        if not read_value:
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
            self._log(f'Failed to decode json string for {var_name} in config file. Using default value')
            values = default
        self._config_vars_deserialized[var_name] = values
        return values

    def _set_serialized(self, var_name: str = '', values=None):
        """
        Setter for a serialized config vars
        :param var_name: name of the config var to get.
        :param values: list or Dict to serialize.
        """
        if not values:
            json_str = ''
        else:
            json_str = json.dumps(values, skipkeys=True, allow_nan=True)
        self._config_vars_deserialized[var_name] = json_str
        self.config_vars[var_name] = json_str

    @property
    def app_title_long(self) -> str:
        """ Getter for app_title_long """
        self._app_title_long: str = f"{__name__} Gui v{__version__} ({__codename__})"
        self._app_title_long += f" - SWITCH VALUE {self.testing_switch} " if self.testing_switch > 0 else ''
        self._app_title_long += ' - DEBUG MODE' if self.debug_mode else ''
        self._app_title_long += ' - OFFLINE MODE' if self._offline_mode else ''
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

    @property
    def last_opened_filter(self) -> str:
        """ Getter for last_opened_filter """
        return self.config_vars['last_opened_filter']

    @last_opened_filter.setter
    def last_opened_filter(self, value):
        """ Setter for last_opened_filter """
        self.config_vars['last_opened_filter'] = value

    @property
    def timeout_for_scraping(self) -> int:
        """ Getter for timeout_for_scraping """
        return gui_fn.convert_to_int(self.config_vars['timeout_for_scraping'])

    @timeout_for_scraping.setter
    def timeout_for_scraping(self, value):
        """ Setter for timeout_for_scraping """
        self.config_vars['timeout_for_scraping'] = value

    @property
    def scraped_assets_per_page(self) -> int:
        """ Getter for scraped_assets_per_page """
        return gui_fn.convert_to_int(self.config_vars['scraped_assets_per_page'])

    @scraped_assets_per_page.setter
    def scraped_assets_per_page(self, value):
        """ Setter for scraped_assets_per_page """
        self.config_vars['scraped_assets_per_page'] = value

    @property
    def group_names(self) -> list:
        """ Getter for group_names """
        return self._get_serialized('group_names')

    @group_names.setter
    def group_names(self, values):
        """ Setter for group_names """
        self._set_serialized('group_names', values)

    @property
    def current_group_name(self) -> str:
        """ Getter for current_group_name """
        return self.config_vars['current_group_name']

    @current_group_name.setter
    def current_group_name(self, value):
        """ Setter for current_group_name """
        self.config_vars['current_group_name'] = value

    @property
    def offline_mode(self) -> bool:
        """ Getter for offline_mode """
        return self._offline_mode

    @offline_mode.setter
    def offline_mode(self, value):
        """ Setter for _offline_mode """
        self._offline_mode = value

    @property
    def backup_files_to_keep(self) -> int:
        """ Getter for backup_files_to_keep """
        return gui_fn.convert_to_int(self.config_vars['backup_files_to_keep'])

    @backup_files_to_keep.setter
    def backup_files_to_keep(self, value):
        """ Setter for backup_files_to_keep """
        self.config_vars['backup_files_to_keep'] = value

    @property
    def keep_invalid_scans(self) -> bool:
        """ Getter for keep_invalid_scans """
        return gui_fn.convert_to_bool(self.config_vars['keep_invalid_scans'])

    @keep_invalid_scans.setter
    def keep_invalid_scans(self, value):
        """ Setter for keep_invalid_scans """
        self.config_vars['keep_invalid_scans'] = value

    # #############
    # Nexts are NOT properties
    # #############
    def get_column_infos(self, source_type: DataSourceType = DataSourceType.DATABASE) -> dict:
        """
        Get columns infos depending on the datasource type
        :param source_type:  the data source type.

        Notes:
            We don't use a @property for this because we need to be able to choose the source_type
        """
        var_name = 'column_infos_sqlite' if source_type == DataSourceType.DATABASE else 'column_infos_file'
        return self._get_serialized(var_name)

    def set_column_infos(self, values: dict, source_type: DataSourceType = DataSourceType.DATABASE):
        """
        Set columns infos depending on the datasource type
        :param values: dict of columns infos.
        :param source_type: data source type.

        Notes:
            We don't use a @property for this because we need to be able to choose the source_type
        """
        var_name = 'column_infos_sqlite' if source_type == DataSourceType.DATABASE else 'column_infos_file'
        self._set_serialized(var_name, values)

    # noinspection PyPep8
    def init_gui_config_file(self, config_file: str = '') -> None:
        """
        Initialize the config file for the gui.
        :param config_file: path to the config file to use.
        """
        if config_path := os.environ.get('XDG_CONFIG_HOME'):
            self.path = path_join(config_path, 'UEVaultManager')
        else:
            self.path = os.path.expanduser('~/.config/UEVaultManager')
        self.path = os.path.normpath(self.path)
        if not os.path.isdir(self.path):
            os.makedirs(self.path)
        if config_file:
            if os.path.exists(config_file):
                self.config_file_gui = os.path.abspath(config_file)
            else:
                self.config_file_gui = path_join(self.path, clean_filename(config_file))
            self._log(f'UEVMGui is using non-default config file "{self.config_file_gui}"')
        else:
            self.config_file_gui = path_join(self.path, 'config_gui.ini')

        # try loading config
        try:
            self.config.read(self.config_file_gui)
        except Exception as error:
            self._log(f'Failed to read configuration file, please ensure that file is valid!:Error: {error!r}')
            self._log('Continuing with blank config in safe-mode...')
            self.config.read_only = True
        config_defaults = {
            'folders_to_scan': {
                'comment': 'List of Folders to scan for assets. Their content will be added to the list',
                'value': ''
            },
            'debug_mode': {
                'comment': 'Set to True to print debug information (GUI related only)',
                'value': 'False'
            },
            'use_threads': {
                'comment': 'Set to True to use multiple threads when scraping/grabbing data for UE assets',
                'value': 'True'
            },
            'timeout_for_scraping': {
                'comment':
                'timeout in second when scraping several assets in once. This value should not be too low to limit timeout issues and scraping cancellation.',
                'value': 30
            },
            'scraped_assets_per_page': {
                'comment': 'Number of grouped assets to scrap with one url. Since 2023-10-31 a value bigger than 75 COULD be refused by UE API',
                'value': 75
            },
            'keep_invalid_scans': {
                'comment': 'Set to True to keep folders that contain a "non marketplace friendly" asset during a folders scan.',
                'value': 'True'
            },
            'reopen_last_file': {
                'comment': 'Set to True to re-open the last file at startup if no input file is given',
                'value': 'True'
            },
            'never_update_data_files': {
                'comment': 'Set to True to speed the update process by not updating the metadata files. FOR TESTING ONLY',
                'value': 'False'
            },
            'use_colors_for_data': {
                'comment': 'Set to True to enable cell coloring depending on its content.It could slow down data and display refreshing',
                'value': 'True'
            },
            'check_asset_folders': {
                'comment': 'Set to True to check and clean invalid asset folders when scraping or rebuilding data for UE assets',
                'value': 'True'
            },
            'browse_when_add_row': {
                'comment': 'Set to True to browse for a folder when adding a new row. If false, an empty row will be added',
                'value': 'True'
            },
            'rows_per_page': {
                'comment':
                'Number of Rows displayed or scraped per page.If this value is changed all the scraped files must be updated to match the new value',
                'value': 37
            },
            'backup_files_to_keep': {
                'comment':
                'Number of backup files version to keep in the folder for backups. The oldest will be deleted. Set to 0 to keep all the backups',
                'value': 30
            },
            'image_cache_max_time': {
                'comment': 'Delay in seconds when image cache will be invalidated. Default value represent 15 days',
                'value': str(60 * 60 * 24 * 15)
            },
            'asset_images_folder': {
                'comment': 'Folder (relative or absolute) to store cached data for assets (mainly preview images)',
                'value': '../../../cache'
            },
            'scraping_folder': {
                'comment': 'Folder (relative or absolute) to store the scraped files for the assets in markeplace',
                'value': '../../../scraping'
            },
            'results_folder': {
                'comment': 'Folder (relative or absolute) to store result files to read and save data from',
                'value': '../../../results'
            },
            # minimal score required when looking for a url file comparing to an asset name.
            # some comparison are more fuzzy than others, so we can set a different score for each comparison
            # The key is a string that must be in the url file name or asset name
            # default value if no key is found
            'minimal_fuzzy_score_by_name': {
                'comment': 'Minimal score required when looking for a url file comparing to an asset name. MUST BE LOWERCASE',
                'value': {
                    'default': 80,
                    'brushify': 80,
                    'elite_landscapes': 90
                }
            },
            'group_names': {
                'comment': 'The name of the groups where the selected rows can be added to.',
                'value': list(['G1', 'G2', 'G3'])
            },
            'current_group_name': {
                'comment': 'The name of the current group where the selected rows can be added to.',
                'value': 'G1'
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
            'last_opened_file': {
                'comment': 'File name of the last opened file. Automatically saved on quit',
                'value': ''
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
            'last_opened_filter': {
                'comment':
                'The last opened filter file name.Automatically saved when loading a filter.Leave empty to load no filter at start.Contains the file name only, not the path',
                'value': ''
            },
            'hidden_column_names': {
                'comment':
                'List of columns names that will be hidden when applying columns width. Note that the "Index_copy" will be hidden by default',
                'value': list(['Uid', 'Release info'])
            },
            'column_infos_sqlite': {
                'comment': 'Infos about columns width and pos in DATABASE mode. Automatically saved on quit. Leave empty for default',
                'value': ''
            },
            'column_infos_file': {
                'comment': 'Infos about columns width and pos in FILE mode. Automatically saved on quit. Leave empty for default',
                'value': ''
            },
            'assets_order_col': {
                'comment':
                'DEV ONLY. NO CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Column name to sort the assets from the database followed by ASC or DESC (Optional).',
                'value': 'date_added DESC'
            },
            'testing_switch': {
                'comment':
                'DEV ONLY. NO CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Value that can be changed in live to switch some behaviours whithout quitting.',
                'value': 0
            },
        }

        has_changed = False
        if 'UEVaultManager' not in self.config:
            self.config.add_section('UEVaultManager')
            has_changed = True

        for option, content in config_defaults.items():
            if not self.config.has_option('UEVaultManager', option):
                self.config.set('UEVaultManager', f';{content["comment"]}')
                value = content['value']
                if isinstance(value, list) or isinstance(value, dict):
                    try:
                        value = json.dumps(value)
                    except TypeError:
                        self._log(f'Failed to encode default value in a json string for {option}.Using an empty value')
                        value = ''
                self.config.set('UEVaultManager', option, value)
                has_changed = True

        if has_changed:
            self.save_config_file(save_config_var=False)

    def read_config_properties(self, update_from_config_file: bool = False) -> dict:
        """
        Read the properties from the config file.
        :param update_from_config_file: True to update the config_vars from the config file.
        :return: dict of config vars.
        """
        if update_from_config_file:
            self.init_gui_config_file(self.config_file_gui)
        # ##### start of properties stored in config file
        # store all the properties that must be saved in config file
        # no need of fallback values here, they are set in the config file by default
        config_vars = {
            'folders_to_scan': self.config.get('UEVaultManager', 'folders_to_scan'),
            'debug_mode': self.config.getboolean('UEVaultManager', 'debug_mode'),
            'use_threads': self.config.getboolean('UEVaultManager', 'use_threads'),
            'timeout_for_scraping': self.config.getint('UEVaultManager', 'timeout_for_scraping'),
            'scraped_assets_per_page': self.config.get('UEVaultManager', 'scraped_assets_per_page'),
            'keep_invalid_scans': self.config.getboolean('UEVaultManager', 'keep_invalid_scans'),
            'reopen_last_file': self.config.getboolean('UEVaultManager', 'reopen_last_file'),
            'never_update_data_files': self.config.getboolean('UEVaultManager', 'never_update_data_files'),
            'use_colors_for_data': self.config.getboolean('UEVaultManager', 'use_colors_for_data'),
            'check_asset_folders': self.config.getboolean('UEVaultManager', 'check_asset_folders'),
            'browse_when_add_row': self.config.getboolean('UEVaultManager', 'browse_when_add_row'),
            'rows_per_page': self.config.getint('UEVaultManager', 'rows_per_page'),
            'backup_files_to_keep': self.config.getint('UEVaultManager', 'backup_files_to_keep'),
            'image_cache_max_time': self.config.getint('UEVaultManager', 'image_cache_max_time'),
            'asset_images_folder': self.config.get('UEVaultManager', 'asset_images_folder'),
            'scraping_folder': self.config.get('UEVaultManager', 'scraping_folder'),
            'results_folder': self.config.get('UEVaultManager', 'results_folder'),
            'minimal_fuzzy_score_by_name': self.config.get('UEVaultManager', 'minimal_fuzzy_score_by_name'),
            'group_names': self.config.get('UEVaultManager', 'group_names'),
            'current_group_name': self.config.get('UEVaultManager', 'current_group_name'),
            'x_pos': self.config.getint('UEVaultManager', 'x_pos'),
            'y_pos': self.config.getint('UEVaultManager', 'y_pos'),
            'width': self.config.getint('UEVaultManager', 'width'),
            'height': self.config.getint('UEVaultManager', 'height'),
            'last_opened_file': self.config.get('UEVaultManager', 'last_opened_file'),
            'last_opened_folder': self.config.get('UEVaultManager', 'last_opened_folder'),
            'last_opened_project': self.config.get('UEVaultManager', 'last_opened_project'),
            'last_opened_engine': self.config.get('UEVaultManager', 'last_opened_engine'),
            'last_opened_filter': self.config.get('UEVaultManager', 'last_opened_filter'),
            'hidden_column_names': self.config.get('UEVaultManager', 'hidden_column_names'),
            'column_infos_sqlite': self.config.get('UEVaultManager', 'column_infos_sqlite'),
            'column_infos_file': self.config.get('UEVaultManager', 'column_infos_file'),
            'assets_order_col': self.config.get('UEVaultManager', 'assets_order_col'),
            'testing_switch': self.config.getint('UEVaultManager', 'testing_switch'),
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
                new_filename = f'config.EXISTING_{mod_time}.ini{self.backup_file_ext}'
                new_filename = path_join(self.backups_folder, new_filename)
                os.rename(self.config_file_gui, new_filename)
                self._log(
                    f'Configuration file has been modified while UEVaultManager was running\nUser-modified config has been be renamed to "{new_filename}"'
                )

        with open(self.config_file_gui, 'w', encoding='utf-8') as file:
            self.config.write(file)
