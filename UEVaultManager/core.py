# coding=utf-8
"""
Implementation for:
- AppCore: handle most of the lower level interaction with the downloader, lfs, and api components to make writing CLI/GUI code easier and cleaner and avoid duplication.
"""
import datetime
import json
import logging
import os
import shutil
from base64 import b64decode
from hashlib import sha1
from locale import getlocale, LC_CTYPE
from multiprocessing import Queue
from platform import system
from typing import List, Optional
from urllib.parse import urlparse

from requests import session
from requests.exceptions import ConnectionError, HTTPError

import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
# noinspection PyPep8Naming
from UEVaultManager import __version__ as UEVM_version
from UEVaultManager.api.egs import EPCAPI
from UEVaultManager.api.uevm import UEVMAPI
from UEVaultManager.downloader.mp.DLManagerClass import DLManager
from UEVaultManager.lfs.EPCLFSClass import EPCLFS
from UEVaultManager.lfs.UEVMLFSClass import UEVMLFS
from UEVaultManager.lfs.utils import clean_filename, path_join
from UEVaultManager.models.Asset import Asset, InstalledAsset
from UEVaultManager.models.downloading import AnalysisResult, ConditionCheckResult
from UEVaultManager.models.exceptions import InvalidCredentialsError
from UEVaultManager.models.json_manifest import JSONManifest
from UEVaultManager.models.manifest import Manifest
from UEVaultManager.models.types import DateFormat
from UEVaultManager.tkgui.modules.functions import exit_and_clean_windows
from UEVaultManager.tkgui.modules.functions_no_deps import format_size
from UEVaultManager.utils.cli import check_and_create_file, check_and_create_folder
from UEVaultManager.utils.egl_crypt import decrypt_epic_data
from UEVaultManager.utils.env import is_windows_mac_or_pyi


# make some properties of the AppCore class accessible from outside to limit the number of imports needed
def log_info_and_gui_display(message: str) -> None:
    """
    Wrapper to log a message using a log function AND use a DisplayWindows to display the message if the gui is active.
    :param message: message to log.

    Notes:
       To avoid "PicklingError" when using multithreading, this method must still here, at the start of the file and outside the class (WTF ?)
       Do not use self. logger instead of logging.getLogger('Core')
    """
    # self.logger.info(message)
    logging.getLogger('Core').info(message)
    if gui_g.WindowsRef.display_content is not None:
        gui_g.WindowsRef.display_content.display(message)


