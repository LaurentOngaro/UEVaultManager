# coding: utf-8

import json
import logging
import os
from collections import defaultdict
from pathlib import Path
from time import time

from UEVaultManager.models.app import *
from UEVaultManager.models.config import LGDConf
from UEVaultManager.utils.aliasing import generate_aliases
from UEVaultManager.utils.env import is_windows_mac_or_pyi
from .utils import clean_filename


class LGDLFS:

    def __init__(self, config_file=None):
        self.log = logging.getLogger('LGDLFS')

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
        self.assets_extras_data = dict()
        # UEVaultManager update check info
        self._update_info = None
        # UE assets metadata cache data
        self._ue_assets_cache_data = None

        # Config with item specific settings (e.g. start parameters, env variables)
        self.config = LGDConf(comment_prefixes='/', allow_no_value=True)

        # Folders used by the app
        self.manifests_folder = 'manifests'
        self.metadata_folder = 'metadata'
        self.tmp_folder = 'tmp'
        self.extras_folder = 'extras'

        if config_file:
            # if user specified a valid relative/absolute path use that,
            # otherwise create file in UEVaultManager config directory
            if os.path.exists(config_file):
                self.config_path = os.path.abspath(config_file)
            else:
                self.config_path = os.path.join(self.path, clean_filename(config_file))
            self.log.info(f'Using non-default config file "{self.config_path}"')
        else:
            self.config_path = os.path.join(self.path, 'config.ini')

        # ensure folders exist.

        for f in ['', self.manifests_folder, self.metadata_folder, self.tmp_folder, self.extras_folder]:
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
            self.config.read(self.config_path)
        except Exception as error:
            self.log.error(f'Unable to read configuration file, please ensure that file is valid! '
                           f'(Error: {repr(error)})')
            self.log.warning('Continuing with blank config in safe-mode...')
            self.config.read_only = True

        # make sure "UEVaultManager" section exists
        has_changed = False
        if 'UEVaultManager' not in self.config:
            self.config.add_section('UEVaultManager')
            has_changed = True

        # Add opt-out options with explainers
        if not self.config.has_option('UEVaultManager', 'disable_update_check'):
            self.config.set('UEVaultManager', '; Disables the automatic update check')
            self.config.set('UEVaultManager', 'disable_update_check', 'false')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'disable_update_notice'):
            self.config.set('UEVaultManager', '; Disables the notice about an available update on exit')
            self.config.set('UEVaultManager', 'disable_update_notice', 'false' if is_windows_mac_or_pyi() else 'true')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'create_output_backup'):
            self.config.set(
                'UEVaultManager',
                '; Create a backup of the output file (when using the --output option) suffixed by a timestamp before creating a new file'
            )
            self.config.set('UEVaultManager', 'create_output_backup', 'true')
            has_changed = True
        if not self.config.has_option('UEVaultManager', 'create_log_backup'):
            self.config.set('UEVaultManager', ';Create a backup of the log files that store asset analysis suffixed by a timestamp')
            self.config.set('UEVaultManager', 'create_log_backup', 'true')
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

        # load existing app metadata
        _meta = None
        for gm_file in os.listdir(os.path.join(self.path, 'metadata')):
            try:
                _meta = json.load(open(os.path.join(self.path, 'metadata', gm_file)))
                self.assets_metadata[_meta['app_name']] = _meta
            except Exception as error:
                self.log.debug(f'Loading asset meta file "{gm_file}" failed: {error!r}')

        # done when asset metadata is parsed to allow filtering
        # load existing app extras data
        # for gm_file in os.listdir(os.path.join(self.path, self.extras_folder)):
        #    try:
        #        _extras = json.load(open(os.path.join(self.path, self.extras_folder, gm_file)))
        #        self._assets_extras_data[_extras['asset_name']] = _extras
        #    except Exception as error:
        #        self.log.debug(f'Loading asset extras file "{gm_file}" failed: {error!r}')

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
        if self._user_data is not None:
            return self._user_data

        try:
            self._user_data = json.load(open(os.path.join(self.path, 'user.json')))
            return self._user_data
        except Exception as error:
            self.log.debug(f'Failed to load user data: {error!r}')
            return None

    @userdata.setter
    def userdata(self, userdata):
        if userdata is None:
            raise ValueError('Userdata is none!')

        self._user_data = userdata
        json.dump(userdata, open(os.path.join(self.path, 'user.json'), 'w'), indent=2, sort_keys=True)

    def invalidate_userdata(self):
        self._user_data = None
        if os.path.exists(os.path.join(self.path, 'user.json')):
            os.remove(os.path.join(self.path, 'user.json'))

    @property
    def entitlements(self):
        if self._entitlements is not None:
            return self._entitlements

        try:
            self._entitlements = json.load(open(os.path.join(self.path, 'entitlements.json')))
            return self._entitlements
        except Exception as error:
            self.log.debug(f'Failed to load entitlements data: {error!r}')
            return None

    @entitlements.setter
    def entitlements(self, entitlements):
        if entitlements is None:
            raise ValueError('Entitlements is none!')

        self._entitlements = entitlements
        json.dump(entitlements, open(os.path.join(self.path, 'entitlements.json'), 'w'), indent=2, sort_keys=True)

    @property
    def assets(self):
        if self._assets is None:
            try:
                tmp = json.load(open(os.path.join(self.path, 'assets.json')))
                self._assets = {k: [AppAsset.from_json(j) for j in v] for k, v in tmp.items()}
            except Exception as error:
                self.log.debug(f'Failed to load assets data: {error!r}')
                return None

        return self._assets

    @assets.setter
    def assets(self, assets):
        if assets is None:
            raise ValueError('Assets is none!')

        self._assets = assets
        json.dump(
            {platform: [a.__dict__ for a in assets] for platform, assets in self._assets.items()},
            open(os.path.join(self.path, 'assets.json'), 'w'),
            indent=2,
            sort_keys=True
        )

    def _get_manifest_filename(self, app_name, version, platform=None):
        if platform:
            file_name = clean_filename(f'{app_name}_{platform}_{version}')
        else:
            file_name = clean_filename(f'{app_name}_{version}')
        return os.path.join(self.path, self.manifests_folder, f'{file_name}.manifest')

    def load_manifest(self, app_name, version, platform='Windows'):
        try:
            return open(self._get_manifest_filename(app_name, version, platform), 'rb').read()
        except FileNotFoundError:  # all other errors should propagate
            self.log.debug(f'Loading manifest failed, retrying without platform in filename...')
            try:
                return open(self._get_manifest_filename(app_name, version), 'rb').read()
            except FileNotFoundError:  # all other errors should propagate
                return None

    def save_manifest(self, app_name, manifest_data, version, platform='Windows'):
        with open(self._get_manifest_filename(app_name, version, platform), 'wb') as f:
            f.write(manifest_data)

    def get_item_meta(self, app_name):
        # note: self._assets_metadata is filled ay the start of the list command by reading all the json files in the metadata folder
        if _meta := self.assets_metadata.get(app_name, None):
            return App.from_json(_meta)  # create an object from the App class using the json data
        return None

    def set_item_meta(self, app_name, meta):
        json_meta = meta.__dict__
        self.assets_metadata[app_name] = json_meta
        meta_file = os.path.join(self.path, 'metadata', f'{app_name}.json')
        json.dump(json_meta, open(meta_file, 'w'), indent=2, sort_keys=True)

    def delete_item_meta(self, app_name: str):
        if app_name not in self.assets_metadata:
            raise ValueError(f'Item {app_name} does not exist in metadata DB!')

        del self.assets_metadata[app_name]
        meta_file = os.path.join(self.path, 'metadata', f'{app_name}.json')
        if os.path.exists(meta_file):
            os.remove(meta_file)

    def get_item_extras(self, app_name: str):
        gm_file = app_name + '.json'
        extras = self.assets_extras_data.get(app_name, None)
        extras_file = os.path.join(self.path, self.extras_folder, f'{app_name}.json')
        if os.path.exists(extras_file):
