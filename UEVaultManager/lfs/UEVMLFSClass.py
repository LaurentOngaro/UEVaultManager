# coding: utf-8
"""
Implementation for:
- UEVMLFS: Local File System.
"""
import filecmp
import json
import logging
import os
from datetime import datetime
from time import time
from typing import Optional

import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.lfs.utils import clean_filename, generate_label_from_path
from UEVaultManager.lfs.utils import path_join
from UEVaultManager.models.AppConfigClass import AppConfig
from UEVaultManager.models.Asset import InstalledAsset
from UEVaultManager.models.types import DateFormat
from UEVaultManager.models.UEAssetDbHandlerClass import UEAssetDbHandler
from UEVaultManager.tkgui.modules.cls.FilterValueClass import FilterValue, FilterValueEncoder
from UEVaultManager.tkgui.modules.functions import create_file_backup
from UEVaultManager.tkgui.modules.functions_no_deps import check_and_convert_list_to_str, create_uid, merge_lists_or_strings
from UEVaultManager.utils.cli import check_and_create_file
from UEVaultManager.utils.env import is_windows_mac_or_pyi


class UEVMLFS:
    """
    Class to handle all local filesystem related tasks.
    :param config_file: path to config file to use instead of default.
    """

    def __init__(self, config_file=None):
        self.logger = logging.getLogger('UEVMLFS')

        if config_path := os.environ.get('XDG_CONFIG_HOME'):
            self.path = path_join(config_path, 'UEVaultManager')
        else:
            self.path = os.path.expanduser('~/.config/UEVaultManager')
        # EGS user info
        self._user_data = None
        # UEVaultManager update check info
        self._update_info = None
        # the sizes of dowloaded assets
        self._asset_sizes = None
        # the catalog item ids of all the (owned) items (assets and games) of the user library
        self._library_catalog_ids = None

        # Config with item specific settings (e.g. start parameters, env variables)
        self.config = AppConfig(comment_prefixes='/', allow_no_value=True)

        if config_file:
            # if user specified a valid relative/absolute path use that,
            # otherwise create file in UEVaultManager config directory
            if os.path.exists(config_file):
                self.config_file = os.path.abspath(config_file)
            else:
                self.config_file = path_join(self.path, clean_filename(config_file))
            self.logger.info(f'UEVMLFS is using non-default config file "{self.config_file}"')
        else:
            self.config_file = path_join(self.path, 'config.ini')

        # Folders used by the application
        self.json_files_folder: str = path_join(self.path, 'json')  # folder for json files other than metadata, extra and manifests
        self.manifests_folder: str = path_join(self.json_files_folder, 'manifests')
        self.tmp_folder: str = path_join(self.path, 'tmp')

        # filename for storing the user data (filled by the 'auth' command).
        self.user_data_filename: str = path_join(self.json_files_folder, 'user_data.json')
        # filename for storing data about the current version of the application
        self.online_version_filename: str = path_join(self.json_files_folder, 'online_version.json')
        # filename for the installed assets list
        self.installed_asset_filename: str = path_join(self.json_files_folder, 'installed_assets.json')
        # filename for storing the size of asset (filled by the 'info' command).
        self.asset_sizes_filename: str = path_join(self.json_files_folder, 'asset_sizes.json')
        # filename for storing the catalog item ids of all the (owned) items (assets and games) of the user library
        self.library_catalog_ids_filename: str = path_join(self.json_files_folder, 'library_catalog_ids.json')

        # ensure folders exist.
        for f in ['', self.manifests_folder, self.tmp_folder, self.json_files_folder]:
            if not os.path.exists(path_join(self.path, f)):
                os.makedirs(path_join(self.path, f))

        # backup important files (before creation to avoid backup of empty files)
        create_file_backup(self.asset_sizes_filename)
        create_file_backup(self.installed_asset_filename)

        # check and create some empty files (to avoid file not found errors in debug)
        check_and_create_file(self.asset_sizes_filename, content='{}')
        check_and_create_file(self.installed_asset_filename, content='{}')

        try:
            self.config.read(self.config_file)
        except Exception as error:
            self.logger.error(f'Failed to read configuration file, please ensure that file is valid!:Error: {error!r}')
            self.logger.warning('Continuing with blank config in safe-mode...')
            self.config.read_only = True

        # make sure "UEVaultManager" section exists
        has_changed = False
        if 'UEVaultManager' not in self.config:
            self.config.add_section('UEVaultManager')
            has_changed = True

        # Add opt-out options with explainers
        if not self.config.has_option('UEVaultManager', 'max_memory'):
            self.config.set('UEVaultManager', '; Set preferred CDN host (e.g. to improve download speed)')
            self.config.set('UEVaultManager', 'max_memory', '2048')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'max_workers'):
            self.config.set(
                'UEVaultManager', '; maximum number of worker processes when downloading (fewer will be slower, use less system resources)'
            )
            self.config.set('UEVaultManager', 'max_workers', '8')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'locale'):
            self.config.set('UEVaultManager', '; locale override, must be in RFC 1766 format (e.g. "en-US")')
            self.config.set('UEVaultManager', 'locale', 'en-US')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'egl_programdata'):
            self.config.set('UEVaultManager', '; path to the "Manifests" folder in the EGL ProgramData directory for non Windows platforms')
            self.config.set('UEVaultManager', 'egl_programdata', 'THIS_MUST_BE_SET_ON_NON_WINDOWS_PLATFORMS')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'preferred_cdn'):
            self.config.set('UEVaultManager', '; maximum shared memory (in MiB) to use for installation')
            self.config.set('UEVaultManager', 'preferred_cdn', 'epicgames-download1.akamaized.net')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'disable_https'):
            self.config.set('UEVaultManager', '; disable HTTPS for downloads (e.g. to use a LanCache)')
            self.config.set('UEVaultManager', 'disable_https', 'false')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'disable_update_check'):
            self.config.set('UEVaultManager', ';Set to True to disable the automatic update check')
            self.config.set('UEVaultManager', 'disable_update_check', 'False')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'disable_update_notice'):
            self.config.set('UEVaultManager', '; Set to True to disable the notice about an available update on exit')
            self.config.set('UEVaultManager', 'disable_update_notice', 'False' if is_windows_mac_or_pyi() else 'True')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'start_in_edit_mode'):
            self.config.set('UEVaultManager', ';Set to True to start the application in Edit mode (since v1.4.4) with the GUI')
            self.config.set('UEVaultManager', 'start_in_edit_mode', 'False')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'create_output_backup'):
            self.config.set(
                'UEVaultManager',
                '; Create a backup of the output file (when using the --output option) suffixed by a timestamp before creating a new file'
            )
            self.config.set('UEVaultManager', 'create_output_backup', 'True')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'create_log_backup'):
            self.config.set(
                'UEVaultManager', '; Set to True to create a backup of the log files that store asset analysis. It is suffixed by a timestamp'
            )
            self.config.set('UEVaultManager', 'create_log_backup', 'True')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'verbose_mode'):
            self.config.set('UEVaultManager', '; Set to True to print more information during long operations')
            self.config.set('UEVaultManager', 'verbose_mode', 'False')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'scrap_assets_filename_log'):
            self.config.set(
                'UEVaultManager', '; File name (and path) to log issues with assets when running the list or scrap commands' + "\n" +
                '; use "~/" at the start of the filename to store it relatively to the user directory'
            )
            self.config.set('UEVaultManager', 'ignored_assets_filename_log', '~/.config/ignored_assets.log')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'notfound_assets_filename_log'):
            self.config.set('UEVaultManager', 'notfound_assets_filename_log', '~/.config/notfound_assets.log')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'scan_assets_filename_log'):
            self.config.set('UEVaultManager', 'scan_assets_filename_log', '~/.config/scan_assets.log')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'scrap_assets_filename_log'):
            self.config.set('UEVaultManager', 'scan_assets_filename_log', '~/.config/scrap_assets.log')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'engine_version_for_obsolete_assets'):
            self.config.set('UEVaultManager', '; Minimal unreal engine version to check for obsolete assets (default is 4.26)')
            self.config.set(
                'UEVaultManager', 'engine_version_for_obsolete_assets', '4.26'
            )  # no access to the engine_version_for_obsolete_assets global settings here without importing its module
            has_changed = True

        if has_changed:
            self.save_config()

        # load existing installed assets
        self._installed_assets = {}
        self.load_installed_assets()

        # TOOBIG
        # load existing assets metadata
        # data_folder = gui_g.s.assets_data_folder
        # for gm_file in os.listdir(path_join(data_folder)):
        #     try:
        #         with open(path_join(data_folder, gm_file), 'r', encoding='utf-8') as file:
        #             json_data = json.load(file)
        #             app_name = self.get_app_name_from_asset_data(json_data)
        #             self.assets_data[app_name] = json_data
        #     except Exception as error:
        #         self.logger.debug(f'Loading asset data file "{gm_file}" failed: {error!r}')

        # load asset sizes
        try:
            with open(self.asset_sizes_filename, 'r', encoding='utf-8') as file:
                self._asset_sizes = json.load(file)
        except Exception as error:
            self.logger.debug(f'Loading assets sizes failed: {error!r}')
            self._asset_sizes = None

        # if not gui_g.s.offline_mode:
        #     self.invalidate_library_catalog_ids()

    @property
    def userdata(self):
        """
        Return the user data as a dict.
        :return: user data.
        """
        if self._user_data is not None:
            return self._user_data
        try:
            with open(self.user_data_filename, 'r', encoding='utf-8') as file:
                self._user_data = json.load(file)
        except Exception as error:
            self.logger.debug(f'Failed to load user data: {error!r}')
            return None
        return self._user_data

    @userdata.setter
    def userdata(self, userdata: dict) -> None:
        """
        Set the user data.
        :param userdata: user data.
        """
        if userdata is None:
            raise ValueError('Userdata is none!')

        self._user_data = userdata
        with open(self.user_data_filename, 'w', encoding='utf-8') as file:
            json.dump(userdata, file, indent=2, sort_keys=True)

    def invalidate_userdata(self) -> None:
        """
        Invalidate the user data.
        """
        self._user_data = None
        if os.path.exists(self.user_data_filename):
            os.remove(self.user_data_filename)

    def invalidate_library_catalog_ids(self) -> None:
        """
        Invalidate the library catalog ids data.
        """
        self._library_catalog_ids = None
        if os.path.exists(self.library_catalog_ids_filename):
            os.remove(self.library_catalog_ids_filename)

    @property
    def asset_sizes(self):
        """
        Return the asset's sizes as a dict. If not loaded, load it from the json file.
        :return: asset's size.
        """
        if self._asset_sizes is None:
            try:
                with open(self.asset_sizes_filename, 'r', encoding='utf-8') as file:
                    self._asset_sizes = json.load(file)
            except Exception as error:
                self.logger.debug(f"Failed to load asset's size: {error!r}")
        return self._asset_sizes

    @asset_sizes.setter
    def asset_sizes(self, asset_sizes) -> None:
        """
        Set the asset data and saved it to a json file.
        :param asset_sizes: asset sizes.
        """
        self._asset_sizes = asset_sizes
        with open(self.asset_sizes_filename, 'w', encoding='utf-8') as file:
            json.dump(self._asset_sizes, file, indent=2, sort_keys=True)

    @property
    def library_catalog_ids(self):
        """
        Return the catalog item ids of all the (owned) items (assets and games) of the user library. If not loaded, load it from the json file.
        :return: asset's size.
        """
        if self._library_catalog_ids is None:
            try:
                with open(self.library_catalog_ids_filename, 'r', encoding='utf-8') as file:
                    self._library_catalog_ids = json.load(file)
            except Exception as error:
                self.logger.debug(f"Failed to load item ids of the user library: {error!r}")
        return self._library_catalog_ids

    @library_catalog_ids.setter
    def library_catalog_ids(self, catalog_ids) -> None:
        """
        Set the asset data and saved it to a json file.
        :param catalog_ids: catalog item ids of all the (owned) items (assets and games) of the user library.
        """
        self._library_catalog_ids = catalog_ids
        with open(self.library_catalog_ids_filename, 'w', encoding='utf-8') as file:
            json.dump(self._library_catalog_ids, file, indent=2, sort_keys=True)

    def _get_manifest_filename(self, app_name: str, version: str, platform: str = None) -> str:
        """
        Get the manifest filename.
        :param app_name: asset name.
        :param version: version of the manifest.
        :param platform: platform of the manifest.
        :return: manifest filename.
        """
        if platform:
            fname = clean_filename(f'{app_name}_{platform}_{version}')
        else:
            fname = clean_filename(f'{app_name}_{version}')
        return path_join(self.manifests_folder, f'{fname}.manifest')

    @staticmethod
    def load_filter(filename: str = '') -> Optional[FilterValue]:
        """
        Load the filters from a json file
        :return: a FilterValue object or None on error.
        """
        filename = filename or gui_g.s.last_opened_filter
        folder = gui_g.s.filters_folder
        full_filename = path_join(folder, filename)
        if not os.path.isfile(full_filename):
            return None
        try:
            with open(full_filename, 'r', encoding='utf-8') as file:
                filter_data = json.load(file)
            filter_value = FilterValue.init(filter_data)
        except (Exception, ) as error:
            print(f'Error while loading filter file "{filename}": {error!r}')
            return None
        return filter_value

    @staticmethod
    def save_filter(filter_value: FilterValue, filename: str = '') -> None:
        """
        Save a filter to a json file.
        :param filter_value: filter to save.
        :param filename: filename to use. If empty, use the last opened filter.
        """
        if not filter_value:
            return
        filename = filename or gui_g.s.last_opened_filter
        folder = gui_g.s.filters_folder
        full_filename = path_join(folder, filename)
        if not full_filename:
            return
        with open(full_filename, 'w', encoding='utf-8') as file:
            json.dump(filter_value, file, indent=2, cls=FilterValueEncoder)

    @staticmethod
    def get_app_name_from_asset_data(asset_data: dict, use_sql_fields: bool = False) -> (str, bool):
        """
        Return the app_name to use to get the asset data.
        :param asset_data: asset data.
        :param use_sql_fields: whether to use the sql fields name instead of json field name. Adapt the value with the type of asset_data.
        :return: (app_name (ie asset_id), and a True if the app_id has been found).
        """
        # check if the app_name has been already added into the file during the _parse_data() method
        app_id = asset_data.get('app_name', '')
        if app_id:
            return app_id, True
        app_id_field = 'appId'  # does not change between JSON and SQL data because is inside another json field
        if use_sql_fields:
            # field names are AFTER parsing (ie in an ue_asset object)
            release_info_field = 'release_info'
            asset_slug_field = 'asset_slug'
            catalog_item_id_field = 'catalog_item_id'
        else:
            # raw field names are BEFORE parsing (ie in json data)
            release_info_field = 'releaseInfo'
            asset_slug_field = 'urlSlug'
            catalog_item_id_field = 'catalogItemId'
        found = True
        try:
            release_info = asset_data[release_info_field]
            if type(release_info) is str:
                release_info = json.loads(release_info)
            app_id = release_info[-1][app_id_field]  # appid from the latest release
        except (Exception, ):
            # we keep UrlSlug here because it can arise from the scraped data
            app_id = asset_data.get(asset_slug_field, None)
            if app_id is None:
                app_id = asset_data.get(catalog_item_id_field, create_uid())
                found = False
        return app_id, found

    @staticmethod
    def get_filename_from_asset_data(asset_data: dict, use_sql_fields: bool = False) -> (str, str):
        """
        Return the filename and the app_name to use to save the asset data.
        :param asset_data: asset data.
        :param use_sql_fields: whether to use the sql fields name instead of json field name. Adapt the value with the type of asset_data.
        :return: (the filename, the app_id).
        """
        app_name, found = UEVMLFS.get_app_name_from_asset_data(asset_data, use_sql_fields=use_sql_fields)
        return f'{app_name}.json' if found else f'_no_appId_{app_name}.json', app_name

    @staticmethod
    def json_data_mapping(data_from_egs_format: dict) -> dict:
        """
        Convert json data from EGS format (NEW) to UEVM format (OLD, i.e. legendary).
        :param data_from_egs_format: json data from EGS format (NEW).
        :return: json data in UEVM format (OLD).

        Notes:
            Mainly used when manipulating assets in the "old" format (I.E. when using ClI methods), like install_asset(), info() and list_files()
        """
        app_name = data_from_egs_format['appName']
        category = data_from_egs_format['categories'][0]['path']

        if category == 'assets/codeplugins':
            category = 'plugins/engine'
        category_1 = category.split('/')[0]
        categorie = [{'path': category}, {'path': category_1}]
        data_to_uevm_format = {
            'app_name': app_name,
            'app_title': data_from_egs_format['title'],
            'asset_infos': {
                'Windows': {
                    'app_name': app_name,
                    # 'asset_id': data_from_egs_format['id'], # no common value between EGS and UEVM
                    # 'build_version': app_name,  # no common value between EGS and UEVM
                    'catalog_item_id': data_from_egs_format['catalogItemId'],
                    # 'label_name': 'Live-Windows',
                    'metadata': {},
                    'namespace': data_from_egs_format['namespace']
                }
            },
            'base_urls': [],
            'metadata': {
                'categories': categorie,
                # 'creationDate': data_from_egs_format['effectiveDate'], # use first release instead
                'description': data_from_egs_format['description'],
                'developer': data_from_egs_format['seller']['name'],
                'developerId': data_from_egs_format['seller']['id'],
                # 'endOfSupport': False,
                'entitlementName': data_from_egs_format['catalogItemId'],
                # 'entitlementType' : 'EXECUTABLE',
                # 'eulaIds': [],
                'id': data_from_egs_format['catalogItemId'],
                # 'itemType': 'DURABLE',
                'keyImages': data_from_egs_format['keyImages'],
                # 'lastModifiedDate': data_from_egs_format['effectiveDate'], # use last release instead
                'longDescription': data_from_egs_format['longDescription'],
                'namespace': data_from_egs_format['namespace'],
                'releaseInfo': data_from_egs_format['releaseInfo'],
                'status': data_from_egs_format['status'],
                'technicalDetails': data_from_egs_format['technicalDetails'],
                'title': data_from_egs_format['title'],
                # 'unsearchable': False
            }
        }
        return data_to_uevm_format

    def get_asset(self, app_name: str, owned_assets_only=False) -> (dict, str):
        """
        Load JSON data from a file.
        :param app_name: name of the asset to load the data from.
        :param owned_assets_only: whether only the owned assets are scraped.
        :return: dictionary containing the loaded data.

        Notes:
            Mainly used when manipulating assets in the "old" format (I.E. when using ClI methods), like install_asset(), info() and list_files()
        """
        folder = gui_g.s.owned_assets_data_folder if owned_assets_only else gui_g.s.assets_data_folder
        filename = app_name + '.json'
        json_data_uevm = {}
        message = ''
        full_filename = path_join(folder, filename)
        if not os.path.isfile(full_filename):
            message = f'The json file "{filename}" to get data from does not exist.\nTry to scrap the asset first.'
        else:
            with open(full_filename, 'r', encoding='utf-8') as file:
                try:
                    json_data = json.load(file)
                except json.decoder.JSONDecodeError as error:
                    message = f'The following error occured when loading data from {filename}:{error!r}'
                # we need to add the appName  (i.e. assetId) to the data because it can't be found INSIDE the json data
                # it needed by the json_data_mapping() method
                json_data['appName'] = app_name
                json_data_uevm = self.json_data_mapping(json_data)
        return json_data_uevm, message

    def delete_folder_content(self, folders=None, extensions_to_delete: list = None, file_name_to_keep: list = None) -> int:
        """
        Delete all the files in a folder that are not in the list_of_items_to_keep list.
        :param folders: list of folder to clean. Could be a list or a string for a single folder.If None, the function will return 0.
        :param extensions_to_delete: list of extensions to delete. Leave to Empty to delete all extentions.
        :param file_name_to_keep: list of items to keep. Leave to Empty to delete all files.
        :return: total size of deleted files.
        """
        if not folders:
            return 0
        if isinstance(folders, str):
            folders_to_clean = [folders]
        else:
            folders_to_clean = folders

        if len(folders_to_clean) < 1:
            return 0
        if file_name_to_keep is None:
            file_name_to_keep = []
        size_deleted = 0
        while folders_to_clean:
            folder = folders_to_clean.pop()
            if folder == self.path and extensions_to_delete is None:
                self.logger.warning("We can't delete the config folder without extensions to filter files!")
                continue
            if not os.path.isdir(folder):
                continue
            for f in os.listdir(folder):
                file_name = path_join(folder, f)
                # file_name = os.path.abspath(file_name)
                app_name, file_ext = os.path.splitext(f)
                file_ext = file_ext.lower()
                # make extensions_to_delete lower
                if extensions_to_delete is not None:
                    extensions_to_delete = [ext.lower() for ext in extensions_to_delete]
                file_is_ok = (file_name_to_keep is None or app_name not in file_name_to_keep)
                ext_is_ok = (extensions_to_delete is None or file_ext in extensions_to_delete)
                if file_is_ok and ext_is_ok:
                    try:
                        size = os.path.getsize(file_name)
                        os.remove(file_name)
                        size_deleted += size
                    except Exception as error:
                        self.logger.warning(f'Failed to delete file "{file_name}": {error!r}')
                elif os.path.isdir(file_name):
                    folders_to_clean.append(file_name)
        return size_deleted

    def load_manifest(self, app_name: str, version: str, platform: str = 'Windows') -> any:
        """
        Load the manifest data from a file.
        :param app_name: name of the item.
        :param version: version of the manifest.
        :param platform: platform of the manifest.
        :return: manifest data.
        """
        try:
            return open(self._get_manifest_filename(app_name, version, platform), 'rb').read()
        except FileNotFoundError:  # all other errors should propagate
            self.logger.debug(f'Loading manifest failed, retrying without platform in filename...')
            try:
                return open(self._get_manifest_filename(app_name, version), 'rb').read()
            except FileNotFoundError:  # all other errors should propagate
                return None

    def save_manifest(self, app_name: str, manifest_data, version: str, platform: str = 'Windows') -> str:
        """
        Save the manifest data to a file.
        :param app_name: name of the item.
        :param manifest_data: manifest data.
        :param version: version of the manifest.
        :param platform: platform of the manifest.
        :return: manifest filename.
        """
        filename = self._get_manifest_filename(app_name, version, platform)
        with open(filename, 'wb') as file:
            file.write(manifest_data)
        return filename

    def clean_tmp_data(self) -> int:
        """
        Delete all the files in the tmp folder.
        :return: size of the deleted files.
        """
        return self.delete_folder_content(self.tmp_folder)

    def clean_cache_data(self) -> int:
        """
        Delete all the files in the cache folders.
        :return: size of the deleted files.
        """
        return self.delete_folder_content(gui_g.s.asset_images_folder)

    def clean_manifests(self) -> int:
        """
        Delete all the metadata files that are not in the names_to_keep list.
        """
        return self.delete_folder_content(self.manifests_folder)

    def clean_logs_and_backups(self) -> int:
        """
        Delete all the log and backup files in the application folders.
        :return: size of the deleted files.
        """
        folders = [self.path, gui_g.s.results_folder, gui_g.s.scraping_folder, gui_g.s.backups_folder]
        return self.delete_folder_content(folders, ['.log', gui_g.s.backup_file_ext])

    def load_installed_assets(self) -> bool:
        """
        Get the installed asset data.
        :return: True if the asset data is loaded.
        """
        try:
            with open(self.installed_asset_filename, 'r', encoding='utf-8') as file:
                self._installed_assets = json.load(file)
        except Exception as error:
            self.logger.debug(f'Failed to load installed asset data: {error!r}')
            return False
        has_changed = False
        for asset in self._installed_assets.values():
            installed_folders = asset.get('installed_folders', None)
            if installed_folders is None:
                asset['installed_folders'] = []
            else:
                # remove all empty string in installed_folders
                asset['installed_folders'] = [folder for folder in asset['installed_folders'] if str(folder).strip()]
            has_changed = has_changed or installed_folders != asset['installed_folders']

        if has_changed:
            self.save_installed_assets()

    def save_installed_assets(self) -> None:
        """
        Save the installed asset data.
        """
        installed_assets = self._installed_assets
        with open(self.installed_asset_filename, 'w', encoding='utf-8') as file:
            json.dump(installed_assets, file, indent=2, sort_keys=True)

    def get_installed_asset(self, app_name: str) -> Optional[InstalledAsset]:
        """
        Get the installed asset data. If it's not currently loaded, it will be read from the json file
        :param app_name: asset name.
        :return: installed asset or None if not found.
        """
        if not app_name:
            return None

        if not self._installed_assets:
            self.load_installed_assets()

        json_data = self._installed_assets.get(app_name)
        if json_data:
            return InstalledAsset.from_json(json_data)

        return None

    def remove_installed_asset(self, app_name: str) -> None:
        """
        Remove an installed asset from the list.
        :param app_name: asset name.
        :return:
        """
        if app_name and app_name in self._installed_assets:
            del self._installed_assets[app_name]
            self.save_installed_assets()

    def update_installed_asset(self, app_name: str, asset_data: dict = None) -> None:
        """
        Update an installed asset data.
        :param app_name: asset name.
        :param asset_data: installed asset data.
        """
        if not app_name:
            return
        if not self._installed_assets:
            self._installed_assets = {}
        has_changed = True
        if asset_data is not None:
            if app_name in self._installed_assets:
                asset_existing = self._installed_assets[app_name]
                # merge the installed_folders fields
                installed_folders_existing = asset_existing.get('installed_folders', [])
                installed_folders_added = asset_data.get('installed_folders', [])
                installed_folders_merged = merge_lists_or_strings(installed_folders_existing, installed_folders_added)
                if installed_folders_merged != installed_folders_existing:
                    asset_data['installed_folders'] = installed_folders_merged
                    self._installed_assets[app_name].update(asset_data)
                else:
                    has_changed = False
            else:
                self._installed_assets[app_name] = asset_data
        else:
            return
        if has_changed:
            self.save_installed_assets()

    def set_installed_asset(self, installed_asset: InstalledAsset) -> None:
        """
        Set the installed asset. Will not create the list if it doesn't exist. Use add_to_installed_assets() instead.
        :param installed_asset: installed asset to set.
        """
        app_name = installed_asset.app_name
        if not app_name or app_name not in self._installed_assets:
            return
        self._installed_assets[app_name] = installed_asset.__dict__

    def add_to_installed_assets(self, installed_asset: InstalledAsset) -> bool:
        """
        Add an installed asset to the list.
        :param installed_asset: installed asset to add.
        :return: True if the asset was added.
        """
        if not self._installed_assets:
            self._installed_assets = {}
        app_name = installed_asset.app_name
        if app_name not in self._installed_assets:
            self._installed_assets[app_name] = installed_asset.__dict__
            return True
        return False

    def get_installed_assets(self) -> dict:
        """
        Get the installed asset data.
        :return: installed asset data.
        """
        return self._installed_assets

    def get_asset_size(self, app_name: str, default=0) -> int:
        """
        Get the size of an asset.
        :param app_name: asset name.
        :param default: default value to return if the asset is not found.
        :return: size of the asset, default if not found.
        """
        if not app_name:
            return default
        return self._asset_sizes.get(app_name, default)

    def set_asset_size(self, app_name: str, size: int) -> None:
        """
        Set the size of an asset.
        :param app_name: asset name.
        :param size: size of the asset.
        """
        if not app_name:
            return
        if self._asset_sizes is None:
            self._asset_sizes = {}
        self._asset_sizes[app_name] = size
        with open(self.asset_sizes_filename, 'w', encoding='utf-8') as file:
            json.dump(self._asset_sizes, file, indent=2, sort_keys=True)

    def save_config(self) -> None:
        """
        Save the config file.
        """
        # do not save if in read-only mode or file hasn't changed
        if self.config.read_only or not self.config.modified:
            return

        file_backup = create_file_backup(self.config_file)
        with open(self.config_file, 'w', encoding='utf-8') as file:
            self.config.write(file)
        # delete the backup if the files and the backup are identical
        if os.path.isfile(file_backup) and filecmp.cmp(self.config_file, file_backup):
            os.remove(file_backup)

    def clean_scraping(self) -> int:
        """
        Delete all the metadata files that are not in the names_to_keep list.
        :return: size of the deleted files.
        """
        folders = [gui_g.s.assets_data_folder, gui_g.s.owned_assets_data_folder, gui_g.s.assets_global_folder, gui_g.s.assets_csv_files_folder]
        return self.delete_folder_content(folders)

    def get_online_version_saved(self) -> dict:
        """
        Get the cached version data.
        :return: version data.
        """
        if self._update_info:
            return self._update_info
        try:
            with open(self.online_version_filename, 'r', encoding='utf-8') as file:
                self._update_info = json.load(file)
        except Exception as error:
            self.logger.debug(f'Failed to load cached version data: {error!r}')
            self._update_info = dict(last_update=0, data=None)
        return self._update_info

    def set_online_version_saved(self, version_data: dict) -> None:
        """
        Set the cached version data.
        :param version_data: version data.
        """
        if not version_data:
            return
        self._update_info = dict(last_update=time(), data=version_data)
        with open(self.online_version_filename, 'w', encoding='utf-8') as file:
            json.dump(self._update_info, file, indent=2, sort_keys=True)

    def extract_version_from_releases(self, release_info: dict) -> (dict, str):
        """
        Extract the version list and the release dict from the release info.
        :param release_info: release info (from the asset info).
        :return: (the release dict, the id of the latest release).
        """
        releases = {}
        all_installed_folders = {}
        installed_assets = self.get_installed_assets()
        latest_id = ''
        for asset_id, installed_asset in installed_assets.items():
            all_installed_folders[asset_id] = installed_asset['installed_folders']
        release_info = gui_fn.get_and_check_release_info(release_info, empty_values=gui_g.s.cell_is_nan_list)
        if release_info is None:
            return [], ''
        else:
            # TODO: print a message if release is not compatible with the version of the selected project or engine.
            for index, item in enumerate(reversed(release_info)):  # reversed to have the latest release first
                asset_id = item.get('appId', None)
                latest_id = latest_id or asset_id
                release_title = item.get('versionTitle', '') or asset_id
                compatible_list = item.get('compatibleApps', None)
                date_added = item.get('dateAdded', '')
                # Convert the string to a datetime object
                datetime_obj = datetime.strptime(date_added, DateFormat.epic)
                # Format the datetime object as "YYYY-MM-DD"
                formatted_date = datetime_obj.strftime(DateFormat.us_short)
                if asset_id is not None and release_title is not None and compatible_list is not None:
                    # remove 'UE_' from items of the compatible_list
                    compatible_list = [item.replace('UE_', '') for item in compatible_list]
                    data = {
                        # 'id': asset_id,  # duplicate with the dict key
                        'title': release_title,  #
                        'compatible': compatible_list,  #
                    }
                    compatible_str = check_and_convert_list_to_str(compatible_list)
                    desc = f'Release id: {asset_id}\nTitle: {release_title}\nRelease Date: {formatted_date}\nUE Versions: {compatible_str}'
                    folder_choice = {}
                    if all_installed_folders.get(asset_id, ''):
                        data['installed_folders'] = all_installed_folders.get(asset_id, [])
                        desc += f'\nInstalled in folders:\n'
                        # add each folder to the description
                        for folder in data['installed_folders']:
                            desc += f' - {folder}\n'
                            # create a sublist of folders for the version choice list
                            # generate a comprehensive label from the full path of a folder
                            # (ex: C:\Program Files\Epic Games\UE_4.27\Engine\Plugins\Marketplace\MyAsset)
                            # to be used in the version choice list
                            # (ex: MyAsset (4.27))
                            label = generate_label_from_path(folder)
                            folder_choice.update(
                                {
                                    label: {
                                        # 'id': label, # duplicate with the dict key
                                        'value': folder,  #
                                        'text': 'Select the installation folder to remove',  #
                                    }
                                }
                            )
                    data['desc'] = desc
                    data['content'] = folder_choice
                    releases[asset_id] = data
        return releases, latest_id

    def get_downloaded_assets_data(self, vault_cache_folder: str, max_depth: int = 3) -> dict:
        """
        Get the list of the assets in the Vault cache folder. Get its size from the installed_asset file if it exists.
        :param vault_cache_folder: Vault cache folder.
        :param max_depth: maximum depth of subfolders to include in the file list.
        :return: dict {asset_id: {size, path}}.

        Notes:
            The scan of a Vault cache folder with lots of assets can take a long time.
            This scan is done when the datatable is loaded.
            So, increase the max_depth value with care to avoid long loading times.
        """
        vault_cache_folder = os.path.normpath(vault_cache_folder) if vault_cache_folder else ''
        downloaded_assets = {}
        # scan the vault_cache_folder for files. Proceed level by level until max_depth is reached.
        for root, dirs, files in os.walk(vault_cache_folder):
            # print(f'scanning root: {root}')
            depth = root[len(vault_cache_folder) + len(os.path.sep):].count(os.path.sep)
            if depth == max_depth:
                # remove all subfolders from the list of folders to scan to speed up the process
                del dirs[:]
            for file in files:
                filename, _ = os.path.splitext(file)
                # print(f'root: {root}, file: {file}, filename: {filename}')
                if filename.lower() == gui_g.s.ue_manifest_filename.lower():
                    # print('==>found manifest file')
                    parts = root.split(os.sep)
                    asset_id = parts[-1]  # the folder name is the asset id
                    installed_asset = self.get_installed_asset(asset_id)
                    size = installed_asset.install_size if installed_asset else 1
                    file_path = os.path.join(root, file)
                    downloaded_assets[asset_id] = {'size': size, 'path': file_path}
        return downloaded_assets

    def pre_update_installed_folders(self, db_handler: UEAssetDbHandler = None) -> None:
        """
        Update the "installed folders" BEFORE loading the data.
        :param db_handler: database handler.
        """
        installed_assets_json = self.get_installed_assets().copy()  # copy because the content could change during the process
        merged_installed_folders = {}
        # get all installed folders for a given catalog_item_id
        for app_name, asset in installed_assets_json.items():
            installed_folders_ori = asset.get('installed_folders', None)
            # WE USE A COPY to avoid modifying the original list and merging all the installation folders for all releases
            installed_folders = installed_folders_ori.copy() if installed_folders_ori is not None else None
            if installed_folders:
                catalog_item_id = asset.get('catalog_item_id', None)
                if merged_installed_folders.get(catalog_item_id, None) is None:
                    merged_installed_folders[catalog_item_id] = installed_folders
                else:
                    merged_installed_folders[catalog_item_id].extend(installed_folders)
            else:
                # the installed_folders field is empty for the installed_assets, we remove it from the json file
                self.remove_installed_asset(app_name)

        # as it, all the formatting and filtering could be done at start with good values
        # update the database using catalog_item_id instead as asset_id to merge installed_folders for ALL the releases
        for catalog_item_id, folders_to_add in merged_installed_folders.items():
            db_handler.add_to_installed_folders(catalog_item_id=catalog_item_id, folders=folders_to_add)
        # update the installed_assets json file from the database info
        # NO TO DO because the in installed_folders have not the same content (for one asset in the json file, for all releases in the database)
        # installed_assets_db = db_handler.get_rows_with_installed_folders()
        # for app_name, asset_data in installed_assets_db.items():
        #  self.update_installed_asset(app_name, asset_data)
