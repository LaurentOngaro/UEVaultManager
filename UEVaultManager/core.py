# coding=utf-8
"""
Implementation for:
- AppCore: handles most of the lower level interaction with the downloader, lfs, and api components to make writing CLI/GUI code easier and cleaner and avoid duplication.
- CSV_headings: contains the title of each column and a boolean value to know if its contents must be preserved if it already exists in the output file (To Avoid overwriting data changed by the user in the file)
"""
import json
import logging
import os
import time
from base64 import b64decode
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from hashlib import sha1
from locale import getlocale, LC_CTYPE
from platform import system
from threading import current_thread, enumerate as thread_enumerate
from urllib.parse import urlparse

from requests import session
from requests.exceptions import HTTPError, ConnectionError

import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager import __version__ as UEVM_version
from UEVaultManager.api.egs import EPCAPI, GrabResult
from UEVaultManager.api.uevm import UEVMAPI
from UEVaultManager.lfs.egl import EPCLFS
from UEVaultManager.lfs.uevmlfs import UEVMLFS
from UEVaultManager.models.app import *
from UEVaultManager.models.exceptions import *
from UEVaultManager.models.json_manifest import JSONManifest
from UEVaultManager.models.manifest import Manifest
from UEVaultManager.utils.cli import check_and_create_path
from UEVaultManager.utils.egl_crypt import decrypt_epic_data
from UEVaultManager.utils.env import is_windows_mac_or_pyi

# The heading dict contains the title of each column and a boolean value to know if its contents must be preserved if it already exists in the output file (To Avoid overwriting data changed by the user in the file)
CSV_headings = {
    'Asset_id': False,  # ! important: Do not Rename => this field is used as main key for each asset
    'App name': False,
    'App title': False,
    'Category': False,
    'UE Version': False,
    'Review': False,
    'Developer': False,
    'Description': False,
    'Status': False,
    'Discount Price': False,
    'On sale': False,
    'Purchased': False,
    'Obsolete': True,
    'Supported Versions': False,
    'Grab result': False,
    'Price': False,  # ! important: Rename Wisely => this field is searched by text in the next lines
    'Old Price': False,  # ! important: always place it after the Price field in the list
    # User Fields
    'Comment': True,
    'Stars': True,
    'Must Buy': True,
    'Test result': True,
    'Installed Folder': True,
    'Alternative': True,
    'Asset Folder': True,
    # less important fields
    'Page title': False,
    'Image': False,
    'Url': True,  # could be kept if a better url that can be used to download the asset is found
    'Compatible Versions': False,
    'Date Added': True,
    'Creation Date': False,
    'Update Date': False,
    'Uid': False
}

# ToDo: instead of true/false return values for success/failure actually raise an exception that the CLI/GUI
#  can handle to give the user more details. (Not required yet since there's no GUI so log output is fine)