class AppCore:
    """
    AppCore handles most of the lower level interaction with
    the downloader, lfs, and api components to make writing CLI/GUI
    code easier and cleaner and avoid duplication.
    :param override_config: path to a config file to use instead of the default.
    :param timeout: timeout for the request. Could be a float or a tuple of float (connect timeout, read timeout).
    """
    _egl_version = '11.0.1-14907503+++Portal+Release-Live'

    def __init__(self, override_config=None, timeout=(7, 7)):
        self.timeout = timeout
        self.logger = logging.getLogger('Core')
        self.egs = EPCAPI(timeout=self.timeout)
        self.uevmlfs = UEVMLFS(config_file=override_config)
        self.egl = EPCLFS()
        self.uevm_api = UEVMAPI()

        # on non-Windows load the programdata path from config
        if os.name != 'nt':
            self.egl.programdata_path = self.uevmlfs.config.get('UEVaultManager', 'egl_programdata', fallback=None)
            if self.egl.programdata_path and not os.path.exists(self.egl.programdata_path):
                self.logger.error(f'Config EGL path ("{self.egl.programdata_path}") is invalid! Disabling sync...')
                self.egl.programdata_path = None
                self.uevmlfs.config.remove_option('UEVaultManager', 'egl_programdata')
                self.uevmlfs.save_config()

        self.local_timezone = datetime.datetime.now().astimezone().tzinfo
        self.language_code, self.country_code = ('en', 'US')

        if locale := self.uevmlfs.config.get('UEVaultManager', 'locale', fallback=getlocale(LC_CTYPE)[0]):
            try:
                self.language_code, self.country_code = locale.split('-' if '-' in locale else '_')
                self.logger.debug(f'Set locale to {self.language_code}-{self.country_code}')
                # adjust egs api language as well
                self.egs.language_code, self.egs.country_code = self.language_code, self.country_code
            except Exception as error:
                self.logger.warning(f'Getting locale failed: {error!r}, falling back to using en-US.')
        elif system() != 'Darwin':  # macOS doesn't have a default locale we can query
            self.logger.warning('Could not determine locale, falling back to en-US')

        self.update_available = False
        self.force_show_update = False
        self.webview_killswitch = False
        self.user_is_connected = False

        # UE assets metadata cache properties
        self.ue_assets_count = 0
        # set to True to add print more information during long operations
        self.verbose_mode = False
        # Create a backup of the output file (when using the --output option) suffixed by a timestamp before creating a new file
        self.create_output_backup = True
        # Set the file name (and path) to log issues when an asset is ignored or filtered when running the list or scrap commands
        self.ignored_assets_filename_log = ''
        # Set the file name (and path) to log issues when an asset is not found on the marketplace when running the list or scrap commands
        self.notfound_assets_filename_log = ''
        # Set the file name (and path) to log issues when scanning folder to find assets
        self.scan_assets_filename_log = ''
        # Set the file name (and path) to log scraped assets
        self.scrap_assets_filename_log = ''
        # Create a backup of the log files that store asset analysis suffixed by a timestamp before creating a new file
        self.create_log_backup = True
        # file loggers
        self.ignored_logger = None
        self.notfound_logger = None
        self.scan_assets_logger = None
        self.scrap_asset_logger = None
        self.use_threads = False
        self.thread_executor = None
        self.thread_executor_must_stop = False
        self.engine_version_for_obsolete_assets = gui_g.s.engine_version_for_obsolete_assets
        # self.display_windows= DisplayContentWindow(title='UEVM command output', quit_on_close=True)
        self.display_windows = None
        self.session_ttl: int = 100  # time to live for the current user login session in seconds

    @staticmethod
    def load_manifest(data: bytes) -> Manifest:
        """
        Load a manifest.
        :param data: bytes object to load the manifest from.
        :return: Manifest object.
        """
        if data[0:1] == b'{':
            return JSONManifest.read_all(data)
        else:
            return Manifest.read_all(data)

    @staticmethod
    def check_installation_conditions(analysis: AnalysisResult, folders: [], ignore_space_req: bool = False) -> ConditionCheckResult:
        """
        Check installation conditions.
        :param analysis: analysis result to check.
        :param folders: folders to check free size for.
        :param ignore_space_req: whether to ignore space requirements or not.
        :return: ConditionCheckResult object.
        """
        results = ConditionCheckResult(failures=set(), warnings=set())
        if not isinstance(folders, list):
            folders = [folders]
        for folder in folders:
            if not folder:
                results.failures.add(f'"At least one folder is not defined. Check your config and command options.')
                break
            if not os.path.exists(folder):
                results.failures.add(
                    f'"{folder}" does not exist. Check your config and command options and make sure all necessary disks are available.'
                )
                break
            min_disk_space = analysis.disk_space_delta
            _, _, free = shutil.disk_usage(folder)
            if free < min_disk_space:
                free_gib = free / 1024 ** 3
                required_gib = min_disk_space / 1024 ** 3
                message = f'"{folder}": Potentially not enough available disk space: {free_gib:.02f} GiB < {required_gib:.02f} GiB'
                if ignore_space_req:
                    results.warnings.add(message)
                else:
                    results.failures.add(message)
        return results

    def setup_assets_loggers(self) -> None:
        """
        Setup logging for ignored, not found and bad data assets.
        """

        def create_logger(logger_name: str, filename_log: str):
            """
            Create a logger for ignored, not found and bad data assets.
            :param logger_name: logger name.
            :param filename_log: log file name.
            :return: logger.
            """
            filename_log = filename_log.replace('~/.config', self.uevmlfs.path)
            if check_and_create_file(filename_log):
                handler = logging.FileHandler(filename_log, mode='w')
                handler.setFormatter(formatter)
                logger = logging.Logger(logger_name, 'INFO')
                logger.addHandler(handler)
                logger.info(message)
                return logger
            else:
                self.logger.warning(f'Failed to create logger for file: {filename_log}')
                return None

        formatter = logging.Formatter('%(message)s')
        message = f"-----\n{datetime.datetime.now().strftime(DateFormat.csv)} Log Started\n-----\n"

        if self.ignored_assets_filename_log:
            self.ignored_logger = create_logger('IgnoredAssets', self.ignored_assets_filename_log)
        if self.notfound_assets_filename_log:
            self.notfound_logger = create_logger('NotFoundAssets', self.notfound_assets_filename_log)
        if self.scan_assets_filename_log:
            self.scan_assets_logger = create_logger('ScanAssets', self.scan_assets_filename_log)
        if self.scrap_assets_filename_log:
            self.scrap_asset_logger = create_logger('ScrapAssets', self.scrap_assets_filename_log)

    def auth_sid(self, sid) -> str:
        """
        Handles getting an exchange code from an id.
        :param sid: session id.
        :return: exchange code.
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

        self.logger.error(f'Getting exchange code failed: {r.json()}')
        return ''

    def auth_code(self, code) -> bool:
        """
        Handles authentication via authorization code (either retrieved manually or automatically).
        """
        try:
            self.uevmlfs.userdata = self.egs.start_session(authorization_code=code)
            return True
        except Exception as error:
            self.logger.error(f'Log in failed with {error!r}, please try again.')
            return False

    def auth_ex_token(self, code) -> bool:
        """
        Handles authentication via exchange token (either retrieved manually or automatically).
        """
        try:
            self.uevmlfs.userdata = self.egs.start_session(exchange_token=code)
            return True
        except Exception as error:
            self.logger.error(f'Log in failed with {error!r}, please try again.')
            return False

    def auth_import(self) -> bool:
        """
        Import refresh token from EGL installation and use it to log in.
        :return: True if successful, False otherwise.
        """
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
                    self.logger.debug(f'Decryption with key {data_key} failed with {error!r}')
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
            self.logger.error(f'Logging failed with {error!r}, please try again.')
            return False

    def login(self, force_refresh: bool = False, raise_error: bool = False) -> bool:
        """
        Attempt log in with existing credentials.
        :param force_refresh: whether to force a refresh of the session.
        :param raise_error: whether to raise an exception if login fails.
        :return: True if successful, False otherwise.
        """
        if not self.uevmlfs.userdata:
            if raise_error:
                raise ValueError('No saved credentials')
            else:
                self.user_is_connected = False
                return False
        elif self.user_is_connected and self.uevmlfs.userdata['expires_at']:
            dt_exp = datetime.datetime.fromisoformat(self.uevmlfs.userdata['expires_at'][:-1])
            dt_now = datetime.datetime.now(datetime.UTC)
            td = dt_now.timestamp() - dt_exp.timestamp()
            if td > self.session_ttl:
                return True
            else:
                self.user_is_connected = False

        # run update check
        if self.update_check_enabled():
            try:
                self.check_for_updates()
            except Exception as error:
                self.logger.warning(f'Checking for UEVaultManager updates failed: {error!r}')

        if self.uevmlfs.userdata['expires_at'] and not force_refresh:
            dt_exp = datetime.datetime.fromisoformat(self.uevmlfs.userdata['expires_at'][:-1])
            dt_now = datetime.datetime.now(datetime.UTC)
            td = dt_now.timestamp() - dt_exp.timestamp()

            if td > self.session_ttl:
                self.logger.info('Trying to re-use existing login session...')
                try:
                    self.egs.resume_session(self.uevmlfs.userdata)
                    self.user_is_connected = True
                    return True
                except InvalidCredentialsError as error:
                    self.logger.warning(f'Resuming failed due to invalid credentials: {error!r}')
                except (Exception, ) as error:
                    self.logger.warning(f'Resuming failed for unknown reason: {error!r}')
                # If verify fails just continue the normal authentication process
                self.logger.info('Falling back to using refresh token...')

        try:
            self.logger.info('Logging in...')
            userdata = self.egs.start_session(self.uevmlfs.userdata['refresh_token'])
        except InvalidCredentialsError as error:
            self.logger.warning(f'Resuming failed due to invalid credentials: {error!r}')
            self.uevmlfs.invalidate_userdata()
            return False
        except (Exception, ) as error:
            self.logger.error(f'Connection failed with error : {error!r}')
            return False
        except (HTTPError, ConnectionError) as error:
            self.logger.error(f'HTTP request for log in failed: {error!r}, please try again later.')
            return False

        self.uevmlfs.userdata = userdata
        self.user_is_connected = True
        return True

    def update_check_enabled(self) -> bool:
        """
        Return whether update checks are enabled or not.
        :return: True if update checks are enabled, False otherwise.
        """
        return not self.uevmlfs.config.getboolean('UEVaultManager', 'disable_update_check', fallback=False)

    def update_notice_enabled(self) -> bool:
        """
        Return whether update notices are enabled or not.
        :return: True if update notices are enabled, False otherwise.
        """
        if self.force_show_update:
            return True
        return not self.uevmlfs.config.getboolean('UEVaultManager', 'disable_update_notice', fallback=not is_windows_mac_or_pyi())

    def check_for_updates(self, force=False) -> None:
        """
        Check for updates and sets the update_available flag accordingly.
        :param force: force update check.
        """

        def version_tuple(v):
            """
            Convert a version string to a tuple of ints.
            :param v: version string.
            :return:  tuple of int.
            """
            return tuple(map(int, (v.split('.'))))

        cached = self.uevmlfs.get_online_version_saved()
        version_info = cached['data']
        if force or not version_info or (datetime.datetime.now().timestamp() - cached['last_update']) > 24 * 3600:
            version_info = self.uevm_api.get_online_version_information()
            self.uevmlfs.set_online_version_saved(version_info)

        web_version = version_info['version']
        self.update_available = version_tuple(web_version) > version_tuple(UEVM_version)

    def get_egl_version(self):
        """
        return the egl version.
        :return:
        """
        return self._egl_version

    def get_update_info(self) -> dict:
        """
        Return update info dict.
        :return: update info dict.
        """
        return self.uevmlfs.get_online_version_saved()['data']

    def is_installed(self, app_name: str) -> bool:
        """
        Return whether an asset is installed.
        :param app_name: asset name to check.
        :return: True if asset is installed, False otherwise.
        """
        return self.uevmlfs.get_installed_asset(app_name) is not None

    def get_installed_manifest(self, app_name):
        """
        Get the installed manifest.
        :param app_name: asset name to get the installed manifest for.
        :return:
        """
        installed_asset = self.uevmlfs.get_installed_asset(app_name)
        old_bytes = self.uevmlfs.load_manifest(app_name, installed_asset.version, installed_asset.platform)
        return old_bytes, installed_asset.base_urls

    def asset_obj_from_json(self, app_name: str) -> Optional[Asset]:
        """
        return an "item" like for compatibilty with "old" methods .
        :param app_name: asset name to get the asset object for.
        :return: Asset object.
        """
        asset_data, _ = self.uevmlfs.get_asset(app_name)
        if asset_data:
            return Asset.from_json(asset_data)  # create an object from the Asset class using the json data
        return None

    def get_cdn_urls(self, item, platform: str = 'Windows'):
        """
        Get the CDN URLs.
        :param item: item to get the CDN URLs for.
        :param platform: platform to get the CDN URLs for.
        :return: list of CDN URLs.
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

    def get_cdn_manifest(self, item, platform: str = 'Windows', disable_https=False):
        """
        Get the CDN manifest.
        :param item: item to get the CDN manifest for.
        :param platform: platform to get the CDN manifest for.
        :param disable_https: disable HTTPS for the manifest URLs.
        :return: tuple (manifest data, base URLs, request status code).
        """
        manifest_urls, base_urls, manifest_hash = self.get_cdn_urls(item, platform)
        if not manifest_urls:
            raise ValueError('No manifest URLs returned by API')

        if disable_https:
            manifest_urls = [url.replace('https://', 'http://') for url in manifest_urls]

        r = {}
        for url in manifest_urls:
            self.logger.debug(f'Trying to download manifest from "{url}"...')
            try:
                r = self.egs.unauth_session.get(url, timeout=self.timeout)
            except Exception as error:
                self.logger.warning(f'Failed to download manifest from "{urlparse(url).netloc}" (Exception: {error!r}), trying next URL...')
                continue

            if r.status_code == 200:
                manifest_bytes = r.content
                break
            else:
                self.logger.warning(f'Failed to download manifest from "{urlparse(url).netloc}" (status: {r.status_code}), trying next URL...')
        else:
            raise ValueError(f'Failed to get manifest from any CDN URL, last result: {r.status_code} ({r.reason})')

        if sha1(manifest_bytes).hexdigest() != manifest_hash:
            raise ValueError('Manifest sha hash mismatch!')

        return manifest_bytes, base_urls, r.status_code

    def get_uri_manifest(self, uri: str) -> (bytes, List[str]):
        """
        Get the manifest.
        :param uri: uRI to get the manifest from.
        :return:  Manifest data and base URLs.
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

    def prepare_download(
        self,
        base_asset: Asset,  # contains generic info of the base asset for all releases, NOT the selected release
        release_name: str,
        release_title: str,
        download_folder: str = '',
        install_folder: str = '',
        no_resume: bool = False,
        platform: str = 'Windows',
        max_shm: int = 0,
        max_workers: int = 0,
        dl_optimizations: bool = False,
        override_manifest: str = '',
        override_old_manifest: str = '',
        override_base_url: str = '',
        status_queue: Queue = None,
        reuse_last_install: bool = False,
        disable_patching: bool = False,
        file_prefix_filter: list = None,
        file_exclude_filter: list = None,
        file_install_tag: list = None,
        preferred_cdn: str = None,
        disable_https: bool = False
    ) -> (DLManager, AnalysisResult, InstalledAsset):
        """
        Prepare a download.
        :param base_asset: "base" asset to prepare the download for, not the selected release.
        :param release_name: release name prepare the download for.
        :param release_title: release title prepare the download for.
        :param download_folder: folder to download the asset to.
        :param install_folder: base folder to install the asset to.
        :param platform: platform to prepare the download for.
        :param no_resume: avoid to resume. Force a new download.
        :param max_shm: maximum amount of shared memory to use.
        :param max_workers: maximum number of workers to use.
        :param dl_optimizations: download optimizations.
        :param override_manifest: override the manifest.
        :param override_old_manifest: override the old manifest.
        :param override_base_url: override the base URL.
        :param reuse_last_install: update previous installation.
        :param disable_patching: disable patching.
        :param status_queue: status queue to send status updates to.
        :param file_prefix_filter: file prefix filter.
        :param file_exclude_filter: file exclude filter.
        :param file_install_tag: file install tag.
        :param preferred_cdn: preferred CDN.
        :param disable_https: disable HTTPS. For LAN installs only.
        :return: (DLManager object, AnalysisResult object, InstalledAsset object).
        """
        old_manifest = None
        egl_guid = ''

        # load old manifest if we have one
        if override_old_manifest:
            log_info_and_gui_display(f'Overriding old manifest with "{override_old_manifest}"')
            old_bytes, _ = self.get_uri_manifest(override_old_manifest)
            old_manifest = self.load_manifest(old_bytes)
        elif not disable_patching and not no_resume and self.is_installed(release_name):
            old_bytes, _base_urls = self.get_installed_manifest(release_name)
            if _base_urls and not base_asset.base_urls:
                base_asset.base_urls = _base_urls
            if not old_bytes:
                self.logger.error(f'Could not load old manifest, patching will not work!')
            else:
                old_manifest = self.load_manifest(old_bytes)

        base_urls = base_asset.base_urls

        # The EGS client uses plaintext HTTP by default for the purposes of enabling simple DNS based
        # CDN redirection to a (local) cache.
        disable_https = disable_https or self.uevmlfs.config.getboolean('UEVaultManager', 'disable_https', fallback=False)

        if override_manifest:
            log_info_and_gui_display(f'Overriding manifest with "{override_manifest}"')
            new_manifest_data, _base_urls = self.get_uri_manifest(override_manifest)
            # if override manifest has a base URL use that instead
            if _base_urls:
                base_urls = _base_urls
        else:
            new_manifest_data, base_urls, status_code = self.get_cdn_manifest(base_asset, platform, disable_https=disable_https)
            # overwrite base urls in metadata with current ones to avoid using old/dead CDNs
            base_asset.base_urls = base_urls

        if not new_manifest_data:
            message = f'Manifest data is empty for "{release_name}". Could be a timeout or an issue with the connection.'
            raise ValueError(message)

        log_info_and_gui_display('Parsing game manifest...')
        manifest = self.load_manifest(new_manifest_data)
        self.logger.debug(f'Base urls: {base_urls}')
        # save manifest with version name as well for testing/downgrading/etc.
        manifest_filename = self.uevmlfs.save_manifest(release_name, new_manifest_data, version=manifest.meta.build_version, platform=platform)

        # make sure donwnload folder actually exists (but do not create asset folder)
        if not check_and_create_folder(download_folder):
            log_info_and_gui_display(f'"{download_folder}" did not exist, it has been created.')
        if not os.access(download_folder, os.W_OK):
            raise PermissionError(f'No write access to "{download_folder}"')

        # reuse existing installation's directory
        installed_asset = self.uevmlfs.get_installed_asset(release_name)
        if reuse_last_install and installed_asset:
            install_path = installed_asset.install_path
            egl_guid = installed_asset.egl_guid
        else:
            # asset are always installed in the 'Content' sub folder
            # NO we don't want to store "content" in the "install path"
            # install_path = path_join(install_folder, 'Content') if install_folder  else ''
            install_path = install_folder

        # check for write access on the installation path or its parent directory if it doesn't exist yet
        if install_path:
            log_info_and_gui_display(f'Install path: {install_path}')
            if not check_and_create_folder(install_path):
                log_info_and_gui_display(f'"{install_path}" did not exist, it has been created.')
            if not os.access(install_path, os.W_OK):
                raise PermissionError(f'No write access to "{install_path}"')

        if not no_resume:
            filename = clean_filename(f'{release_name}.resume')
            resume_file = path_join(self.uevmlfs.tmp_folder, filename)
        else:
            resume_file = None

        # Use user-specified base URL or preferred CDN first, otherwise fall back to
        # EGS's behaviour of just selecting the first CDN in the list.
        base_url = None
        if override_base_url:
            log_info_and_gui_display(f'Overriding base URL with "{override_base_url}"')
            base_url = override_base_url
        elif preferred_cdn or (preferred_cdn := self.uevmlfs.config.get('UEVaultManager', 'preferred_cdn', fallback=None)):
            for url in base_urls:
                if preferred_cdn in url:
                    base_url = url
                    break
            else:
                self.logger.warning(f'Preferred CDN "{preferred_cdn}" unavailable, using default selection.')
        # Use first, fail if none known
        if not base_url:
            if not base_urls:
                raise ValueError('No base URLs found, please try again.')
            base_url = base_urls[0]

        if disable_https:
            base_url = base_url.replace('https://', 'http://')

        self.logger.debug(f'Using base URL: {base_url}')
        scheme, cdn_host = base_url.split('/')[0:3:2]
        log_info_and_gui_display(f'Selected CDN: {cdn_host} ({scheme.strip(":")})')

        if not max_shm:
            max_shm = self.uevmlfs.config.getint('UEVaultManager', 'max_memory', fallback=2048)

        if dl_optimizations:
            log_info_and_gui_display('Download order optimizations are enabled.')
            process_opt = True
        else:
            process_opt = False

        if not max_workers:
            max_workers = self.uevmlfs.config.getint('UEVaultManager', 'max_workers', fallback=0)

        download_manager = DLManager(
            download_dir=download_folder,
            base_url=base_url,
            resume_file=resume_file,
            status_q=status_queue,
            max_shared_memory=max_shm * 1024 * 1024,
            max_workers=max_workers,
            timeout=self.timeout,
            trace_func=log_info_and_gui_display,
        )
        installed_asset = self.uevmlfs.get_installed_asset(release_name)
        if installed_asset is None:
            # create a new installed asset
            installed_asset = InstalledAsset(app_name=release_name, title=release_title)
        # update the installed asset
        installed_asset.version = manifest.meta.build_version
        installed_asset.base_urls = base_urls
        installed_asset.egl_guid = egl_guid
        installed_asset.manifest_path = override_manifest if override_manifest else manifest_filename
        installed_asset.platform = platform
        installed_asset.catalog_item_id = base_asset.catalog_item_id
        already_installed = install_path and install_path in installed_asset.installed_folders
        analyse_res = download_manager.run_analysis(
            manifest=manifest,
            old_manifest=old_manifest,
            patch=not disable_patching,
            resume=not no_resume,
            file_prefix_filter=file_prefix_filter,
            file_exclude_filter=file_exclude_filter,
            file_install_tag=file_install_tag,
            processing_optimization=process_opt,
            already_installed=already_installed
        )
        if install_path:
            # will add install_path to the installed_folders list after checking if it is not already in it
            installed_asset.install_path = install_path
        installed_asset.install_size = analyse_res.install_size
        return download_manager, analyse_res, installed_asset

    def clean_exit(self, code=0) -> None:
        """
        Do cleanup, config saving, and quit.
        :param code: exit code.
        """
        self.uevmlfs.save_config()
        logging.shutdown()
        exit_and_clean_windows(code)

    def open_manifest_file(self, file_path: str) -> dict:
        """
        Open a manifest file and return its data.
        :param file_path: path to the manifest file.
        :return: manifest data.
        """
        try:
            with open(file_path, 'rb') as file:
                manifest_data = file.read()
        except FileNotFoundError:
            self.logger.warning(f'The file {file_path} does not exist.')
            return {}
        manifest_info = {}
        manifest = self.load_manifest(manifest_data)
        manifest_info['app_name'] = manifest.meta.app_name

        # file and chunk count
        manifest_info['num_files'] = manifest.file_manifest_list.count
        manifest_info['num_chunks'] = manifest.chunk_data_list.count
        # total file size
        total_size = sum(fm.file_size for fm in manifest.file_manifest_list.elements)
        file_size = format_size(total_size)
        manifest_info['file_size'] = file_size
        manifest_info['disk_size'] = total_size
        # total chunk size
        total_size = sum(c.file_size for c in manifest.chunk_data_list.elements)
        chunk_size = format_size(total_size)
        manifest_info['chunk_size'] = chunk_size
        manifest_info['download_size'] = total_size
        return manifest_info
