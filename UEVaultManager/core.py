# coding: utf-8

import json
import logging
import os

from base64 import b64decode
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha1
from locale import getdefaultlocale
from platform import system
from requests import session
from requests.exceptions import HTTPError, ConnectionError
from urllib.parse import urlparse
from datetime import datetime

from UEVaultManager import __version__
from UEVaultManager.api.egs import EPCAPI
from UEVaultManager.api.lgd import LGDAPI
from UEVaultManager.lfs.egl import EPCLFS
from UEVaultManager.lfs.lgndry import LGDLFS
from UEVaultManager.models.exceptions import *
from UEVaultManager.models.app import *
from UEVaultManager.models.json_manifest import JSONManifest
from UEVaultManager.models.manifest import Manifest
from UEVaultManager.utils.egl_crypt import decrypt_epic_data
from UEVaultManager.utils.env import is_windows_mac_or_pyi
from UEVaultManager.utils.game_workarounds import update_workarounds
from UEVaultManager.utils.selective_dl import games as sdl_games

# ToDo: instead of true/false return values for success/failure actually raise an exception that the CLI/GUI
#  can handle to give the user more details. (Not required yet since there's no GUI so log output is fine)


class LegendaryCore:
  """
  LegendaryCore handles most of the lower level interaction with
  the downloader, lfs, and api components to make writing CLI/GUI
  code easier and cleaner and avoid duplication.
  """
  _egl_version = '11.0.1-14907503+++Portal+Release-Live'

  def __init__(self, override_config=None, timeout=10.0):
    self.log = logging.getLogger('Core')
    self.egs = EPCAPI(timeout=timeout)
    self.lgd = LGDLFS(config_file=override_config)
    self.egl = EPCLFS()
    self.lgdapi = LGDAPI()

    # on non-Windows load the programdata path from config
    if os.name != 'nt':
      self.egl.programdata_path = self.lgd.config.get('UEVaultManager', 'egl_programdata', fallback=None)
      if self.egl.programdata_path and not os.path.exists(self.egl.programdata_path):
        self.log.error(f'Config EGL path ("{self.egl.programdata_path}") is invalid! Disabling sync...')
        self.egl.programdata_path = None
        self.lgd.config.remove_option('UEVaultManager', 'egl_programdata')
        self.lgd.config.remove_option('UEVaultManager', 'egl_sync')
        self.lgd.save_config()

    self.local_timezone = datetime.now().astimezone().tzinfo
    self.language_code, self.country_code = ('en', 'US')

    if locale := self.lgd.config.get('UEVaultManager', 'locale', fallback=getdefaultlocale(('LANG', 'LANGUAGE', 'LC_ALL', 'LC_CTYPE'))[0]):
      try:
        self.language_code, self.country_code = locale.split('-' if '-' in locale else '_')
        self.log.debug(f'Set locale to {self.language_code}-{self.country_code}')
        # adjust egs api language as well
        self.egs.language_code, self.egs.country_code = self.language_code, self.country_code
      except Exception as e:
        self.log.warning(f'Getting locale failed: {e!r}, falling back to using en-US.')
    elif system() != 'Darwin':  # macOS doesn't have a default locale we can query
      self.log.warning('Could not determine locale, falling back to en-US')

    self.update_available = False
    self.force_show_update = False
    self.webview_killswitch = False
    self.logged_in = False

    # UE assets metadata cache properties (Hack LO)
    self.ue_assets_count = 0
    self.ue_assets_update_available = False
    # after 15 days UE assets metadata cache will be invalidated
    self.ue_assets_max_cache_duration = 15 * 24 * 3600

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
      self.lgd.userdata = self.egs.start_session(authorization_code=code)
      return True
    except Exception as e:
      self.log.error(f'Logging in failed with {e!r}, please try again.')
      return False

  def auth_ex_token(self, code) -> bool:
    """
    Handles authentication via exchange token (either retrieved manually or automatically)
    """
    try:
      self.lgd.userdata = self.egs.start_session(exchange_token=code)
      return True
    except Exception as e:
      self.log.error(f'Logging in failed with {e!r}, please try again.')
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
        except Exception as e:
          self.log.debug(f'Decryption with key {data_key} failed with {e!r}')
      else:
        raise ValueError('Decryption of EPIC launcher user information failed.')
    else:
      re_data = json.loads(raw_data)[0]

    if 'Token' not in re_data:
      raise ValueError('No login session in config')
    refresh_token = re_data['Token']
    try:
      self.lgd.userdata = self.egs.start_session(refresh_token=refresh_token)
      return True
    except Exception as e:
      self.log.error(f'Logging in failed with {e!r}, please try again.')
      return False

  def login(self, force_refresh=False) -> bool:
    """
    Attempts logging in with existing credentials.

    raises ValueError if no existing credentials or InvalidCredentialsError if the API return an error
    """
    if not self.lgd.userdata:
      raise ValueError('No saved credentials')
    elif self.logged_in and self.lgd.userdata['expires_at']:
      dt_exp = datetime.fromisoformat(self.lgd.userdata['expires_at'][:-1])
      dt_now = datetime.utcnow()
      td = dt_now - dt_exp

      # if session still has at least 10 minutes left we can re-use it.
      if dt_exp > dt_now and abs(td.total_seconds()) > 600:
        return True
      else:
        self.logged_in = False

    # run update check
    # TODO re-enable this code
    # if self.update_check_enabled():
    if False and self.update_check_enabled():
      try:
        self.check_for_updates()
      except Exception as e:
        self.log.warning(f'Checking for UEVaultManager updates failed: {e!r}')
    else:
      self.apply_lgd_config()

    if self.lgd.userdata['expires_at'] and not force_refresh:
      dt_exp = datetime.fromisoformat(self.lgd.userdata['expires_at'][:-1])
      dt_now = datetime.utcnow()
      td = dt_now - dt_exp

      # if session still has at least 10 minutes left we can re-use it.
      if dt_exp > dt_now and abs(td.total_seconds()) > 600:
        self.log.info('Trying to re-use existing login session...')
        try:
          self.egs.resume_session(self.lgd.userdata)
          self.logged_in = True
          return True
        except InvalidCredentialsError as e:
          self.log.warning(f'Resuming failed due to invalid credentials: {e!r}')
        except Exception as e:
          self.log.warning(f'Resuming failed for unknown reason: {e!r}')
        # If verify fails just continue the normal authentication process
        self.log.info('Falling back to using refresh token...')

    try:
      self.log.info('Logging in...')
      userdata = self.egs.start_session(self.lgd.userdata['refresh_token'])
    except InvalidCredentialsError:
      self.log.error('Stored credentials are no longer valid! Please login again.')
      self.lgd.invalidate_userdata()
      return False
    except (HTTPError, ConnectionError) as e:
      self.log.error(f'HTTP request for login failed: {e!r}, please try again later.')
      return False

    self.lgd.userdata = userdata
    self.logged_in = True
    return True

  def update_check_enabled(self):
    return not self.lgd.config.getboolean('UEVaultManager', 'disable_update_check', fallback=False)

  def update_notice_enabled(self):
    if self.force_show_update:
      return True
    return not self.lgd.config.getboolean('UEVaultManager', 'disable_update_notice', fallback=not is_windows_mac_or_pyi())

  def check_for_updates(self, force=False):

    def version_tuple(v):
      return tuple(map(int, (v.split('.'))))

    cached = self.lgd.get_cached_version()
    version_info = cached['data']
    if force or not version_info or (datetime.now().timestamp() - cached['last_update']) > 24 * 3600:
      version_info = self.lgdapi.get_version_information()
      self.lgd.set_cached_version(version_info)

    web_version = version_info['release_info']['version']
    self.update_available = version_tuple(web_version) > version_tuple(__version__)
    self.apply_lgd_config(version_info)

  def apply_lgd_config(self, version_info=None):
    """Applies configuration options returned by update API"""
    if not version_info:
      version_info = self.lgd.get_cached_version()['data']
    # if cached data is invalid
    if not version_info:
      self.log.debug('No cached UEVaultManager config to apply.')
      return

    if 'egl_config' in version_info:
      self.egs.update_egs_params(version_info['egl_config'])
      self._egl_version = version_info['egl_config'].get('version', self._egl_version)
      for data_key in version_info['egl_config'].get('data_keys', []):
        if data_key not in self.egl.data_keys:
          self.egl.data_keys.append(data_key)
    if game_overrides := version_info.get('game_overrides'):
      update_workarounds(game_overrides)
      if sdl_config := game_overrides.get('sdl_config'):
        # add placeholder for games to fetch from API that aren't hardcoded
        for app_name in sdl_config.keys():
          if app_name not in sdl_games:
            sdl_games[app_name] = None
    if lgd_config := version_info.get('legendary_config'):
      self.webview_killswitch = lgd_config.get('webview_killswitch', False)

  def get_update_info(self):
    return self.lgd.get_cached_version()['data'].get('release_info')

  def get_sdl_data(self, app_name, platform='Windows'):
    if platform not in ('Win32', 'Windows'):
      app_name = f'{app_name}_{platform}'

    if app_name not in sdl_games:
      return None
    # load hardcoded data as fallback
    sdl_data = sdl_games[app_name]
    # get cached data
    cached = self.lgd.get_cached_sdl_data(app_name)
    # check if newer version is available and/or download if necessary
    version_info = self.lgd.get_cached_version()['data']
    latest = version_info.get('game_overrides', {}).get('sdl_config', {}).get(app_name)
    if (not cached and latest) or (cached and latest and latest > cached['version']):
      try:
        sdl_data = self.lgdapi.get_sdl_config(app_name)
        self.log.debug(f'Downloaded SDL data for "{app_name}", version: {latest}')
        self.lgd.set_cached_sdl_data(app_name, latest, sdl_data)
      except Exception as e:
        self.log.warning(f'Downloading SDL data failed with {e!r}')
    elif cached:
      sdl_data = cached['data']
    # return data if available
    return sdl_data

  def update_aliases(self, force=False):
    _aliases_enabled = not self.lgd.config.getboolean('UEVaultManager', 'disable_auto_aliasing', fallback=False)
    if _aliases_enabled and (force or not self.lgd.aliases):
      self.lgd.generate_aliases()

  def get_assets(self, update_assets=False, platform='Windows') -> List[AppAsset]:
    # do not save and always fetch list when platform is overridden
    if not self.lgd.assets or update_assets or platform not in self.lgd.assets:
      # if not logged in, return empty list
      if not self.egs.user:
        return []

      assets = self.lgd.assets.copy() if self.lgd.assets else dict()

      assets.update({platform: [AppAsset.from_egs_json(a) for a in self.egs.get_game_assets(platform=platform)]})

      # only save (and write to disk) if there were changes
      if self.lgd.assets != assets:
        self.lgd.assets = assets

    return self.lgd.assets[platform]

  def get_asset(self, app_name, platform='Windows', update=False) -> AppAsset:
    if update or platform not in self.lgd.assets:
      self.get_assets(update_assets=True, platform=platform)

    try:
      return next(i for i in self.lgd.assets[platform] if i.app_name == app_name)
    except StopIteration:
      raise ValueError

  def asset_valid(self, app_name) -> bool:
    # EGL sync is only supported for Windows titles so this is fine
    return any(i.app_name == app_name for i in self.lgd.assets['Windows'])

  def asset_available(self, game: App, platform='Windows') -> bool:
    # Just say yes for Origin titles
    if game.third_party_store:
      return True

    try:
      asset = self.get_asset(game.app_name, platform=platform)
      return asset is not None
    except ValueError:
      return False

  def get_game(self, app_name, update_meta=False, platform='Windows') -> App:
    if update_meta:
      self.get_asset_list(True, platform=platform)
    return self.lgd.get_game_meta(app_name)

  def get_asset_list(self, update_assets=True, platform='Windows') -> List[App]:
    return self.get_inner_asset_list(update_assets=update_assets, platform=platform)[0]

  # add a parameter to bypass some resource loads if ue asset only are required (Hack LO)
  def get_inner_asset_list(self, update_assets=True, platform='Windows') -> (List[App], Dict[str, List[App]]):
    _ret = []
    _dlc = defaultdict(list)
    meta_updated = False

    # fetch asset information for Windows, all installed platforms, and the specified one
    platforms = {'Windows'}
    platforms |= {platform}

    for _platform in platforms:
      self.get_assets(update_assets=update_assets, platform=_platform)

    if not self.lgd.assets:
      return _ret, _dlc

    assets = {}
    for _platform, _assets in self.lgd.assets.items():
      for _asset in _assets:
        if _asset.app_name in assets:
          assets[_asset.app_name][_platform] = _asset
        else:
          assets[_asset.app_name] = {_platform: _asset}

    fetch_list = []
    apps = {}

    # split asset checking and data grabbing to optimize cache checking (Hack LO)
    valid_items = []
    bypass_count = 0
    for app_name, app_assets in sorted(assets.items()):
      # skip all items that are not UE assets if the --ue-assets-only command line option has been used (Hack LO)
      # if ue_assets_only and all(v.namespace != 'ue' for v in app_assets.values()):
      if app_assets['Windows'].namespace != 'ue':
        self.log.info(f' {app_name} has been bypassed #1')
        bypass_count += 1
        continue

      item = {"name": app_name, "asset": app_assets}
      valid_items.append(item)

    self.ue_assets_count = len(valid_items)

    # check if we must refresh ue asset metadata cache (Hack LO)
    self.check_for_ue_assets_updates()
    force_refresh = self.ue_assets_update_available

    # loop through valid items (Hack LO)
    for libitem in valid_items:
      app_name = libitem["name"]
      app_assets = libitem["asset"]
      self.log.info(f' adding {app_name} / {app_assets["Windows"].namespace} to the list')

      game = self.lgd.get_game_meta(app_name)
      asset_updated = False
      if game:
        asset_updated = any(game.app_version(_p) != app_assets[_p].build_version for _p in app_assets.keys())
        apps[app_name] = game

      if update_assets and (not game or force_refresh or (game and asset_updated)):
        self.log.debug(f'Scheduling metadata update for {app_name}')
        # namespace/catalog item are the same for all platforms, so we can just use the first one
        _ga = next(iter(app_assets.values()))
        fetch_list.append((app_name, _ga.namespace, _ga.catalog_item_id))
        meta_updated = True

    def fetch_asset_meta(args):
      name, namespace, catalog_item_id = args
      eg_meta = self.egs.get_game_info(namespace, catalog_item_id, timeout=10.0)
      app = App(app_name=name, app_title=eg_meta['title'], metadata=eg_meta, asset_infos=assets[name])
      self.lgd.set_game_meta(app.app_name, app)
      apps[name] = app
      # (Hack LO) some items to update could have bypassed
      try:
        still_needs_update.remove(name)
      except Exception as e:
        self.log.warning(f'Removing {name} from the update list failed with {e!r}')
        return False

    # setup and teardown of thread pool takes some time, so only do it when it makes sense.
    still_needs_update = {e[0] for e in fetch_list}
    use_threads = len(fetch_list) > 5
    if fetch_list:
      self.log.info(f'Fetching metadata for {len(fetch_list)} app(s).')
      if use_threads:
        with ThreadPoolExecutor(max_workers=16) as executor:
          executor.map(fetch_asset_meta, fetch_list, timeout=60.0)
    bypass_count = 0

    for app_name, app_assets in sorted(assets.items()):
      # skip all items that are not UE assets if the --ue-assets-only command line option has been used (Hack LO)
      # if ue_assets_only and all(v.namespace != 'ue' for v in app_assets.values()):
      if app_assets['Windows'].namespace != 'ue':
        self.log.info(f' {app_name} has been bypassed #3')
        bypass_count += 1
        continue

      game = apps.get(app_name)
      # retry if metadata is still missing/threaded loading wasn't used
      if not game or app_name in still_needs_update:
        if use_threads:
          self.log.warning(f'Fetching metadata for {app_name} failed, retrying')
        _ga = next(iter(app_assets.values()))
        fetch_asset_meta((app_name, _ga.namespace, _ga.catalog_item_id))
        game = apps[app_name]

      if not any(i['path'] == 'mods' for i in game.metadata.get('categories', [])) and platform in app_assets:
        _ret.append(game)

    self.update_aliases(force=meta_updated)
    if meta_updated:
      self._prune_metadata()

    return _ret, _dlc

  def _prune_metadata(self):
    # compile list of games without assets, then delete their metadata

    for app_name in self.lgd.get_game_app_names():
      self.log.debug(f'Removing old/unused metadata for "{app_name}"')
      self.lgd.delete_game_meta(app_name)

  def get_non_asset_library_items(self, force_refresh=False, skip_ue=True) -> (List[App], Dict[str, List[App]]):
    """
    Gets a list of Games without assets for installation, for instance Games delivered via
    third-party stores that do not have assets for installation

    :param force_refresh: Force a metadata refresh
    :param skip_ue: Ingore Unreal Marketplace entries
    :return: List of Games and DLC that do not have assets
    """
    _ret = []
    _dlc = defaultdict(list)
    # get all the appnames we have to ignore
    ignore = set(i.app_name for i in self.get_assets())

    for libitem in self.egs.get_library_items():
      if libitem['namespace'] == 'ue' and skip_ue:
        continue
      if libitem['appName'] in ignore:
        continue

      game = self.lgd.get_game_meta(libitem['appName'])
      if not game or force_refresh:
        eg_meta = self.egs.get_game_info(libitem['namespace'], libitem['catalogItemId'])
        game = App(app_name=libitem['appName'], app_title=eg_meta['title'], metadata=eg_meta)
        self.lgd.set_game_meta(game.app_name, game)

      if game.is_dlc:
        _dlc[game.metadata['mainGameItem']['id']].append(game)
      elif not any(i['path'] == 'mods' for i in game.metadata.get('categories', [])):
        _ret.append(game)

    # Force refresh to make sure these titles are included in aliasing
    self.update_aliases(force=True)
    return _ret, _dlc

  def get_app_environment(self, app_name) -> dict:
    # get environment overrides from config
    env = dict()
    if 'default.env' in self.lgd.config:
      env |= {k: v for k, v in self.lgd.config['default.env'].items() if v and not k.startswith(';')}
    if f'{app_name}.env' in self.lgd.config:
      env |= {k: v for k, v in self.lgd.config[f'{app_name}.env'].items() if v and not k.startswith(';')}

    return env

  @staticmethod
  def load_manifest(data: bytes) -> Manifest:
    if data[0:1] == b'{':
      return JSONManifest.read_all(data)
    else:
      return Manifest.read_all(data)

  def get_cdn_urls(self, game, platform='Windows'):
    m_api_r = self.egs.get_game_manifest(game.namespace, game.catalog_item_id, game.app_name, platform)

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

  def get_cdn_manifest(self, game, platform='Windows', disable_https=False):
    manifest_urls, base_urls, manifest_hash = self.get_cdn_urls(game, platform)
    if not manifest_urls:
      raise ValueError('No manifest URLs returned by API')

    if disable_https:
      manifest_urls = [url.replace('https://', 'http://') for url in manifest_urls]

    for url in manifest_urls:
      self.log.debug(f'Trying to download manifest from "{url}"...')
      try:
        r = self.egs.unauth_session.get(url, timeout=10.0)
      except Exception as e:
        self.log.warning(f'Unable to download manifest from "{urlparse(url).netloc}" '
                         f'(Exception: {e!r}), trying next URL...')
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

  def get_uri_manifest(self, uri):
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

  def get_delta_manifest(self, base_url, old_build_id, new_build_id):
    """Get optimized delta manifest (doesn't seem to exist for most games)"""
    if old_build_id == new_build_id:
      return None

    r = self.egs.unauth_session.get(f'{base_url}/Deltas/{new_build_id}/{old_build_id}.delta')
    return r.content if r.status_code == 200 else None

  # Check if the UE assets metadata cache must be updated (Hack LO)
  def check_for_ue_assets_updates(self):
    cached = self.lgd.get_ue_assets_cache_data()
    ue_assets_count = cached['ue_assets_count']

    self.ue_assets_update_available = False
    if not ue_assets_count or ue_assets_count != self.ue_assets_count or (datetime.now().timestamp() - cached['last_update']) > self.ue_assets_max_cache_duration:
      ue_assets_count = self.ue_assets_count
      self.lgd.set_ue_assets_cache_data(ue_assets_count=ue_assets_count)
      self.ue_assets_update_available = True

  def exit(self):
    """
    Do cleanup, config saving, and exit.
    """
    self.lgd.save_config()
