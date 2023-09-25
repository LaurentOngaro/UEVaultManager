# coding: utf-8
"""
Implementation for:
- UEVMLFS: Local File System.
"""
import filecmp
import json
import logging
import os
from time import time
from typing import Optional

import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.lfs.utils import clean_filename
from UEVaultManager.lfs.utils import path_join
from UEVaultManager.models.app import App, AppAsset, InstalledApp
from UEVaultManager.models.config import AppConf
from UEVaultManager.tkgui.modules.functions import create_file_backup
from UEVaultManager.utils.env import is_windows_mac_or_pyi


class UEVMLFS:
    """
    Class to handle all local filesystem related tasks.
    :param config_file: Path to config file to use instead of default.
    """

    def __init__(self, config_file=None):
        self.log = logging.getLogger('UEVMLFS')

        if config_path := os.environ.get('XDG_CONFIG_HOME'):
            self.path = path_join(config_path, 'UEVaultManager')
        else:
            self.path = os.path.expanduser('~/.config/UEVaultManager')

        # EGS user info
        self._user_data = None
        # EGS entitlements
        self._entitlements = None
        # EGS asset data
        self._assets = None
        # EGS metadata
        self.assets_metadata = dict()
        # additional infos (price, review...)
        self.assets_extra_data = dict()
        # UEVaultManager update check info
        self._update_info = None
        # UE assets metadata cache data
        self._assets_cache_info = None

        # Config with item specific settings (e.g. start parameters, env variables)
        self.config = AppConf(comment_prefixes='/', allow_no_value=True)

        # Folders used by the app
        self.manifests_folder = 'manifests'
        self.metadata_folder = 'metadata'
        self.tmp_folder = 'tmp'
        self.extra_folder = 'extra'

        if config_file:
            # if user specified a valid relative/absolute path use that,
            # otherwise create file in UEVaultManager config directory
            if os.path.exists(config_file):
                self.config_file = os.path.abspath(config_file)
            else:
                self.config_file = path_join(self.path, clean_filename(config_file))
            self.log.info(f'UEVMLFS is using non-default config file "{self.config_file}"')
        else:
            self.config_file = path_join(self.path, 'config.ini')

        # ensure folders exist.

        for f in ['', self.manifests_folder, self.metadata_folder, self.tmp_folder, self.extra_folder]:
            if not os.path.exists(path_join(self.path, f)):
                os.makedirs(path_join(self.path, f))

        # if "old" folder exists migrate files and remove it
        if os.path.exists(path_join(self.path, self.manifests_folder, 'old')):
            self.log.info('Migrating manifest files from old folders to new, please wait...')
            # remove not versioned manifest files
            for _f in os.listdir(path_join(self.path, self.manifests_folder)):
                if '.manifest' not in _f:
                    continue
                if '_' not in _f or (_f.startswith('UE_') and _f.count('_') < 2):
                    self.log.debug(f'Deleting "{_f}" ...')
                    os.remove(path_join(self.path, self.manifests_folder, _f))

            # move files from "old" to the base folder
            for _f in os.listdir(path_join(self.path, self.manifests_folder, 'old')):
                try:
                    self.log.debug(f'Renaming "{_f}"')
                    os.rename(path_join(self.path, self.manifests_folder, 'old', _f), path_join(self.path, self.manifests_folder, _f))
                except Exception as error:
                    self.log.warning(f'Renaming manifest file "{_f}" failed: {error!r}')

            # remove "old" folder
            try:
                os.removedirs(path_join(self.path, self.manifests_folder, 'old'))
            except Exception as error:
                self.log.warning(f'Removing "{path_join(self.path, "manifests", "old")}" folder failed: '
                                 f'{error!r}, please remove manually')

        # try loading config
        try:
            self.config.read(self.config_file)
        except Exception as error:
            self.log.error(f'Failed to read configuration file, please ensure that file is valid!:Error: {error!r}')
            self.log.warning('Continuing with blank config in safe-mode...')
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
            self.config.set('UEVaultManager', ';Set to True to start the App in Edit mode (since v1.4.4) with the GUI')
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
        if not self.config.has_option('UEVaultManager', 'ue_assets_max_cache_duration'):
            self.config.set('UEVaultManager', '; Delay in seconds when UE assets metadata cache will be invalidated. Default value represent 15 days')
            self.config.set('UEVaultManager', 'ue_assets_max_cache_duration', '1296000')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'ignored_assets_filename_log'):
            self.config.set(
                'UEVaultManager', '; File name (and path) to log issues with assets when running the --list command' + "\n" +
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
        if not self.config.has_option('UEVaultManager', 'scan_assets_filename_log'):
            self.config.set('UEVaultManager', 'scan_assets_filename_log', '~/.config/scan_assets.log')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'engine_version_for_obsolete_assets'):
            self.config.set('UEVaultManager', '; Minimal unreal engine version to check for obsolete assets (default is 4.26)')
            self.config.set(
                'UEVaultManager', 'engine_version_for_obsolete_assets', '4.26'
            )  # no access to the engine_version_for_obsolete_assets global settings here without importing its module
            has_changed = True

        if has_changed:
            self.save_config()

        # load existing installed assets/apps
        try:
            self._installed_apps = json.load(open(path_join(self.path, 'installed.json')))
        except Exception as error:
            self.log.debug(f'Loading installed assets failed: {error!r}')
            self._installed_apps = None

        # load existing app metadata
        _meta = None
        for gm_file in os.listdir(path_join(self.path, 'metadata')):
            try:
                _meta = json.load(open(path_join(self.path, 'metadata', gm_file)))
                self.assets_metadata[_meta['app_name']] = _meta
            except Exception as error:
                self.log.debug(f'Loading asset meta file "{gm_file}" failed: {error!r}')

        # done when asset metadata is parsed to allow filtering
        # load existing app extra data
        # for gm_file in os.listdir(path_join(self.path, self.extra_folder)):
        #    try:
        #        _extra = json.load(open(path_join(self.path, self.extra_folder, gm_file)))
        #        self._assets_extra_data[_extra['asset_name']] = _extra
        #    except Exception as error:
        #        self.log.debug(f'Loading asset extra file "{gm_file}" failed: {error!r}')

        # load auto-aliases if enabled
        self.aliases = dict()
        if not self.config.getboolean('UEVaultManager', 'disable_auto_aliasing', fallback=False):
            try:
                _j = json.load(open(path_join(self.path, 'aliases.json')))
                for app_name, aliases in _j.items():
                    for alias in aliases:
                        self.aliases[alias] = app_name
            except Exception as error:
                self.log.debug(f'Loading aliases failed with {error!r}')

    @property
    def userdata(self):
        """
        Return the user data as a dict.
        :return: User data.
        """
        if self._user_data is not None:
            return self._user_data

        try:
            self._user_data = json.load(open(path_join(self.path, 'user.json')))
            return self._user_data
        except Exception as error:
            self.log.debug(f'Failed to load user data: {error!r}')
            return None

    @userdata.setter
    def userdata(self, userdata: dict) -> None:
        """
        Set the user data.
        :param userdata: User data.
        """
        if userdata is None:
            raise ValueError('Userdata is none!')

        self._user_data = userdata
        json.dump(userdata, open(path_join(self.path, 'user.json'), 'w'), indent=2, sort_keys=True)

    def invalidate_userdata(self) -> None:
        """
        Invalidate the user data.
        """
        self._user_data = None
        if os.path.exists(path_join(self.path, 'user.json')):
            os.remove(path_join(self.path, 'user.json'))

    @property
    def assets(self):
        """
        Return the asset's data as a dict.
        :return: asset's data.
        """
        if self._assets is None:
            try:
                tmp = json.load(open(path_join(self.path, 'assets.json')))
                self._assets = {k: [AppAsset.from_json(j) for j in v] for k, v in tmp.items()}
            except Exception as error:
                self.log.debug(f"Failed to load asset's data: {error!r}")
                return None

        return self._assets

    @assets.setter
    def assets(self, assets) -> None:
        """
        Set the asset data.
        :param assets: assets.
        """
        if assets is None:
            raise ValueError('No Assets data!')

        self._assets = assets
        json.dump(
            {
                platform: [a.__dict__ for a in assets] for platform, assets in self._assets.items()
            },
            open(path_join(self.path, 'assets.json'), 'w'),
            indent=2,
            sort_keys=True
        )

    @staticmethod
    def load_filter_list(filename: str = '') -> Optional[dict]:
        """
        Load the filters from a json file
        :return: The filters or {} if not found. Will return None on error
        """
        if filename == '':
            filename = gui_g.s.last_opened_filter
        folder = gui_g.s.filters_folder
        full_filename = path_join(folder, filename)
        if not os.path.isfile(full_filename):
            return {}
        try:
            filters = json.load(open(full_filename))
        except (Exception, ):
            return None
        return filters

    @staticmethod
    def save_filter_list(filters: {}, filename: str = '') -> None:
        """
        Save the filters to a json file.
        """
        if filename == '':
            filename = gui_g.s.last_opened_filter
        folder = gui_g.s.filters_folder
        full_filename = path_join(folder, filename)
        if not full_filename:
            return
        json.dump(filters, open(full_filename, 'w'), indent=2, sort_keys=True)

    def _get_manifest_filename(self, app_name: str, version: str, platform: str = None) -> str:
        """
        Get the manifest filename.
        :param app_name: app name.
        :param version: version of the manifest.
        :param platform: platform of the manifest.
        :return: The manifest filename.
        """
        if platform:
            fname = clean_filename(f'{app_name}_{platform}_{version}')
        else:
            fname = clean_filename(f'{app_name}_{version}')
        return path_join(self.path, 'manifests', f'{fname}.manifest')

    def get_tmp_path(self) -> str:
        """
        Get the path to the tmp folder.
        :return: The path to the tmp folder.
        """
        return path_join(self.path, 'tmp')

    def delete_folder_content(self, folders=None, extensions_to_delete: list = None, file_name_to_keep: list = None) -> int:
        """
        Delete all the files in a folder that are not in the list_of_items_to_keep list.
        :param folders: The list of folder to clean. Could be a list or a string for a single folder.If None, the function will return 0.
        :param extensions_to_delete: The list of extensions to delete. Leave to Empty to delete all extentions.
        :param file_name_to_keep: The list of items to keep. Leave to Empty to delete all files.
        :return: The total size of deleted files.
        """
        if folders is None or not folders:
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
                self.log.warning("We can't delete the config folder without extensions to filter files!")
                continue
            if not os.path.isdir(folder):
                continue
            for f in os.listdir(folder):
                file_name = path_join(folder, f)
                # file_name = os.path.abspath(file_name)
                app_name, file_ext = os.path.splitext(f)
                file_ext = file_ext.lower()
                file_is_ok = (file_name_to_keep is None or app_name not in file_name_to_keep)
                ext_is_ok = (extensions_to_delete is None or file_ext in extensions_to_delete)
                if file_is_ok and ext_is_ok:
                    try:
                        size = os.path.getsize(file_name)
                        os.remove(file_name)
                        size_deleted += size
                    except Exception as error:
                        self.log.warning(f'Failed to delete file "{file_name}": {error!r}')
                elif os.path.isdir(file_name):
                    folders_to_clean.append(file_name)
        return size_deleted

    def load_manifest(self, app_name: str, version: str, platform: str = 'Windows') -> any:
        """
        Load the manifest data from a file.
        :param app_name: The name of the item.
        :param version: version of the manifest.
        :param platform: platform of the manifest.
        :return: The manifest data.
        """
        try:
            return open(self._get_manifest_filename(app_name, version, platform), 'rb').read()
        except FileNotFoundError:  # all other errors should propagate
            self.log.debug(f'Loading manifest failed, retrying without platform in filename...')
            try:
                return open(self._get_manifest_filename(app_name, version), 'rb').read()
            except FileNotFoundError:  # all other errors should propagate
                return None

    def save_manifest(self, app_name: str, manifest_data, version: str, platform: str = 'Windows') -> str:
        """
        Save the manifest data to a file.
        :param app_name: The name of the item.
        :param manifest_data: The manifest data.
        :param version: version of the manifest.
        :param platform: platform of the manifest.
        :return: The manifest filename.
        """
        filename = self._get_manifest_filename(app_name, version, platform)
        with open(filename, 'wb') as f:
            f.write(manifest_data)
        return filename

    def get_item_meta(self, app_name: str):
        """
        Get the metadata for an item.
        :param app_name: The name of the item.
        :return: an App object.
        """
        # Note: self._assets_metadata is filled at the start of the list command by reading all the json files in the metadata folder
        if _meta := self.assets_metadata.get(app_name, None):
            return App.from_json(_meta)  # create an object from the App class using the json data
        return None

    def set_item_meta(self, app_name: str, meta) -> None:
        """
        Set the metadata for an item.
        :param app_name: The name of the item.
        :param meta: The metadata object.
        """
        json_meta = meta.__dict__
        self.assets_metadata[app_name] = json_meta
        meta_file = path_join(self.path, 'metadata', f'{app_name}.json')
        json.dump(json_meta, open(meta_file, 'w'), indent=2, sort_keys=True)

    def delete_item_meta(self, app_name: str) -> None:
        """
        Delete the metadata for an item.
        :param app_name: The name of the item.
        """
        if app_name not in self.assets_metadata:
            raise ValueError(f'Item {app_name} does not exist in metadata DB!')

        del self.assets_metadata[app_name]
        meta_file = path_join(self.path, 'metadata', f'{app_name}.json')
        if os.path.exists(meta_file):
            os.remove(meta_file)

    def get_item_extra(self, app_name: str) -> dict:
        """
        Get the extra data for an app.
        :param app_name: The app name.
        :return: The extra data.
        """
        gm_file = app_name + '.json'
        extra = self.assets_extra_data.get(app_name, None)
        extra_file = path_join(self.path, self.extra_folder, f'{app_name}.json')
        if os.path.exists(extra_file):
            try:
                extra = json.load(open(path_join(self.path, self.extra_folder, gm_file)))
                self.assets_extra_data[extra['asset_name']] = extra
            except json.decoder.JSONDecodeError:
                self.log.warning(f'Failed to load extra data for {app_name}!. Deleting file...')
                # delete the file
                try:
                    os.remove(extra_file)
                except Exception as error:
                    self.log.error(f'Failed to delete extra file {extra_file}: {error!r}')
                return {}
        return extra

    def set_item_extra(self, app_name: str, extra: dict, update_global_dict: True) -> None:
        """
        Save the extra data for an app.
        :param app_name: The app name.
        :param extra: The extra data.
        :param update_global_dict: Update the global dict with the new data.
        """
        extra_file = path_join(self.path, self.extra_folder, f'{app_name}.json')
        self.log.debug(f'--- SAVING {len(extra)} extra data for {app_name} in {extra_file}')
        json.dump(extra, open(extra_file, 'w'), indent=2, sort_keys=True)
        if update_global_dict:
            self.assets_extra_data[app_name] = extra

    def delete_item_extra(self, app_name: str, update_global_dict: True) -> None:
        """
        Delete the extra data for an app.
        :param app_name: The app name.
        :param update_global_dict: Update the global dict with the new data.
        """
        if update_global_dict and self.assets_extra_data.get(app_name):
            del self.assets_extra_data[app_name]
        extra_file = path_join(self.path, self.extra_folder, f'{app_name}.json')
        if os.path.exists(extra_file):
            os.remove(extra_file)

    def get_item_app_names(self) -> list:
        """
        Get the list of app names.
        :return: The list of app names.
        """
        return sorted(self.assets_metadata.keys())

    def clean_tmp_data(self) -> int:
        """
        Delete all the files in the tmp folder.
        :return: The size of the deleted files.
        """
        folder = path_join(self.path, self.tmp_folder)
        return self.delete_folder_content(folder)

    def clean_cache_data(self) -> int:
        """
        Delete all the files in the cache folders.
        :return: The size of the deleted files.
        """
        return self.delete_folder_content(gui_g.s.cache_folder)

    def clean_metadata(self, app_names_to_keep: list) -> int:
        """
        Delete all the metadata files that are not in the app_names_to_keep list.
        :param app_names_to_keep: The list of app names to keep.
        :return: The size of the deleted files.
        """
        folder = path_join(self.path, self.metadata_folder)
        return self.delete_folder_content(folder, file_name_to_keep=app_names_to_keep)

    def clean_extra(self, app_names_to_keep: list) -> int:
        """
        Delete all the metadata files that are not in the app_names_to_keep list.
        :param app_names_to_keep: The list of app names to keep.
        :return: The size of the deleted files.
        """
        folder = path_join(self.path, self.extra_folder)
        return self.delete_folder_content(folder, file_name_to_keep=app_names_to_keep)

    def clean_manifests(self) -> int:
        """
        Delete all the metadata files that are not in the app_names_to_keep list.
        """
        folder = path_join(self.path, self.manifests_folder)
        return self.delete_folder_content(folder)

    def clean_logs_and_backups(self) -> int:
        """
        Delete all the log and backup files in the app folders.
        :return: The size of the deleted files.
        """
        folders = [self.path, gui_g.s.results_folder, gui_g.s.scraping_folder]
        return self.delete_folder_content(folders, ['.log', '.bak'])

    def get_installed_app(self, app_name: str) -> Optional[InstalledApp]:
        """
        Get the installed app data.
        :param app_name: The app name.
        :return: The installed app data or None if not found.
        """
        if not app_name:
            return None
        if self._installed_apps is None:
            try:
                self._installed_apps = json.load(open(path_join(self.path, 'installed.json')))
            except Exception as error:
                self.log.debug(f'Failed to load installed asset data: {error!r}')
                return None
        if json_data := self._installed_apps.get(app_name, None):
            return InstalledApp.from_json(json_data)
        return None

    def set_installed_app(self, app_name: str, install_info: {}) -> None:
        """
        Set the installed app data.
        :param app_name: The app name.
        :param install_info: The installed app data.
        """
        if self._installed_apps is None:
            self._installed_apps = dict()
        if app_name in self._installed_apps:
            self._installed_apps[app_name].update(install_info.__dict__)
        else:
            self._installed_apps[app_name] = install_info.__dict__
        json.dump(self._installed_apps, open(path_join(self.path, 'installed.json'), 'w'), indent=2, sort_keys=True)

    def save_config(self) -> None:
        """
        Save the config file.
        """
        # do not save if in read-only mode or file hasn't changed
        if self.config.read_only or not self.config.modified:
            return

        file_backup = create_file_backup(self.config_file)
        with open(self.config_file, 'w') as cf:
            self.config.write(cf)
        # delete the backup if the files and the backup are identical
        if os.path.isfile(file_backup) and filecmp.cmp(self.config_file, file_backup):
            os.remove(file_backup)

    def clean_scrapping(self) -> int:
        """
        Delete all the metadata files that are not in the app_names_to_keep list.
        :return: The size of the deleted files.
        """
        folders = [gui_g.s.assets_data_folder, gui_g.s.owned_assets_data_folder, gui_g.s.assets_global_folder, gui_g.s.assets_csv_files_folder]
        return self.delete_folder_content(folders)

    def get_cached_version(self) -> dict:
        """
        Get the cached version data.
        :return: version data.
        """
        if self._update_info:
            return self._update_info
        try:
            self._update_info = json.load(open(path_join(self.path, 'version.json')))
        except Exception as error:
            self.log.debug(f'Failed to load cached update data: {error!r}')
            self._update_info = dict(last_update=0, data=None)

        return self._update_info

    def set_cached_version(self, version_data: dict) -> None:
        """
        Set the cached version data.
        :param version_data: The version data.
        """
        if not version_data:
            return
        self._update_info = dict(last_update=time(), data=version_data)
        json.dump(self._update_info, open(path_join(self.path, 'version.json'), 'w'), indent=2, sort_keys=True)

    def get_assets_cache_info(self) -> dict:
        """
        Get assets metadata cache information.
        :return: dict {last_update, ue_assets_count}.
        """
        if self._assets_cache_info:
            return self._assets_cache_info

        try:
            self._assets_cache_info = json.load(open(path_join(self.path, 'assets_cache_info.json')))
        except Exception as error:
            self.log.debug(f'Failed to UE assets last update data: {error!r}')
            self._assets_cache_info = dict(last_update=0, ue_assets_count=0)

        return self._assets_cache_info

    # Set UE assets metadata cache data
    def set_assets_cache_info(self, last_update: float, ue_assets_count: int) -> None:
        """
        Set assets metadata cache information.
        :param last_update: last update time.
        :param ue_assets_count: number of UE assets on last update.
        :return:
        """
        self._assets_cache_info = dict(last_update=last_update, ue_assets_count=ue_assets_count)
        json.dump(self._assets_cache_info, open(path_join(self.path, 'assets_cache_info.json'), 'w'), indent=2, sort_keys=True)
