# coding: utf-8

import json
import os
import logging
from datetime import datetime
from collections import defaultdict
from pathlib import Path
from time import time

from .utils import clean_filename

from UEVaultManager.models.app import *
from UEVaultManager.utils.aliasing import generate_aliases
from UEVaultManager.models.config import LGDConf
from UEVaultManager.utils.env import is_windows_mac_or_pyi


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
        self._assets_metadata = dict()
        # UEVaultManager update check info
        self._update_info = None
        # UE assets metadata cache data (Hack LO)
        self._ue_assets_cache_data = None

        # Config with item specific settings (e.g. start parameters, env variables)
        self.config = LGDConf(comment_prefixes='/', allow_no_value=True)

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
        for f in ['', 'manifests', 'metadata', 'tmp']:
            if not os.path.exists(os.path.join(self.path, f)):
                os.makedirs(os.path.join(self.path, f))

        # if "old" folder exists migrate files and remove it
        if os.path.exists(os.path.join(self.path, 'manifests', 'old')):
            self.log.info('Migrating manifest files from old folders to new, please wait...')
            # remove unversioned manifest files
            for _f in os.listdir(os.path.join(self.path, 'manifests')):
                if '.manifest' not in _f:
                    continue
                if '_' not in _f or (_f.startswith('UE_') and _f.count('_') < 2):
                    self.log.debug(f'Deleting "{_f}" ...')
                    os.remove(os.path.join(self.path, 'manifests', _f))

            # move files from "old" to the base folder
            for _f in os.listdir(os.path.join(self.path, 'manifests', 'old')):
                try:
                    self.log.debug(f'Renaming "{_f}"')
                    os.rename(os.path.join(self.path, 'manifests', 'old', _f), os.path.join(self.path, 'manifests', _f))
                except Exception as e:
                    self.log.warning(f'Renaming manifest file "{_f}" failed: {e!r}')

            # remove "old" folder
            try:
                os.removedirs(os.path.join(self.path, 'manifests', 'old'))
            except Exception as e:
                self.log.warning(f'Removing "{os.path.join(self.path, "manifests", "old")}" folder failed: '
                                 f'{e!r}, please remove manually')

        # try loading config
        try:
            self.config.read(self.config_path)
        except Exception as e:
            self.log.error(f'Unable to read configuration file, please ensure that file is valid! '
                           f'(Error: {repr(e)})')
            self.log.warning('Continuing with blank config in safe-mode...')
            self.config.read_only = True

        # make sure "UEVaultManager" section exists
        if 'UEVaultManager' not in self.config:
            self.config.add_section('UEVaultManager')

        # Add opt-out options with explainers
        if not self.config.has_option('UEVaultManager', 'disable_update_check'):
            self.config.set('UEVaultManager', '; Disables the automatic update check')
            self.config.set('UEVaultManager', 'disable_update_check', 'false')
        if not self.config.has_option('UEVaultManager', 'disable_update_notice'):
            self.config.set('UEVaultManager', '; Disables the notice about an available update on exit')
            self.config.set('UEVaultManager', 'disable_update_notice', 'false' if is_windows_mac_or_pyi() else 'true')

        # load existing app metadata
        for gm_file in os.listdir(os.path.join(self.path, 'metadata')):
            try:
                _meta = json.load(open(os.path.join(self.path, 'metadata', gm_file)))
                self._assets_metadata[_meta['app_name']] = _meta
            except Exception as e:
                self.log.debug(f'Loading asset meta file "{gm_file}" failed: {e!r}')

        # load auto-aliases if enabled
        self.aliases = dict()
        if not self.config.getboolean('UEVaultManager', 'disable_auto_aliasing', fallback=False):
            try:
                _j = json.load(open(os.path.join(self.path, 'aliases.json')))
                for app_name, aliases in _j.items():
                    for alias in aliases:
                        self.aliases[alias] = app_name
            except Exception as e:
                self.log.debug(f'Loading aliases failed with {e!r}')

    @property
    def userdata(self):
        if self._user_data is not None:
            return self._user_data

        try:
            self._user_data = json.load(open(os.path.join(self.path, 'user.json')))
            return self._user_data
        except Exception as e:
            self.log.debug(f'Failed to load user data: {e!r}')
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
        except Exception as e:
            self.log.debug(f'Failed to load entitlements data: {e!r}')
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
            except Exception as e:
                self.log.debug(f'Failed to load assets data: {e!r}')
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
            fname = clean_filename(f'{app_name}_{platform}_{version}')
        else:
            fname = clean_filename(f'{app_name}_{version}')
        return os.path.join(self.path, 'manifests', f'{fname}.manifest')

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
        if _meta := self._assets_metadata.get(app_name, None):
            return App.from_json(_meta)
        return None

    def set_item_meta(self, app_name, meta):
        json_meta = meta.__dict__
        self._assets_metadata[app_name] = json_meta
        meta_file = os.path.join(self.path, 'metadata', f'{app_name}.json')
        json.dump(json_meta, open(meta_file, 'w'), indent=2, sort_keys=True)

    def delete_item_meta(self, app_name):
        if app_name not in self._assets_metadata:
            raise ValueError(f'Item {app_name} does not exist in metadata DB!')

        del self._assets_metadata[app_name]
        meta_file = os.path.join(self.path, 'metadata', f'{app_name}.json')
        if os.path.exists(meta_file):
            os.remove(meta_file)

    def get_item_app_names(self):
        return sorted(self._assets_metadata.keys())

    def get_tmp_path(self):
        return os.path.join(self.path, 'tmp')

    def clean_tmp_data(self):
        for f in os.listdir(os.path.join(self.path, 'tmp')):
            try:
                os.remove(os.path.join(self.path, 'tmp', f))
            except Exception as e:
                self.log.warning(f'Failed to delete file "{f}": {e!r}')

    def clean_metadata(self, app_names):
        for f in os.listdir(os.path.join(self.path, 'metadata')):
            app_name = f.rpartition('.')[0]
            if app_name not in app_names:
                try:
                    os.remove(os.path.join(self.path, 'metadata', f))
                except Exception as e:
                    self.log.warning(f'Failed to delete file "{f}": {e!r}')

    def clean_manifests(self, in_use):
        in_use_files = {f'{clean_filename(f"{app_name}_{version}")}.manifest' for app_name, version, _ in in_use}

        in_use_files |= {f'{clean_filename(f"{app_name}_{platform}_{version}")}.manifest' for app_name, version, platform in in_use}

        for f in os.listdir(os.path.join(self.path, 'manifests')):
            if f not in in_use_files:
                try:
                    os.remove(os.path.join(self.path, 'manifests', f))
                except Exception as e:
                    self.log.warning(f'Failed to delete file "{f}": {e!r}')

    def save_config(self):
        # do not save if in read-only mode or file hasn't changed
        if self.config.read_only or not self.config.modified:
            return
        # if config file has been modified externally, back-up the user-modified version before writing
        if os.path.exists(self.config_path):
            if (modtime := int(os.stat(self.config_path).st_mtime)) != self.config.modtime:
                new_filename = f'config.{modtime}.ini'
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
        except Exception as e:
            self.log.debug(f'Failed to load cached update data: {e!r}')
            self._update_info = dict(last_update=0, data=None)

        return self._update_info

    def set_cached_version(self, version_data):
        if not version_data:
            return
        self._update_info = dict(last_update=time(), data=version_data)
        json.dump(self._update_info, open(os.path.join(self.path, 'version.json'), 'w'), indent=2, sort_keys=True)

    def get_cached_sdl_data(self, app_name):
        try:
            return json.load(open(os.path.join(self.path, 'tmp', f'{app_name}.json')))
        except Exception as e:
            self.log.debug(f'Failed to load cached SDL data: {e!r}')
            return None

    def set_cached_sdl_data(self, app_name, sdl_version, sdl_data):
        if not app_name or not sdl_data:
            return
        json.dump(dict(version=sdl_version, data=sdl_data), open(os.path.join(self.path, 'tmp', f'{app_name}.json'), 'w'), indent=2, sort_keys=True)

    def generate_aliases(self):
        self.log.debug('Generating list of aliases...')

        self.aliases = dict()
        aliases = set()
        collisions = set()
        alias_map = defaultdict(set)

        for app_name in self._assets_metadata.keys():
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

    # Get UE assets metadata cache data (Hack LO)
    def get_ue_assets_cache_data(self):
        if self._ue_assets_cache_data:
            return self._ue_assets_cache_data

        try:
            self._ue_assets_cache_data = json.load(open(os.path.join(self.path, 'ue_assets_cache_data.json')))
        except Exception as e:
            self.log.debug(f'Failed to UE assets last update data: {e!r}')
            self._ue_assets_cache_data = dict(last_update=0, ue_assets_count=0)

        return self._ue_assets_cache_data

    # Set UE assets metadata cache data (Hack LO)
    def set_ue_assets_cache_data(self, ue_assets_count):
        self._ue_assets_cache_data = dict(last_update=datetime.now().timestamp(), ue_assets_count=ue_assets_count)
        json.dump(self._ue_assets_cache_data, open(os.path.join(self.path, 'ue_assets_cache_data.json'), 'w'), indent=2, sort_keys=True)