class AppCore:
    """
    AppCore handles most of the lower level interaction with
    the downloader, lfs, and api components to make writing CLI/GUI
    code easier and cleaner and avoid duplication.
    :param override_config: path to a config file to use instead of the default
    :param timeout: timeout in seconds for requests
    """
    _egl_version = '11.0.1-14907503+++Portal+Release-Live'

    def __init__(self, override_config=None, timeout=10.0):
        self.log = logging.getLogger('Core')
        self.egs = EPCAPI(timeout=timeout)
        self.uevmlfs = UEVMLFS(config_file=override_config)
        self.egl = EPCLFS()
        self.uevm_api = UEVMAPI()

        # on non-Windows load the programdata path from config
        if os.name != 'nt':
            self.egl.programdata_path = self.uevmlfs.config.get('UEVaultManager', 'egl_programdata', fallback=None)
            if self.egl.programdata_path and not os.path.exists(self.egl.programdata_path):
                self.log.error(f'Config EGL path ("{self.egl.programdata_path}") is invalid! Disabling sync...')
                self.egl.programdata_path = None
                self.uevmlfs.config.remove_option('UEVaultManager', 'egl_programdata')
                self.uevmlfs.save_config()

        self.local_timezone = datetime.now().astimezone().tzinfo
        self.language_code, self.country_code = ('en', 'US')

        if locale := self.uevmlfs.config.get('UEVaultManager', 'locale', fallback=getlocale(LC_CTYPE)[0]):
            try:
                self.language_code, self.country_code = locale.split('-' if '-' in locale else '_')
                self.log.debug(f'Set locale to {self.language_code}-{self.country_code}')
                # adjust egs api language as well
                self.egs.language_code, self.egs.country_code = self.language_code, self.country_code
            except Exception as error:
                self.log.warning(f'Getting locale failed: {error!r}, falling back to using en-US.')
        elif system() != 'Darwin':  # macOS doesn't have a default locale we can query
            self.log.warning('Could not determine locale, falling back to en-US')

        self.update_available = False
        self.force_show_update = False
        self.webview_killswitch = False
        self.logged_in = False

        self.default_datetime_format = '%y-%m-%d %H:%M:%S'
        # UE assets metadata cache properties
        self.ue_assets_count = 0
        self.cache_is_invalidate = False
        # Delay (in seconds) when UE assets metadata cache will be invalidated. Default value is 15 days
        self.ue_assets_max_cache_duration = 15 * 24 * 3600
        # set to True to add print more information during long operations
        self.verbose_mode = False
        # Create a backup of the output file (when using the --output option) suffixed by a timestamp before creating a new file
        self.create_output_backup = True
        # Set the file name (and path) for logging when an asset is ignored or filtered when running the --list command
        self.ignored_assets_filename_log = ''
        # Set the file name (and path) for logging when an asset is not found on the marketplace when running the --list command
        self.notfound_assets_filename_log = ''
        # Set the file name (and path) for logging when an asset has metadata and extras data are incoherent when running the --list command
        self.bad_data_assets_filename_log = ''
        # Create a backup of the log files that store asset analysis suffixed by a timestamp before creating a new file
        self.create_log_backup = True
        # new file loggers
        self.ignored_logger = None
        self.notfound_logger = None
        self.bad_data_logger = None
        # store time to process metadata and extras update
        self.process_time_average = {'time': 0.0, 'count': 0}
        self.use_threads = False
        self.thread_executor = None
        self.thread_executor_must_stop = False
        self.engine_version_for_obsolete_assets = '4.26'

    def setup_assets_logging(self) -> None:
        """
        Setup logging for ignored, not found and bad data assets
        """
        formatter = logging.Formatter('%(message)s')
        message = f"-----\n{datetime.now().strftime(self.default_datetime_format)} Log Started\n-----\n"

        if self.ignored_assets_filename_log != '':
            ignored_assets_filename_log = self.ignored_assets_filename_log.replace('~/.config', self.uevmlfs.path)
            if check_and_create_path(ignored_assets_filename_log):
                ignored_assets_handler = logging.FileHandler(ignored_assets_filename_log, mode='w')
                ignored_assets_handler.setFormatter(formatter)
                self.ignored_logger = logging.Logger('IgnoredAssets', 'INFO')
                self.ignored_logger.addHandler(ignored_assets_handler)
                self.ignored_logger.info(message)

        if self.notfound_assets_filename_log != '':
            notfound_assets_filename_log = self.notfound_assets_filename_log.replace('~/.config', self.uevmlfs.path)
            if check_and_create_path(notfound_assets_filename_log):
                notfound_assets_handler = logging.FileHandler(notfound_assets_filename_log, mode='w')
                notfound_assets_handler.setFormatter(formatter)
                self.notfound_logger = logging.Logger('NotFoundAssets', 'INFO')
                self.notfound_logger.addHandler(notfound_assets_handler)
                self.notfound_logger.info(message)

        if self.bad_data_assets_filename_log != '':
            bad_data_assets_filename_log = self.bad_data_assets_filename_log.replace('~/.config', self.uevmlfs.path)
            if check_and_create_path(bad_data_assets_filename_log):
                bad_data_assets_handler = logging.FileHandler(bad_data_assets_filename_log, mode='w')
                bad_data_assets_handler.setFormatter(formatter)
                self.bad_data_logger = logging.Logger('BadDataAssets', 'INFO')
                self.bad_data_logger.addHandler(bad_data_assets_handler)
                self.bad_data_logger.info(message)

    def auth_sid(self, sid) -> str:
        """
        Handles getting an exchange code from an id
        :param sid: session id
        :return: exchange code
        """
        s = session()
        s.headers.update(
            {
                'X-Epic-Event-Action':
                'login',
                'X-Epic-Event-Category':
                'login',
                'X-Epic-Strategy-Flags':
                '',
                'X-Requested-With':
                'XMLHttpRequest',
                'User-Agent':
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                f'EpicGamesLauncher/{self._egl_version} '
                'UnrealEngine/4.23.0-14907503+++Portal+Release-Live '
                'Chrome/84.0.4147.38 Safari/537.36'
            }
        )
        s.cookies['EPIC_COUNTRY'] = self.country_code.upper()

        # get first set of cookies (EPIC_BEARER_TOKEN etc.)
        _ = s.get('https://www.epicgames.com/id/api/set-sid', params=dict(sid=sid))
        # get XSRF-TOKEN and EPIC_SESSION_AP cookie
        _ = s.get('https://www.epicgames.com/id/api/csrf')
        # finally, get the exchange code
        r = s.post('https://www.epicgames.com/id/api/exchange/generate', headers={'X-XSRF-TOKEN': s.cookies['XSRF-TOKEN']})

        if r.status_code == 200:
            return r.json()['code']

        self.log.error(f'Getting exchange code failed: {r.json()}')
        return ''

    def auth_code(self, code) -> bool:
        """
        Handles authentication via authorization code (either retrieved manually or automatically)
        """
        try:
            self.uevmlfs.userdata = self.egs.start_session(authorization_code=code)
            return True
        except Exception as error:
            self.log.error(f'Logging in failed with {error!r}, please try again.')
            return False

    def auth_ex_token(self, code) -> bool:
        """
        Handles authentication via exchange token (either retrieved manually or automatically)
        """
        try:
            self.uevmlfs.userdata = self.egs.start_session(exchange_token=code)
            return True
        except Exception as error:
            self.log.error(f'Logging in failed with {error!r}, please try again.')
            return False

    def auth_import(self) -> bool:
        """Import refresh token from EGL installation and use it for logging in"""
        self.egl.read_config()
        remember_me_data = self.egl.config.get('RememberMe', 'Data')
        raw_data = b64decode(remember_me_data)
        # data is encrypted
        if raw_data[0] != '{':
            for data_key in self.egl.data_keys:
                try:
                    decrypted_data = decrypt_epic_data(data_key, raw_data)
                    re_data = json.loads(decrypted_data)[0]
                    break
                except Exception as error:
                    self.log.debug(f'Decryption with key {data_key} failed with {error!r}')
            else:
                raise ValueError('Decryption of EPIC launcher user information failed.')
        else:
            re_data = json.loads(raw_data)[0]

        if 'Token' not in re_data:
            raise ValueError('No login session in config')
        refresh_token = re_data['Token']
        try:
            self.uevmlfs.userdata = self.egs.start_session(refresh_token=refresh_token)
            return True
        except Exception as error:
            self.log.error(f'Logging in failed with {error!r}, please try again.')
            return False

    def login(self, force_refresh=False) -> bool:
        """
        Attempts logging in with existing credentials.

        raises ValueError if no existing credentials or InvalidCredentialsError if the API return an error
        """
        if not self.uevmlfs.userdata:
            raise ValueError('No saved credentials')
        elif self.logged_in and self.uevmlfs.userdata['expires_at']:
            dt_exp = datetime.fromisoformat(self.uevmlfs.userdata['expires_at'][:-1])
            dt_now = datetime.utcnow()
            td = dt_now - dt_exp

            # if session still has at least 10 minutes left we can re-use it.
            if dt_exp > dt_now and abs(td.total_seconds()) > 600:
                return True
            else:
                self.logged_in = False

        # run update check
        if self.update_check_enabled():
            try:
                self.check_for_updates()
            except Exception as error:
                self.log.warning(f'Checking for UEVaultManager updates failed: {error!r}')

        if self.uevmlfs.userdata['expires_at'] and not force_refresh:
            dt_exp = datetime.fromisoformat(self.uevmlfs.userdata['expires_at'][:-1])
            dt_now = datetime.utcnow()
            td = dt_now - dt_exp

            # if session still has at least 10 minutes left we can re-use it.
            if dt_exp > dt_now and abs(td.total_seconds()) > 600:
                self.log.info('Trying to re-use existing login session...')
                try:
                    self.egs.resume_session(self.uevmlfs.userdata)
                    self.logged_in = True
                    return True
                except InvalidCredentialsError as error:
                    self.log.warning(f'Resuming failed due to invalid credentials: {error!r}')
                except Exception as error:
                    self.log.warning(f'Resuming failed for unknown reason: {error!r}')
                # If verify fails just continue the normal authentication process
                self.log.info('Falling back to using refresh token...')

        try:
            self.log.info('Logging in...')
            userdata = self.egs.start_session(self.uevmlfs.userdata['refresh_token'])
        except InvalidCredentialsError:
            self.log.error('Stored credentials are no longer valid! Please login again.')
            self.uevmlfs.invalidate_userdata()
            return False
        except (HTTPError, ConnectionError) as error:
            self.log.error(f'HTTP request for login failed: {error!r}, please try again later.')
            return False

        self.uevmlfs.userdata = userdata
        self.logged_in = True
        return True

    def update_check_enabled(self) -> bool:
        """
        Returns whether update checks are enabled or not
        :return: True if update checks are enabled, False otherwise
        """
        return not self.uevmlfs.config.getboolean('UEVaultManager', 'disable_update_check', fallback=False)

    def update_notice_enabled(self) -> bool:
        """
        Returns whether update notices are enabled or not
        :return: True if update notices are enabled, False otherwise
        """
        if self.force_show_update:
            return True
        return not self.uevmlfs.config.getboolean('UEVaultManager', 'disable_update_notice', fallback=not is_windows_mac_or_pyi())

    def check_for_updates(self, force=False) -> None:
        """
        Checks for updates and sets the update_available flag accordingly
        :param force: force update check
        """

        def version_tuple(v):
            """
            Converts a version string to a tuple of ints
            :param v: version string
            :return:  tuple of ints
            """
            return tuple(map(int, (v.split('.'))))

        cached = self.uevmlfs.get_cached_version()
        version_info = cached['data']
        if force or not version_info or (datetime.now().timestamp() - cached['last_update']) > 24 * 3600:
            version_info = self.uevm_api.get_version_information()
            self.uevmlfs.set_cached_version(version_info)

        web_version = version_info['version']
        self.update_available = version_tuple(web_version) > version_tuple(UEVM_version)

    def get_update_info(self) -> dict:
        """
        Returns update info dict
        :return: update info dict
        """
        return self.uevmlfs.get_cached_version()['data']

    def update_aliases(self, force=False) -> None:
        """
        Updates aliases if enabled
        :param force: force alias update
        """
        _aliases_enabled = not self.uevmlfs.config.getboolean('UEVaultManager', 'disable_auto_aliasing', fallback=False)
        if _aliases_enabled and (force or not self.uevmlfs.aliases):
            self.uevmlfs.generate_aliases()

    def get_assets(self, update_assets=False, platform='Windows') -> List[AppAsset]:
        """
        Returns a list of assets for the given platform.
        :param update_assets: if True, always fetches a new list of assets from the server
        :param platform: platform to fetch assets for
        :return: list of AppAsset objects
        """
        # do not save and always fetch list when platform is overridden
        if not self.uevmlfs.assets or update_assets or platform not in self.uevmlfs.assets:
            # if not logged in, return empty list
            if not self.egs.user:
                return []

            assets = self.uevmlfs.assets.copy() if self.uevmlfs.assets else dict()

            assets.update({platform: [AppAsset.from_egs_json(a) for a in self.egs.get_item_assets(platform=platform)]})

            # only save (and write to disk) if there were changes
            if self.uevmlfs.assets != assets:
                self.uevmlfs.assets = assets

        return self.uevmlfs.assets[platform]

    def get_asset(self, app_name: str, platform='Windows', update=False) -> AppAsset:
        """
        Returns an AppAsset object for the given app name and platform
        :param app_name: app name to get
        :param platform: platform to get asset for
        :param update: force update of asset list
        :return: AppAsset object
        """
        if update or platform not in self.uevmlfs.assets:
            self.get_assets(update_assets=True, platform=platform)

        try:
            return next(i for i in self.uevmlfs.assets[platform] if i.app_name == app_name)
        except StopIteration:
            raise ValueError

    def asset_available(self, item: App, platform='Windows') -> bool:
        """
        Returns whether an asset is available for the given item and platform
        :param item: item to check
        :param platform:
        :return: True if asset is available, False otherwise
        """
        # Just say yes for Origin titles
        if item.third_party_store:
            return True

        try:
            asset = self.get_asset(item.app_name, platform=platform)
            return asset is not None
        except ValueError:
            return False

    def get_item(self, app_name, update_meta=False, platform='Windows') -> App:
        """
        Returns an App object
        :param app_name: name to get
        :param update_meta: force update of metadata
        :param platform: platform to get app for
        :return: App object
        """
        if update_meta:
            self.get_asset_list(True, platform=platform)
        return self.uevmlfs.get_item_meta(app_name)

    def get_asset_list(self, update_assets=True, platform='Windows', filter_category='', force_refresh=False) -> (List[App], Dict[str, List[App]]):
        """
        Returns a list of all available assets for the given platform
        :param update_assets: force update of asset list
        :param platform: platform to get assets for
        :param filter_category: filter by category
        :param force_refresh: force refresh of asset list
        :return: Assets list
        """

        # Cancel all outstanding tasks and shut down the executor
        def stop_executor(tasks) -> None:
            """
            Cancel all outstanding tasks and shut down the executor
            :param tasks: tasks to cancel
            """
            for _, task in tasks.items():
                task.cancel()
            self.thread_executor.shutdown(wait=False)

        def fetch_asset_meta(name: str) -> bool:
            """
            Fetches asset metadata for the given app name and adds it to the list of assets
            :param name: app name
            :return: True if successful, False otherwise
            """
            if (name in currently_fetching or not fetch_list.get(name)) and ('Asset_Fetcher' in thread_enumerate()) or self.thread_executor_must_stop:
                return False

            thread_data = ''
            if self.use_threads:
                thread = current_thread()
                thread_data = f' ==> By Thread name={thread.name}'

            self.log.debug(f'--- START fetching data {name}{thread_data}')

            currently_fetching[name] = True
            start_time = datetime.now()
            name, namespace, catalog_item_id, _process_meta, _process_extras = fetch_list[name]

            if _process_meta:
                eg_meta = self.egs.get_item_info(namespace, catalog_item_id, timeout=10.0)
                app = App(app_name=name, app_title=eg_meta['title'], metadata=eg_meta, asset_infos=assets[name])
                self.uevmlfs.set_item_meta(app.app_name, app)
                apps[name] = app

            if _process_extras:
                # we use title because it's less ambiguous than a name when searching an asset
                eg_extras = self.egs.get_assets_extras(asset_name=name, asset_title=apps[name].app_title, verbose_mode=self.verbose_mode)
                self.uevmlfs.set_item_extras(app_name=name, extras=eg_extras, update_global_dict=True)

                # log the asset if the title in metadata and the title in the marketplace grabbed page are not identical
                if eg_extras['page_title'] != '' and eg_extras['page_title'] != apps[name].app_title:
                    self.log.warning(f'{name} has incoherent data. It has been added to the bad_data_logger file')
                    eg_extras['grab_result'] = GrabResult.INCONSISTANT_DATA.name
                    if self.bad_data_logger:
                        self.bad_data_logger.info(name)

            # compute process time and average in s
            end_time = datetime.now()
            process_time = (end_time - start_time).total_seconds()
            self.process_time_average['time'] += process_time
            self.process_time_average['count'] += 1

            if fetch_list.get(name):
                del fetch_list[name]
                if self.verbose_mode:
                    self.log.info(f'Removed {name} from the metadata update')

            if currently_fetching.get(name):
                del currently_fetching[name]

            if not self.use_threads:
                process_average = self.process_time_average['time'] / self.process_time_average['count']
                self.log.info(f'===Time Average={process_average:.3f} s # ({(len(fetch_list) * process_average):.3f} s time left)')

            self.log.info(
                f'--- END fetching data in {name}{thread_data}. Time For Processing={process_time:.3f}s # Still {len(fetch_list)} assets to process'
            )
            if gui_g.progress_window_ref is not None and not gui_g.progress_window_ref.update_and_continue(increment=1):
                self.thread_executor_must_stop = True
                return False
            return True

        _ret = []
        meta_updated = False

        # fetch asset information for Windows, all installed platforms, and the specified one
        platforms = {'Windows'}
        platforms |= {platform}
        if gui_g.progress_window_ref is not None:
            gui_g.progress_window_ref.reset(new_value=0, new_text="Fetching platforms...", new_max_value=len(platforms))
        for _platform in platforms:
            self.get_assets(update_assets=update_assets, platform=_platform)
            if gui_g.progress_window_ref is not None and not gui_g.progress_window_ref.update_and_continue(increment=1):
                return []

        if not self.uevmlfs.assets:
            return _ret

        assets = {}
        if gui_g.progress_window_ref is not None:
            gui_g.progress_window_ref.reset(new_value=0, new_text="Fetching assets...", new_max_value=len(self.uevmlfs.assets.items()))
        for _platform, _assets in self.uevmlfs.assets.items():
            for _asset in _assets:
                if gui_g.progress_window_ref is not None and not gui_g.progress_window_ref.update_and_continue(increment=1):
                    return []
                if _asset.app_name in assets:
                    assets[_asset.app_name][_platform] = _asset
                else:
                    assets[_asset.app_name] = {_platform: _asset}

        fetch_list = {}
        assets_bypassed = {}
        apps = {}

        # loop through assets items to check for if they are for ue or not
        valid_items = []
        bypass_count = 0
        self.log.info(f'======\nSTARTING phase 1: asset indexing (ue or not)\n')
        if gui_g.progress_window_ref is not None:
            gui_g.progress_window_ref.reset(new_value=0, new_text="Indexing assets...", new_max_value=len(assets.items()))
        # note: we sort by reverse, as it the most recent version of an asset will be listed first
        for app_name, app_assets in sorted(assets.items(), reverse=True):
            if gui_g.progress_window_ref is not None and not gui_g.progress_window_ref.update_and_continue(increment=1):
                return []
            # notes:
            #   asset_id is not unique because somme assets can have the same asset_id but with several UE versions
            #   app_name is unique because it includes the unreal version
            # asset_id = app_assets['Windows'].asset_id
            assets_bypassed[app_name] = False
            if app_assets['Windows'].namespace != 'ue':
                self.log.debug(f'{app_name} has been bypassed (namespace != "ue") in phase 1')
                bypass_count += 1
                assets_bypassed[app_name] = True
                continue

            item = {'name': app_name, 'asset': app_assets}
            valid_items.append(item)

        self.ue_assets_count = len(valid_items)

        self.log.info(f'A total of {bypass_count} on {len(valid_items)} assets have been bypassed in phase 1')

        # check if we must refresh ue asset metadata cache
        self.check_for_ue_assets_updates(self.ue_assets_count, force_refresh)
        force_refresh = self.cache_is_invalidate
        if force_refresh:
            self.log.info(f'!! Assets metadata will be updated !!\n')
        else:
            self.log.info(f"Asset metadata won't be updated\n")

        self.log.info(f'======\nSTARTING phase 2:asset filtering and metadata updating\n')
        if gui_g.progress_window_ref is not None:
            gui_g.progress_window_ref.reset(new_value=0, new_text="Updating metadata...", new_max_value=len(valid_items))
        # loop through valid items to check for update and filtering
        bypass_count = 0
        filtered_items = []
        currently_fetching = {}
        i = 0
        while i < len(valid_items):
            if gui_g.progress_window_ref is not None and not gui_g.progress_window_ref.update_and_continue(increment=1):
                return []
            item = valid_items[i]
            app_name = item['name']
            app_assets = item['asset']
            if self.verbose_mode:
                self.log.info(f'Checking {app_name}....')

            item_metadata = self.uevmlfs.get_item_meta(app_name)
            asset_updated = False

            if not item_metadata:
                self.log.info(f'Metadata for {app_name} are missing. It Will be ADDED to the FETCH list')
            else:
                category = str(item_metadata.metadata['categories'][0]['path']).lower()
                if filter_category and filter_category.lower() not in category:
                    self.log.info(
                        f'{app_name} has been FILTERED by category ("{filter_category}" text not found in "{category}").It has been added to the ignored_logger file'
                    )
                    if self.ignored_logger:
                        self.ignored_logger.info(app_name)
                    assets_bypassed[app_name] = True
                    bypass_count += 1
                    i += 1
                    continue
                asset_updated = any(item_metadata.app_version(_p) != app_assets[_p].build_version for _p in app_assets.keys())
                apps[app_name] = item_metadata
                self.log.debug(f'{app_name} has been ADDED to the apps list with asset_updated={asset_updated}')

            # get extras data only in not filtered
            if force_refresh or asset_updated:
                process_extras = True
            else:
                # will read the extras data from file if necessary and put in the global dict
                process_extras = self.uevmlfs.get_item_extras(app_name) is None

            process_meta = not item_metadata or force_refresh or asset_updated

            if update_assets and (process_extras or process_meta):
                self.log.debug(f'Scheduling metadata and extras update for {app_name}')
                # namespace/catalog item are the same for all platforms, so we can just use the first one
                _ga = next(iter(app_assets.values()))
                fetch_list[app_name] = (app_name, _ga.namespace, _ga.catalog_item_id, process_meta, process_extras)
                meta_updated = True
            i += 1
            filtered_items.append(item)
            # end while i < len(valid_items):

        # setup and teardown of thread pool takes some time, so only do it when it makes sense.
        self.use_threads = len(fetch_list) > 5
        # self.use_threads = False  # test only
        if fetch_list:
            if gui_g.progress_window_ref is not None:
                gui_g.progress_window_ref.reset(
                    new_value=0, new_text="Fetching missing metadata...\nIt could take some time. Be patient.", new_max_value=len(fetch_list)
                )
                # gui_g.progress_window_ref.hide_progress_bar()
                # gui_g.progress_window_ref.hide_stop_button()

            self.log.info(f'Fetching metadata for {len(fetch_list)} app(s).')
            if self.use_threads:
                # note:  unreal engine API limits the number of connection to 16. So no more than 16 threads !

                # with ThreadPoolExecutor(max_workers=min(16, os.cpu_count() - 2), thread_name_prefix="Asset_Fetcher") as executor:
                #    executor.map(fetch_asset_meta, fetch_list.keys(), timeout=30.0)
                self.thread_executor = ThreadPoolExecutor(max_workers=min(16, os.cpu_count() + 2), thread_name_prefix="Asset_Fetcher")
                # Dictionary that maps each key to its corresponding Future object
                futures = {}
                for key in fetch_list.keys():
                    # Submit the task and add its Future to the dictionary
                    future = self.thread_executor.submit(fetch_asset_meta, key)
                    futures[key] = future
                    if self.thread_executor_must_stop:
                        self.log.info(f'User stop has been pressed. Stopping running threads....')
                        stop_executor(futures)
                        return []

        self.log.info(f'A total of {bypass_count} on {len(valid_items)} assets have been bypassed in phase 2')
        self.log.info(f'======\nSTARTING phase 3: emptying the List of assets to be fetched \n')
        if gui_g.progress_window_ref is not None:
            # gui_g.progress_window_ref.show_progress_bar()  # show progress bar, must be before reset
            gui_g.progress_window_ref.show_stop_button()
            gui_g.progress_window_ref.reset(new_value=0, new_text="Checking and Fetching assets data...", new_max_value=len(filtered_items))
        # loop through valid and filtered items
        meta_updated = (bypass_count == 0) and meta_updated  # to avoid deleting metadata files or assets that have been filtered
        while len(filtered_items) > 0:
            if gui_g.progress_window_ref is not None and not gui_g.progress_window_ref.update_and_continue(increment=1):
                return []
            item = filtered_items.pop()
            app_name = item['name']
            app_assets = item['asset']
            if self.verbose_mode:
                self.log.info(f'Checking {app_name}. Still {len(filtered_items)} assets to check')
            try:
                app_item = apps.get(app_name)
            except (KeyError, IndexError):
                self.log.debug(f'{app_name} has not been found int the app list. Bypassing')
                # item not found in app, ignore and pass to next one
                continue

            # retry if the asset is still in fetch list (with active fetcher treads)
            if fetch_list.get(app_name) and (not currently_fetching.get(app_name) or 'Asset_Fetcher' not in thread_enumerate()):
                self.log.info(f'Fetching metadata for {app_name} is still no done, retrying')
                if currently_fetching.get(app_name):
                    del currently_fetching[app_name]
                fetch_asset_meta(app_name)

            try:
                is_bypassed = (app_name in assets_bypassed) and (assets_bypassed[app_name])
                is_a_mod = any(i['path'] == 'mods' for i in app_item.metadata.get('categories', []))
            except (KeyError, IndexError, AttributeError):
                self.log.debug(f'{app_name} has no metadata. Adding to the fetch list (again)')
                try:
                    fetch_list[app_name] = (app_name, item.namespace, item.catalog_item_id, True, True)
                    _ret.append(app_item)
                except (KeyError, IndexError, AttributeError):
                    self.log.debug(f'{app_name} has an invalid format. Could not been added to the fetch list')
                continue

            has_valid_platform = platform in app_assets
            is_still_fetching = (app_name in fetch_list) or (app_name in currently_fetching)

            if is_still_fetching:
                # put again the asset in the list waiting when it will be fetched
                filtered_items.append(item)
                time.sleep(3)  # Sleep for 3 seconds to let the fetch process progress or end

            # check if the asset will be added to the final list
            if not is_bypassed and not is_still_fetching and not is_a_mod and has_valid_platform:
                _ret.append(app_item)

        self.log.info(f'A total of {len(_ret)} assets have been analysed and kept in phase 3')

        self.update_aliases(force=meta_updated)

        if meta_updated:
            if gui_g.progress_window_ref is not None:
                gui_g.progress_window_ref.reset(new_value=0, new_text="Updating metadata files...", new_max_value=len(_ret))
            # delete old files
            self._prune_metadata()
            self._save_metadata(_ret)
        #  meta_updated = True  # test only
        if meta_updated:
            if gui_g.progress_window_ref is not None:
                gui_g.progress_window_ref.reset(new_value=0, new_text="Updating extras data files...", new_max_value=len(_ret))
            # save new ones
            self._prune_extras_data(update_global_dict=False)
            self._save_extras_data(self.uevmlfs.assets_extras_data, update_global_dict=False)
        return _ret

    # end def get_asset_list(self, update_assets=True, platform='Windows', filter_category='') -> (List[App], Dict[str, List[App]]):

    def _prune_metadata(self) -> None:
        """
        Compile a list of assets without assets, then delete their metadata
        """
        # compile list of assets without assets, then delete their metadata
        available_assets = set()
        available_assets |= {i.app_name for i in self.get_assets(platform='Windows')}

        for app_name in self.uevmlfs.get_item_app_names():
            self.log.debug(f'Removing old/unused metadata for "{app_name}"')
            self.uevmlfs.delete_item_meta(app_name)

    def _prune_extras_data(self, update_global_dict: True) -> None:
        """
        Compile a list of assets without assets, then delete their extras data
        :param update_global_dict:  if True, update the global dict
        """
        available_assets = set()
        available_assets |= {i.app_name for i in self.get_assets(platform='Windows')}

        for app_name in self.uevmlfs.get_item_app_names():
            self.log.debug(f'Removing old/unused extras data for "{app_name}"')
            self.uevmlfs.delete_item_extras(app_name, update_global_dict=update_global_dict)

    def _save_metadata(self, assets) -> None:
        """
        Save the metadata for the given assets
        :param assets:  List of assets to save
        """
        for app in assets:
            if gui_g.progress_window_ref is not None and not gui_g.progress_window_ref.update_and_continue(increment=1):
                return
            self.uevmlfs.set_item_meta(app.app_name, app)

    def _save_extras_data(self, extras: dict, update_global_dict: True) -> None:
        """
        Save the extras data for the given assets
        :param extras: Dict of extras data to save
        :param update_global_dict: if True, update the global dict
        """
        for app_name, eg_extras in extras.items():
            if gui_g.progress_window_ref is not None and not gui_g.progress_window_ref.update_and_continue(increment=1):
                return
            self.uevmlfs.set_item_extras(app_name=app_name, extras=eg_extras, update_global_dict=update_global_dict)

    def get_non_asset_library_items(self, force_refresh=False, skip_ue=True) -> (List[App], Dict[str, List[App]]):
        """
        Gets a list of Items without assets for installation, for instance Items delivered via
        third-party stores that do not have assets for installation

        :param force_refresh: Force a metadata refresh
        :param skip_ue: Ignore Unreal Marketplace entries
        :return: List of Items that do not have assets
        """
        _ret = []
        # get all the app names we have to ignore
        ignore = set(i.app_name for i in self.get_assets())

        for lib_item in self.egs.get_library_items():
            if lib_item['namespace'] == 'ue' and skip_ue:
                continue
            if lib_item['appName'] in ignore:
                continue

            item = self.uevmlfs.get_item_meta(lib_item['appName'])
            if not item or force_refresh:
                eg_meta = self.egs.get_item_info(lib_item['namespace'], lib_item['catalogItemId'])
                item = App(app_name=lib_item['appName'], app_title=eg_meta['title'], metadata=eg_meta)
                self.uevmlfs.set_item_meta(item.app_name, item)

            if not any(i['path'] == 'mods' for i in item.metadata.get('categories', [])):
                _ret.append(item)

        # Force refresh to make sure these titles are included in aliasing
        self.update_aliases(force=True)
        return _ret

    @staticmethod
    def load_manifest(data: bytes) -> Manifest:
        """
        Load a manifest
        :param data: Bytes object to load the manifest from
        :return: Manifest object
        """
        if data[0:1] == b'{':
            return JSONManifest.read_all(data)
        else:
            return Manifest.read_all(data)

    def get_cdn_urls(self, item, platform='Windows'):
        """
        Get the CDN URLs
        :param item: Item to get the CDN URLs for
        :param platform: Platform to get the CDN URLs for
        :return: List of CDN URLs
        """
        m_api_r = self.egs.get_item_manifest(item.namespace, item.catalog_item_id, item.app_name, platform)

        # never seen this outside the launcher itself, but if it happens: PANIC!
        if len(m_api_r['elements']) > 1:
            raise ValueError('Manifest response has more than one element!')

        manifest_hash = m_api_r['elements'][0]['hash']
        base_urls = []
        manifest_urls = []
        for manifest in m_api_r['elements'][0]['manifests']:
            base_url = manifest['uri'].rpartition('/')[0]
            if base_url not in base_urls:
                base_urls.append(base_url)

            if 'queryParams' in manifest:
                params = '&'.join(f'{p["name"]}={p["value"]}' for p in manifest['queryParams'])
                manifest_urls.append(f'{manifest["uri"]}?{params}')
            else:
                manifest_urls.append(manifest['uri'])

        return manifest_urls, base_urls, manifest_hash

    def get_cdn_manifest(self, item, platform='Windows', disable_https=False):
        """
        Get the CDN manifest
        :param item: Item to get the CDN manifest for
        :param platform: Platform to get the CDN manifest for
        :param disable_https: Disable HTTPS for the manifest URLs
        :return: list of base URLs, manifest hash
        """
        manifest_urls, base_urls, manifest_hash = self.get_cdn_urls(item, platform)
        if not manifest_urls:
            raise ValueError('No manifest URLs returned by API')

        if disable_https:
            manifest_urls = [url.replace('https://', 'http://') for url in manifest_urls]

        r = {}
        for url in manifest_urls:
            self.log.debug(f'Trying to download manifest from "{url}"...')
            try:
                r = self.egs.unauth_session.get(url, timeout=10.0)
            except Exception as error:
                self.log.warning(f'Unable to download manifest from "{urlparse(url).netloc}" '
                                 f'(Exception: {error!r}), trying next URL...')
                continue

            if r.status_code == 200:
                manifest_bytes = r.content
                break
            else:
                self.log.warning(f'Unable to download manifest from "{urlparse(url).netloc}" '
                                 f'(status: {r.status_code}), trying next URL...')
        else:
            raise ValueError(f'Unable to get manifest from any CDN URL, last result: {r.status_code} ({r.reason})')

        if sha1(manifest_bytes).hexdigest() != manifest_hash:
            raise ValueError('Manifest sha hash mismatch!')

        return manifest_bytes, base_urls

    def get_uri_manifest(self, uri: str) -> (bytes, List[str]):
        """
        Get the manifest
        :param uri: URI to get the manifest from
        :return:  Manifest data and base URLs
        """
        if uri.startswith('http'):
            r = self.egs.unauth_session.get(uri)
            r.raise_for_status()
            new_manifest_data = r.content
            base_urls = [r.url.rpartition('/')[0]]
        else:
            base_urls = []
            with open(uri, 'rb') as f:
                new_manifest_data = f.read()

        return new_manifest_data, base_urls

    # Check if the UE assets metadata cache must be updated
    def check_for_ue_assets_updates(self, assets_count: int, force_refresh=False) -> None:
        """
        Check if the UE assets metadata cache must be updated
        :param assets_count: assets count from the API
        :param force_refresh: force the refresh of the cache
        """
        self.cache_is_invalidate = False
        cached = self.uevmlfs.get_ue_assets_cache_data()
        cached_assets_count = cached['ue_assets_count']

        date_now = datetime.now().timestamp()
        date_diff = date_now - cached['last_update']

        if not cached_assets_count or cached_assets_count != assets_count:
            self.log.info(f'New assets are available. {assets_count} available VS {cached_assets_count} in cache')
            self.uevmlfs.set_ue_assets_cache_data(last_update=cached['last_update'], ue_assets_count=assets_count)

        if force_refresh or date_diff > self.ue_assets_max_cache_duration:
            self.cache_is_invalidate = True
            self.uevmlfs.set_ue_assets_cache_data(last_update=date_now, ue_assets_count=assets_count)
            if not force_refresh:
                self.log.info(f'Data cache is outdated. Cache age is {date_diff:.1f} s OR {str(timedelta(seconds=date_diff))}')
        else:
            self.log.info(f'Data cache is still valid. Cache age is {str(timedelta(seconds=date_diff))}')

    def clean_exit(self, code=0) -> None:
        """
        Do cleanup, config saving, and quit
        :param code: exit code
        """
        self.uevmlfs.save_config()
        logging.shutdown()
        exit(code)
