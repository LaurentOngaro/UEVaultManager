# coding: utf-8
"""
Implementation for:
- UEVMLFS: Local File System.
"""
import filecmp
import json
import logging
import os
from pathlib import Path
from time import time

from UEVaultManager.models.app import *
from UEVaultManager.models.config import AppConf
from UEVaultManager.utils.env import is_windows_mac_or_pyi
from .utils import clean_filename
from ..tkgui.modules.functions import create_file_backup


class UEVMLFS:
    """
    Class to handle all local filesystem related tasks.
    :param config_file: Path to config file to use instead of default.
    """

    def __init__(self, config_file=None):
        self.log = logging.getLogger('UEVMLFS')

        if config_path := os.environ.get('XDG_CONFIG_HOME'):
            self.path = os.path.join(config_path, 'UEVaultManager')
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
                self.config_file = os.path.join(self.path, clean_filename(config_file))
            self.log.info(f'UEVMLFS is using non-default config file "{self.config_file}"')
        else:
            self.config_file = os.path.join(self.path, 'config.ini')

        # ensure folders exist.

        for f in ['', self.manifests_folder, self.metadata_folder, self.tmp_folder, self.extra_folder]:
            if not os.path.exists(os.path.join(self.path, f)):
                os.makedirs(os.path.join(self.path, f))

        # if "old" folder exists migrate files and remove it
        if os.path.exists(os.path.join(self.path, self.manifests_folder, 'old')):
            self.log.info('Migrating manifest files from old folders to new, please wait...')
            # remove not versioned manifest files
            for _f in os.listdir(os.path.join(self.path, self.manifests_folder)):
                if '.manifest' not in _f:
                    continue
                if '_' not in _f or (_f.startswith('UE_') and _f.count('_') < 2):
                    self.log.debug(f'Deleting "{_f}" ...')
                    os.remove(os.path.join(self.path, self.manifests_folder, _f))

            # move files from "old" to the base folder
            for _f in os.listdir(os.path.join(self.path, self.manifests_folder, 'old')):
                try:
                    self.log.debug(f'Renaming "{_f}"')
                    os.rename(os.path.join(self.path, self.manifests_folder, 'old', _f), os.path.join(self.path, self.manifests_folder, _f))
                except Exception as error:
                    self.log.warning(f'Renaming manifest file "{_f}" failed: {error!r}')

            # remove "old" folder
            try:
                os.removedirs(os.path.join(self.path, self.manifests_folder, 'old'))
            except Exception as error:
                self.log.warning(f'Removing "{os.path.join(self.path, "manifests", "old")}" folder failed: '
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
        if not self.config.has_option('UEVaultManager', 'start_in_edit_mode'):
            self.config.set('UEVaultManager', ';Set to True to start the App in Edit mode (since v1.4.4) with the GUI')
            self.config.set('UEVaultManager', 'start_in_edit_mode', 'False')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'disable_update_check'):
            self.config.set('UEVaultManager', ';Set to True to disable the automatic update check')
            self.config.set('UEVaultManager', 'disable_update_check', 'False')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'disable_update_notice'):
            self.config.set('UEVaultManager', '; Set to True to disable the notice about an available update on exit')
            self.config.set('UEVaultManager', 'disable_update_notice', 'False' if is_windows_mac_or_pyi() else 'True')
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
                'UEVaultManager', '; File name (and path) for logging issues with assets when running the --list command' + "\n" +
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

        # load existing app metadata
        _meta = None
        for gm_file in os.listdir(os.path.join(self.path, 'metadata')):
            try:
                _meta = json.load(open(os.path.join(self.path, 'metadata', gm_file)))
                self.assets_metadata[_meta['app_name']] = _meta
            except Exception as error:
                self.log.debug(f'Loading asset meta file "{gm_file}" failed: {error!r}')

        # done when asset metadata is parsed to allow filtering
        # load existing app extra data
        # for gm_file in os.listdir(os.path.join(self.path, self.extra_folder)):
        #    try:
        #        _extra = json.load(open(os.path.join(self.path, self.extra_folder, gm_file)))
        #        self._assets_extra_data[_extra['asset_name']] = _extra
        #    except Exception as error:
        #        self.log.debug(f'Loading asset extra file "{gm_file}" failed: {error!r}')

        # load auto-aliases if enabled
        self.aliases = dict()
        if not self.config.getboolean('UEVaultManager', 'disable_auto_aliasing', fallback=False):
            try:
                _j = json.load(open(os.path.join(self.path, 'aliases.json')))
                for app_name, aliases in _j.items():
                    for alias in aliases:
                        self.aliases[alias] = app_name
            except Exception as error:
                self.log.debug(f'Loading aliases failed with {error!r}')

    @property
    def userdata(self):
        """
        Returns the user data as a dict.
        :return: User data.
        """
        if self._user_data is not None:
            return self._user_data

        try:
            self._user_data = json.load(open(os.path.join(self.path, 'user.json')))
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
        json.dump(userdata, open(os.path.join(self.path, 'user.json'), 'w'), indent=2, sort_keys=True)

    def invalidate_userdata(self) -> None:
        """
        Invalidate the user data.
        """
        self._user_data = None
        if os.path.exists(os.path.join(self.path, 'user.json')):
            os.remove(os.path.join(self.path, 'user.json'))

    @property
    def assets(self):
        """
        Returns the assets data as a dict.
        :return: Assets data.
        """
        if self._assets is None:
            try:
                tmp = json.load(open(os.path.join(self.path, 'assets.json')))
                self._assets = {k: [AppAsset.from_json(j) for j in v] for k, v in tmp.items()}
            except Exception as error:
                self.log.debug(f'Failed to load assets data: {error!r}')
                return None

        return self._assets

    @assets.setter
    def assets(self, assets) -> None:
        """
        Set the asset data.
        :param assets: assets.
        """
        if assets is None:
            raise ValueError('Assets is none!')

        self._assets = assets
        json.dump(
            {platform: [a.__dict__ for a in assets] for platform, assets in self._assets.items()},
            open(os.path.join(self.path, 'assets.json'), 'w'),
            indent=2,
            sort_keys=True
        )

    def delete_folder(self, folder: str, list_of_items_to_keep=None) -> bool:
        """
        Delete all the files in a folder that are not in the list_of_items_to_keep list.
        :param folder: The folder to clean.
        :param list_of_items_to_keep: The list of items to keep.
        """
        if list_of_items_to_keep is None:
            list_of_items_to_keep = []
        for f in os.listdir(os.path.join(self.path, folder)):
            app_name = f.rpartition('.')[0]
            if list_of_items_to_keep is None or app_name not in list_of_items_to_keep:
                try:
                    os.remove(os.path.join(self.path, folder, f))
                except Exception as error:
                    self.log.warning(f'Failed to delete file "{f}": {error!r}')
                    return False
        return True

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
        meta_file = os.path.join(self.path, 'metadata', f'{app_name}.json')
        json.dump(json_meta, open(meta_file, 'w'), indent=2, sort_keys=True)

    def delete_item_meta(self, app_name: str) -> None:
        """
        Delete the metadata for an item.
        :param app_name: The name of the item.
        """
        if app_name not in self.assets_metadata:
            raise ValueError(f'Item {app_name} does not exist in metadata DB!')

        del self.assets_metadata[app_name]
        meta_file = os.path.join(self.path, 'metadata', f'{app_name}.json')
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
        extra_file = os.path.join(self.path, self.extra_folder, f'{app_name}.json')
        if os.path.exists(extra_file):
            try:
                extra = json.load(open(os.path.join(self.path, self.extra_folder, gm_file)))
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
        extra_file = os.path.join(self.path, self.extra_folder, f'{app_name}.json')
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
        extra_file = os.path.join(self.path, self.extra_folder, f'{app_name}.json')
        if os.path.exists(extra_file):
            os.remove(extra_file)

    def get_item_app_names(self) -> list:
        """
        Get the list of app names.
        :return: The list of app names.
        """
        return sorted(self.assets_metadata.keys())

    def clean_tmp_data(self) -> None:
        """
        Delete all the files in the tmp folder.
        """
        self.delete_folder(self.tmp_folder)

    def clean_metadata(self, app_names_to_keep: list) -> None:
        """
        Delete all the metadata files that are not in the app_names_to_keep list.
        :param app_names_to_keep: The list of app names to keep.
        """
        self.delete_folder(self.metadata_folder, app_names_to_keep)

    def clean_extra(self, app_names_to_keep: list) -> None:
        """
        Delete all the metadata files that are not in the app_names_to_keep list.
        :param app_names_to_keep: The list of app names to keep.
        """
        self.delete_folder(self.extra_folder, app_names_to_keep)

    def clean_manifests(self) -> None:
        """
        Delete all the metadata files that are not in the app_names_to_keep list.
        """
        self.delete_folder(self.manifests_folder)

    def clean_logs_and_backups(self) -> None:
        """
        Delete all the log and backup files in the app folder.
        """
        for f in os.listdir(self.path):
            file_name_no_ext, file_ext = os.path.splitext(f)
            if '.log' in file_ext or '.bak' in file_ext:
                try:
                    os.remove(os.path.join(self.path, f))
                except Exception as error:
                    self.log.warning(f'Failed to delete file "{f}": {error!r}')

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
        if filecmp.cmp(self.config_file, file_backup):
            os.remove(file_backup)

    def get_dir_size(self) -> int:
        """
        Get the size of the directory.
        :return: The size of the directory.
        """
        return sum(f.stat().st_size for f in Path(self.path).glob('**/*') if f.is_file())

    def get_cached_version(self) -> dict:
        """
        Get the cached version data.
        :return: version data.
        """
        if self._update_info:
            return self._update_info
        try:
            self._update_info = json.load(open(os.path.join(self.path, 'version.json')))
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
        json.dump(self._update_info, open(os.path.join(self.path, 'version.json'), 'w'), indent=2, sort_keys=True)

    def get_assets_cache_info(self) -> dict:
        """
        Get assets metadata cache information.
        :return: dict {last_update, ue_assets_count}.
        """
        if self._assets_cache_info:
            return self._assets_cache_info

        try:
            self._assets_cache_info = json.load(open(os.path.join(self.path, 'assets_cache_info.json')))
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
        json.dump(self._assets_cache_info, open(os.path.join(self.path, 'assets_cache_info.json'), 'w'), indent=2, sort_keys=True)