²            try:
                extras = json.load(open(os.path.join(self.path, self.extras_folder, gm_file)))
                self.assets_extras_data[extras['asset_name']] = extras
            except json.decoder.JSONDecodeError:
                self.log.warning(f'Failed to load extras data for {app_name}!. Deleting file...')
                # delete the file
                try:
                    os.remove(extras_file)
                except Exception as error:
                    self.log.error(f'Failed to delete extras file {extras_file}: {error!r}')
            return None
        return extras

    def set_item_extras(self, app_name: str, extras: dict, update_global_dict: True):
        extras_file = os.path.join(self.path, self.extras_folder, f'{app_name}.json')
        self.log.debug(f'--- SAVING {len(extras)} extras data for {app_name} in {extras_file}')
        json.dump(extras, open(extras_file, 'w'), indent=2, sort_keys=True)
        if update_global_dict:
            self.assets_extras_data[app_name] = extras

    def delete_item_extras(self, app_name: str, update_global_dict: True):
        if update_global_dict and self.assets_extras_data.get(app_name):
            del self.assets_extras_data[app_name]
        extras_file = os.path.join(self.path, self.extras_folder, f'{app_name}.json')
        if os.path.exists(extras_file):
            os.remove(extras_file)

    def get_item_app_names(self):
        return sorted(self.assets_metadata.keys())

    def clean_tmp_data(self):
        for f in os.listdir(os.path.join(self.path, self.tmp_folder)):
            try:
                os.remove(os.path.join(self.path, self.tmp_folder, f))
            except Exception as error:
                self.log.warning(f'Failed to delete file "{f}": {error!r}')

    def clean_metadata(self, app_names_to_keep):
        for f in os.listdir(os.path.join(self.path, self.metadata_folder)):
            app_name = f.rpartition('.')[0]
            if app_name not in app_names_to_keep:
                try:
                    os.remove(os.path.join(self.path, self.metadata_folder, f))
                except Exception as error:
                    self.log.warning(f'Failed to delete file "{f}": {error!r}')

    def clean_extras(self, app_names_to_keep):
        for f in os.listdir(os.path.join(self.path, self.extras_folder)):
            app_name = f.rpartition('.')[0]
            if app_name not in app_names_to_keep:
                try:
                    os.remove(os.path.join(self.path, self.extras_folder, f))
                except Exception as error:
                    self.log.warning(f'Failed to delete file "{f}": {error!r}')

    def clean_manifests(self):
        for f in os.listdir(os.path.join(self.path, self.manifests_folder)):
            try:
                os.remove(os.path.join(self.path, self.manifests_folder, f))
            except Exception as error:
                self.log.warning(f'Failed to delete file "{f}": {error!r}')

    def clean_logs_and_backups(self):
        for f in os.listdir(self.path):
            file_name_no_ext, file_ext = os.path.splitext(f)
            if '.log' in file_ext or '.bak' in file_ext:
                try:
                    os.remove(os.path.join(self.path, f))
                except Exception as error:
                    self.log.warning(f'Failed to delete file "{f}": {error!r}')

    def save_config(self):
        # do not save if in read-only mode or file hasn't changed
        if self.config.read_only or not self.config.modified:
            return
        # if config file has been modified externally, back-up the user-modified version before writing
        if os.path.exists(self.config_path):
            if (mod_time := int(os.stat(self.config_path).st_mtime)) != self.config.mod_time:
                new_filename = f'config.{mod_time}.ini'
                self.log.warning(
                    f'Configuration file has been modified while UEVaultManager was running, '
                    f'user-modified config will be renamed to "{new_filename}"...'
                )
                os.rename(self.config_path, os.path.join(os.path.dirname(self.config_path), new_filename))

        with open(self.config_path, 'w') as cf:
            self.config.write(cf)

    def get_dir_size(self):
        return sum(f.stat().st_size for f in Path(self.path).glob('**/*') if f.is_file())

    def get_cached_version(self):
        if self._update_info:
            return self._update_info

        try:
            self._update_info = json.load(open(os.path.join(self.path, 'version.json')))
        except Exception as error:
            self.log.debug(f'Failed to load cached update data: {error!r}')
            self._update_info = dict(last_update=0, data=None)

        return self._update_info

    def set_cached_version(self, version_data):
        if not version_data:
            return
        self._update_info = dict(last_update=time(), data=version_data)
        json.dump(self._update_info, open(os.path.join(self.path, 'version.json'), 'w'), indent=2, sort_keys=True)

    def get_cached_sdl_data(self, app_name):
        try:
            return json.load(open(os.path.join(self.path, self.tmp_folder, f'{app_name}.json')))
        except Exception as error:
            self.log.debug(f'Failed to load cached SDL data: {error!r}')
            return None

    def set_cached_sdl_data(self, app_name, sdl_version, sdl_data):
        if not app_name or not sdl_data:
            return
        json.dump(
            dict(version=sdl_version, data=sdl_data),
            open(os.path.join(self.path, self.tmp_folder, f'{app_name}.json'), 'w'),
            indent=2,
            sort_keys=True
        )

    def generate_aliases(self):
        self.log.debug('Generating list of aliases...')

        self.aliases = dict()
        aliases = set()
        collisions = set()
        alias_map = defaultdict(set)

        for app_name in self.assets_metadata.keys():
            item = self.get_item_meta(app_name)
            if item.is_dlc:
                continue
            item_folder = item.metadata.get('customAttributes', {}).get('FolderName', {}).get('value', None)
            _aliases = generate_aliases(item.app_title, item_folder=item_folder, app_name=item.app_name)
            for alias in _aliases:
                if alias not in aliases:
                    aliases.add(alias)
                    alias_map[item.app_name].add(alias)
                else:
                    collisions.add(alias)

        # remove colliding aliases from map and add aliases to lookup table
        for app_name, aliases in alias_map.items():
            alias_map[app_name] -= collisions
            for alias in alias_map[app_name]:
                self.aliases[alias] = app_name

        def serialise_sets(obj):
            """Turn sets into sorted lists for storage"""
            return sorted(obj) if isinstance(obj, set) else obj

        json.dump(alias_map, open(os.path.join(self.path, 'aliases.json'), 'w', newline='\n'), indent=2, sort_keys=True, default=serialise_sets)

    # Get UE assets metadata cache data
    def get_ue_assets_cache_data(self):
        if self._ue_assets_cache_data:
            return self._ue_assets_cache_data

        try:
            self._ue_assets_cache_data = json.load(open(os.path.join(self.path, 'ue_assets_cache_data.json')))
        except Exception as error:
            self.log.debug(f'Failed to UE assets last update data: {error!r}')
            self._ue_assets_cache_data = dict(last_update=0, ue_assets_count=0)

        return self._ue_assets_cache_data

    # Set UE assets metadata cache data
    def set_ue_assets_cache_data(self, last_update: float, ue_assets_count: int):
        self._ue_assets_cache_data = dict(last_update=last_update, ue_assets_count=ue_assets_count)
        json.dump(self._ue_assets_cache_data, open(os.path.join(self.path, 'ue_assets_cache_data.json'), 'w'), indent=2, sort_keys=True)
