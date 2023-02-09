#!/usr/bin/env python
# coding: utf-8

import argparse
import csv
import json
import subprocess
import webbrowser
import logging
import os

from collections import namedtuple
from logging.handlers import QueueListener
from multiprocessing import freeze_support, Queue as MPQueue
from platform import platform
from sys import exit, stdout, platform as sys_platform

from UEVaultManager import __version__, __codename__
from UEVaultManager.core import LegendaryCore
from UEVaultManager.models.exceptions import InvalidCredentialsError
from UEVaultManager.utils.custom_parser import HiddenAliasSubparsersAction

# todo custom formatter for cli logger (clean info, highlighted error/warning)
logging.basicConfig(format='[%(name)s] %(levelname)s: %(message)s', level=logging.INFO)
logger = logging.getLogger('cli')


class UEVaultManagerCLI:

    def __init__(self, override_config=None, api_timeout=None):
        self.core = LegendaryCore(override_config, timeout=api_timeout)
        self.logger = logging.getLogger('cli')
        self.logging_queue = None

    def setup_threaded_logging(self):
        self.logging_queue = MPQueue(-1)
        shandler = logging.StreamHandler()
        sformatter = logging.Formatter('[%(name)s] %(levelname)s: %(message)s')
        shandler.setFormatter(sformatter)
        ql = QueueListener(self.logging_queue, shandler)
        ql.start()
        return ql

    def _resolve_aliases(self, name):
        # make sure aliases exist if not yet created
        self.core.update_aliases(force=False)
        name = name.strip()
        # resolve alias (if any) to real app name
        return self.core.lgd.config.get(section='UEVaultManager.aliases', option=name, fallback=self.core.lgd.aliases.get(name.lower(), name))

    @staticmethod
    def _print_json(data, pretty=False):
        if pretty:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            print(json.dumps(data))

    def auth(self, args):
        if args.auth_delete:
            self.core.lgd.invalidate_userdata()
            logger.info('User data deleted.')
            return

        try:
            logger.info('Testing existing login data if present...')
            if self.core.login():
                logger.info(
                    'Stored credentials are still valid, if you wish to switch to a different '
                    'account, run "UEVaultManager auth --delete" and try again.'
                )
                return
        except ValueError:
            pass
        except InvalidCredentialsError:
            logger.error('Stored credentials were found but were no longer valid. Continuing with login...')
            self.core.lgd.invalidate_userdata()

        # Force an update check and notice in case there are API changes
        self.core.check_for_updates(force=True)
        self.core.force_show_update = True

        if args.import_egs_auth:
            logger.info('Importing login session from the Epic Launcher...')
            try:
                if self.core.auth_import():
                    logger.info('Successfully imported login session from EGS!')
                    logger.info(f'Now logged in as user "{self.core.lgd.userdata["displayName"]}"')
                    return
                else:
                    logger.warning('Login session from EGS seems to no longer be valid.')
                    exit(1)
            except Exception as e:
                logger.error(f'No EGS login session found, please login manually. (Exception: {e!r})')
                exit(1)

        exchange_token = ''
        auth_code = ''
        if not args.auth_code and not args.session_id:
            # only import here since pywebview import is slow
            from UEVaultManager.utils.webview_login import webview_available, do_webview_login

            if not webview_available or args.no_webview or self.core.webview_killswitch:
                # unfortunately the captcha stuff makes a complete CLI login flow kinda impossible right now...
                print('Please login via the epic web login!')
                url = 'https://legendary.gl/epiclogin'
                webbrowser.open(url)
                print(f'If the web page did not open automatically, please manually open the following URL: {url}')
                auth_code = input('Please enter the "authorizationCode" value from the JSON response: ')
                auth_code = auth_code.strip()
                if auth_code[0] == '{':
                    tmp = json.loads(auth_code)
                    auth_code = tmp['authorizationCode']
                else:
                    auth_code = auth_code.strip('"')
            else:
                if do_webview_login(callback_code=self.core.auth_ex_token):
                    logger.info(f'Successfully logged in as "{self.core.lgd.userdata["displayName"]}" via WebView')
                else:
                    logger.error('WebView login attempt failed, please see log for details.')
                return
        elif args.session_id:
            exchange_token = self.core.auth_sid(args.session_id)
        elif args.auth_code:
            auth_code = args.auth_code
        elif args.ex_token:
            exchange_token = args.ex_token

        if not exchange_token and not auth_code:
            logger.fatal('No exchange token/authorization code, cannot login.')
            return

        if exchange_token and self.core.auth_ex_token(exchange_token):
            logger.info(f'Successfully logged in as "{self.core.lgd.userdata["displayName"]}"')
        elif auth_code and self.core.auth_code(auth_code):
            logger.info(f'Successfully logged in as "{self.core.lgd.userdata["displayName"]}"')
        else:
            logger.error('Login attempt failed, please see log for details.')

    def list_assets(self, args):
        logger.info('Logging in...')
        if not self.core.login():
            logger.error('Login failed, cannot continue!')
            exit(1)

        if args.force_refresh:
            logger.info('Refreshing asset list, this may take a while...')
        else:
            logger.info('Getting asset list... (this may take a while)')

        # (Hack LO) add ue_assets_only argument
        items, dlc_list = self.core.get_inner_asset_list()
        # Get information for games that cannot be installed through UEVaultManager (yet), such
        # as games that have to be activated on and launched through Origin.
        if args.include_noasset:
            na_games, na_dlcs = self.core.get_non_asset_library_items(skip_ue=not args.include_ue)
            items.extend(na_games)

        # sort games and dlc by name
        items = sorted(items, key=lambda x: x.app_title.lower())

        # add some metadata in the returned list og "games" for ue only assets (Hack LO)
        if args.ue_assets_only:
            dummy_text = "dummy_text"
            # output with extended info
            if args.csv or args.tsv:
                writer = csv.writer(stdout, dialect='excel-tab' if args.tsv else 'excel', lineterminator='\n')
                writer.writerow(
                    [
                        # dans les infos
                        'App name', 'App title', 'Asset_id', 'Image', 'Url', 'UE Version', 'compatible Versions', 'Review', 'Vendeur', 'Description',
                        'Categorie', 'Prix', 'uid', 'Date Creation', 'Date Updated', 'Status'
                        # calculés lors de l'ajout
                        , 'Date Ajout', 'En Promo', 'Ancien Prix'
                        # Complétés par l'utilisateur
                        , 'Emplacement', 'A Acheter', 'Test', 'Avis', 'Remarque', 'Commentaire', 'Dossier Test', 'Dossier Asset', 'Alternative'
                    ]
                )
                for game in items:
                    metadata = game.metadata
                    asset_id = game.asset_infos['Windows'].asset_id
                    uid = metadata["id"]
                    separator = ','
                    tmp_list = [separator.join(item.get('compatibleApps')) for item in metadata["releaseInfo"]]
                    compatible_versions = separator.join(tmp_list)

                    # the following methods always return an empty vamue due to an obsolete API call:
                    # TODO: find a better way to get this data (marketplace web scrapping ?)
                    price = self.core.egs.get_assets_price(uid)
                    review = self.core.egs.get_assets_review(asset_id)

                    print(f'price {price} review {review}')
                    writer.writerow(
                        (
                            # dans les infos
                            game.app_name  # 'App name'
                            , game.app_title  # 'App title'
                            , asset_id  # 'asset_id'
                            , metadata["keyImages"][2]["url"]  # 'Image' with 488 height
                            , f'https://www.unrealengine.com/marketplace/en-US/product/{asset_id}'  # 'Url'
                            , game.app_version(args.platform)  # 'UE Version'
                            , compatible_versions  # compatible_versions
                            , review  # 'Review'
                            , metadata["developer"]  # 'Vendeur'
                            , metadata["description"]  # 'Description'
                            , metadata["categories"][0]['path']  # 'Categorie'
                            , price  # 'Prix'
                            , uid  # 'uid'
                            , metadata["creationDate"]  # 'Date creation'
                            , metadata["lastModifiedDate"]  # 'Date MAJ'
                            , metadata["status"]  # 'status'

                            # calculé lors de l'ajout
                            , dummy_text  # 'Date Ajout'
                            , dummy_text  # 'En Promo'
                            , dummy_text  # 'Ancien Prix'

                            # complétés par l'utilisateur
                            , ''  # 'Emplacement'
                            , ''  # 'A Acheter'
                            , ''  # 'Test
                            , ''  # 'Avis'
                            , ''  # 'Remarque'
                            , ''  # 'Commentaire'
                            , ''  # 'Dossier Test'
                            , ''  # 'Dossier Asset'
                            , ''  # 'Alternative'
                        )
                    )
                return

            if args.json:
                _out = []
                for game in items:
                    _j = vars(game)
                    _j['dlcs'] = [vars(dlc) for dlc in dlc_list[game.catalog_item_id]]
                    _out.append(_j)

            print('\nAvailable UE Assets:')
            for game in items:
                version = game.app_version(args.platform)
                print(f' * {game.app_title.strip()} (App name: {game.app_name} | Version: {version})')

            print(f'\nTotal: {len(items)}')

        else:
            # standard output
            if args.csv or args.tsv:
                writer = csv.writer(stdout, dialect='excel-tab' if args.tsv else 'excel', lineterminator='\n')
                writer.writerow(['App name', 'App title', 'Version', 'Is DLC'])
                for game in items:
                    writer.writerow((game.app_name, game.app_title, game.app_version(args.platform), False))
                    for dlc in dlc_list[game.catalog_item_id]:
                        writer.writerow((dlc.app_name, dlc.app_title, dlc.app_version(args.platform), True))
                return

            if args.json:
                _out = []
                for game in items:
                    _j = vars(game)
                    _j['dlcs'] = [vars(dlc) for dlc in dlc_list[game.catalog_item_id]]
                    _out.append(_j)

                return self._print_json(_out, args.pretty_json)

            print('\nAvailable Assets:')
            for game in items:
                version = game.app_version(args.platform)
                print(f' * {game.app_title.strip()} (App name: {game.app_name} | Version: {version})')
                # Games that "require" launching through EGL/UEVaultManager, but have to be installed and managed through
                # a third-party application (such as Origin).
                if not version:
                    _store = game.third_party_store
                    if _store == 'Origin':
                        print(
                            f'  - This game has to be activated, installed, and launched via Origin, use '
                            f'"UEVaultManager launch --origin {game.app_name}" to activate and/or run the game.'
                        )
                    elif _store:
                        print(f'  ! This game has to be installed through a third-party store ({_store}, not supported)')
                    else:
                        print('  ! No version information (unknown cause)')
                # Games that have assets, but only require a one-time activation before they can be independently installed
                # via a third-party platform (e.g. Uplay)
                if game.partner_link_type:
                    _type = game.partner_link_type
                    if _type == 'ubisoft':
                        print(
                            '  - This game can be activated directly on your Ubisoft account and does not require '
                            'UEVaultManager to install/run. Use "UEVaultManager activate --uplay" and follow the instructions.'
                        )
                    else:
                        print(f'  ! This app requires linking to a third-party account (name: "{_type}", not supported)')

                for dlc in dlc_list[game.catalog_item_id]:
                    print(f'  + {dlc.app_title} (App name: {dlc.app_name} | Version: {dlc.app_version(args.platform)})')
                    if not dlc.app_version(args.platform):
                        print(f'   ! This DLC is either included in the base game, or not available for {args.platform}')

            print(f'\nTotal: {len(items)}')

    def list_files(self, args):
        if args.platform:
            args.force_download = True

        if not args.override_manifest and not args.app_name:
            print('You must provide either a manifest url/path or app name!')
            return
        elif args.app_name:
            args.app_name = self._resolve_aliases(args.app_name)

        # check if we even need to log in
        if args.override_manifest:
            logger.info(f'Loading manifest from "{args.override_manifest}"')
            manifest_data, _ = self.core.get_uri_manifest(args.override_manifest)
        else:
            logger.info(f'Logging in and downloading manifest for {args.app_name}')
            if not self.core.login():
                logger.error('Login failed! Cannot continue with download process.')
                exit(1)
            game = self.core.get_item(args.app_name, update_meta=True)
            if not game:
                logger.fatal(f'Could not fetch metadata for "{args.app_name}" (check spelling/account ownership)')
                exit(1)
            manifest_data, _ = self.core.get_cdn_manifest(game, platform=args.platform)

        manifest = self.core.load_manifest(manifest_data)
        files = sorted(manifest.file_manifest_list.elements, key=lambda a: a.filename.lower())

        if args.install_tag:
            files = [fm for fm in files if args.install_tag in fm.install_tags]

        if args.hashlist:
            for fm in files:
                print(f'{fm.hash.hex()} *{fm.filename}')
        elif args.csv or args.tsv:
            writer = csv.writer(stdout, dialect='excel-tab' if args.tsv else 'excel', lineterminator='\n')
            writer.writerow(['path', 'hash', 'size', 'install_tags'])
            writer.writerows((fm.filename, fm.hash.hex(), fm.file_size, '|'.join(fm.install_tags)) for fm in files)
        elif args.json:
            _files = [
                dict(filename=fm.filename, sha_hash=fm.hash.hex(), install_tags=fm.install_tags, file_size=fm.file_size, flags=fm.flags)
                for fm in files
            ]
            return self._print_json(_files, args.pretty_json)
        else:
            install_tags = set()
            for fm in files:
                print(fm.filename)
                for t in fm.install_tags:
                    install_tags.add(t)
            if install_tags:
                # use the log output so this isn't included when piping file list into file
                logger.info(f'Install tags: {", ".join(sorted(install_tags))}')

    def status(self, args):
        if not args.offline:
            try:
                if not self.core.login():
                    logger.error('Log in failed!')
                    exit(1)
            except ValueError:
                pass
            # if automatic checks are off force an update here
            self.core.check_for_updates(force=True)

        if not self.core.lgd.userdata:
            user_name = '<not logged in>'
            args.offline = True
        else:
            user_name = self.core.lgd.userdata['displayName']

        games_available = len(self.core.get_asset_list(update_assets=not args.offline))
        if args.json:
            return self._print_json(dict(account=user_name, games_available=games_available, config_directory=self.core.lgd.path), args.pretty_json)

        print(f'Epic account: {user_name}')
        print(f'Assets available: {games_available}')
        print(f'Config directory: {self.core.lgd.path}')
        print(f'Platform (System): {platform()} ({os.name})')
        print(f'\nUEVaultManager version: {__version__} - "{__codename__}"')
        print(f'Update available: {"yes" if self.core.update_available else "no"}')
        if self.core.update_available:
            if update_info := self.core.get_update_info():
                print(f'- New version: {update_info["version"]} - "{update_info["name"]}"')
                print(f'- Release summary:\n{update_info["summary"]}\n- Release URL: {update_info["gh_url"]}')
                if update_info['critical']:
                    print('! This update is recommended as it fixes major issues.')
            # prevent update message on close
            self.core.update_available = False

    def info(self, args):
        name_or_path = args.app_name_or_manifest
        app_name = manifest_uri = None
        if os.path.exists(name_or_path) or name_or_path.startswith('http'):
            manifest_uri = name_or_path
        else:
            app_name = self._resolve_aliases(name_or_path)

        if not args.offline and not manifest_uri:
            try:
                if not self.core.login():
                    logger.error('Log in failed!')
                    exit(1)
            except ValueError:
                pass

        # lists that will be printed or turned into JSON data
        info_items = dict(game=list(), manifest=list(), install=list())
        InfoItem = namedtuple('InfoItem', ['name', 'json_name', 'value', 'json_value'])

        game = self.core.get_item(app_name, update_meta=not args.offline, platform=args.platform)
        if game and not self.core.asset_available(game, platform=args.platform):
            logger.warning(
                f'Asset information for "{game.app_name}" is missing, this may be due to the game '
                f'not being available on the selected platform or currently logged-in account.'
            )
            args.offline = True

        manifest_data = None
        entitlements = None
        # load installed manifest or URI
        if args.offline or manifest_uri:
            if manifest_uri and manifest_uri.startswith('http'):
                r = self.core.egs.unauth_session.get(manifest_uri)
                r.raise_for_status()
                manifest_data = r.content
            elif manifest_uri and os.path.exists(manifest_uri):
                with open(manifest_uri, 'rb') as f:
                    manifest_data = f.read()
            else:
                logger.info('Game not installed and offline mode enabled, cannot load manifest.')
        elif game:
            entitlements = self.core.egs.get_user_entitlements()
            egl_meta = self.core.egs.get_asset_info(game.namespace, game.catalog_item_id)
            game.metadata = egl_meta
            # Get manifest if asset exists for current platform
            if args.platform in game.asset_infos:
                manifest_data, _ = self.core.get_cdn_manifest(game, args.platform)

        if game:
            game_infos = info_items['game']
            game_infos.append(InfoItem('App name', 'app_name', game.app_name, game.app_name))
            game_infos.append(InfoItem('Title', 'title', game.app_title, game.app_title))
            game_infos.append(InfoItem('Latest version', 'version', game.app_version(args.platform), game.app_version(args.platform)))
            all_versions = {k: v.build_version for k, v in game.asset_infos.items()}
            game_infos.append(InfoItem('All versions', 'platform_versions', all_versions, all_versions))
            # Cloud save support for Mac and Windows
            game_infos.append(
                InfoItem(
                    'Cloud saves supported', 'cloud_saves_supported', game.supports_cloud_saves or game.supports_mac_cloud_saves,
                                                                      game.supports_cloud_saves or game.supports_mac_cloud_saves
                )
            )
            cs_dir = None
            if game.supports_cloud_saves:
                cs_dir = game.metadata['customAttributes']['CloudSaveFolder']['value']
            game_infos.append(InfoItem('Cloud save folder (Windows)', 'cloud_save_folder', cs_dir, cs_dir))

            cs_dir = None
            if game.supports_mac_cloud_saves:
                cs_dir = game.metadata['customAttributes']['CloudSaveFolder_MAC']['value']
            game_infos.append(InfoItem('Cloud save folder (Mac)', 'cloud_save_folder_mac', cs_dir, cs_dir))

            game_infos.append(InfoItem('Is DLC', 'is_dlc', game.is_dlc, game.is_dlc))

            external_activation = game.third_party_store or game.partner_link_type
            game_infos.append(InfoItem('Activates on external platform', 'external_activation', external_activation or 'No', external_activation))

            # Find custom launch options, if available
            launch_options = []
            i = 1
            while f'extraLaunchOption_{i:03d}_Name' in game.metadata['customAttributes']:
                launch_options.append(
                    (
                        game.metadata['customAttributes'][f'extraLaunchOption_{i:03d}_Name']['value'],
                        game.metadata['customAttributes'][f'extraLaunchOption_{i:03d}_Args']['value']
                    )
                )
                i += 1

            if launch_options:
                human_list = []
                json_list = []
                for opt_name, opt_cmd in sorted(launch_options):
                    human_list.append(f'Name: "{opt_name}", Parameters: {opt_cmd}')
                    json_list.append(dict(name=opt_name, parameters=opt_cmd))
                game_infos.append(InfoItem('Extra launch options', 'launch_options', human_list, json_list))
            else:
                game_infos.append(InfoItem('Extra launch options', 'launch_options', None, []))

            # list all owned DLC based on entitlements
            if entitlements and not game.is_dlc:
                owned_entitlements = {i['entitlementName'] for i in entitlements}
                owned_app_names = {g.app_name for g in self.core.get_assets(args.platform)}
                owned_dlc = []
                for dlc in game.metadata.get('dlcItemList', []):
                    installable = dlc.get('releaseInfo', None)
                    if dlc['entitlementName'] in owned_entitlements:
                        owned_dlc.append((installable, None, dlc['title'], dlc['id']))
                    elif installable:
                        app_name = dlc['releaseInfo'][0]['appId']
                        if app_name in owned_app_names:
                            owned_dlc.append((installable, app_name, dlc['title'], dlc['id']))

                if owned_dlc:
                    human_list = []
                    json_list = []
                    for installable, app_name, title, dlc_id in owned_dlc:
                        json_list.append(dict(app_name=app_name, title=title, installable=installable, id=dlc_id))
                        if installable:
                            human_list.append(f'App name: {app_name}, Title: "{title}"')
                        else:
                            human_list.append(f'Title: "{title}" (no installation required)')
                    game_infos.append(InfoItem('Owned DLC', 'owned_dlc', human_list, json_list))
                else:
                    game_infos.append(InfoItem('Owned DLC', 'owned_dlc', None, []))
            else:
                game_infos.append(InfoItem('Owned DLC', 'owned_dlc', None, []))

        if manifest_data:
            manifest_info = info_items['manifest']
            manifest = self.core.load_manifest(manifest_data)
            manifest_size = len(manifest_data)
            manifest_size_human = f'{manifest_size / 1024:.01f} KiB'
            manifest_info.append(InfoItem('Manifest size', 'size', manifest_size_human, manifest_size))
            manifest_type = 'JSON' if hasattr(manifest, 'json_data') else 'Binary'
            manifest_info.append(InfoItem('Manifest type', 'type', manifest_type, manifest_type.lower()))
            manifest_info.append(InfoItem('Manifest version', 'version', manifest.version, manifest.version))
            manifest_info.append(InfoItem('Manifest feature level', 'feature_level', manifest.meta.feature_level, manifest.meta.feature_level))
            manifest_info.append(InfoItem('Manifest app name', 'app_name', manifest.meta.app_name, manifest.meta.app_name))
            manifest_info.append(InfoItem('Launch EXE', 'launch_exe', manifest.meta.launch_exe or 'N/A', manifest.meta.launch_exe))
            manifest_info.append(InfoItem('Launch Command', 'launch_command', manifest.meta.launch_command or '(None)', manifest.meta.launch_command))
            manifest_info.append(InfoItem('Build version', 'build_version', manifest.meta.build_version, manifest.meta.build_version))
            manifest_info.append(InfoItem('Build ID', 'build_id', manifest.meta.build_id, manifest.meta.build_id))
            if manifest.meta.prereq_ids:
                human_list = [
                    f'Prerequisite IDs: {", ".join(manifest.meta.prereq_ids)}', f'Prerequisite name: {manifest.meta.prereq_name}',
                    f'Prerequisite path: {manifest.meta.prereq_path}', f'Prerequisite args: {manifest.meta.prereq_args or "(None)"}',
                ]
                manifest_info.append(
                    InfoItem(
                        'Prerequisites', 'prerequisites', human_list,
                        dict(
                            ids=manifest.meta.prereq_ids,
                            name=manifest.meta.prereq_name,
                            path=manifest.meta.prereq_path,
                            args=manifest.meta.prereq_args
                        )
                    )
                )
            else:
                manifest_info.append(InfoItem('Prerequisites', 'prerequisites', None, None))

            install_tags = {''}
            for fm in manifest.file_manifest_list.elements:
                for tag in fm.install_tags:
                    install_tags.add(tag)

            install_tags = sorted(install_tags)
            install_tags_human = ', '.join(i if i else '(empty)' for i in install_tags)
            manifest_info.append(InfoItem('Install tags', 'install_tags', install_tags_human, install_tags))
            # file and chunk count
            manifest_info.append(InfoItem('Files', 'num_files', manifest.file_manifest_list.count, manifest.file_manifest_list.count))
            manifest_info.append(InfoItem('Chunks', 'num_chunks', manifest.chunk_data_list.count, manifest.chunk_data_list.count))
            # total file size
            total_size = sum(fm.file_size for fm in manifest.file_manifest_list.elements)
            file_size = '{:.02f} GiB'.format(total_size / 1024 / 1024 / 1024)
            manifest_info.append(InfoItem('Disk size (uncompressed)', 'disk_size', file_size, total_size))
            # total chunk size
            total_size = sum(c.file_size for c in manifest.chunk_data_list.elements)
            chunk_size = '{:.02f} GiB'.format(total_size / 1024 / 1024 / 1024)
            manifest_info.append(InfoItem('Download size (compressed)', 'download_size', chunk_size, total_size))

            # if there are install tags break downsize by tag
            tag_disk_size = []
            tag_disk_size_human = []
            tag_download_size = []
            tag_download_size_human = []
            if len(install_tags) > 1:
                longest_tag = max(max(len(t) for t in install_tags), len('(empty)'))
                for tag in install_tags:
                    # sum up all file sizes for the tag
                    human_tag = tag or '(empty)'
                    tag_files = [fm for fm in manifest.file_manifest_list.elements if (tag in fm.install_tags) or (not tag and not fm.install_tags)]
                    tag_file_size = sum(fm.file_size for fm in tag_files)
                    tag_disk_size.append(dict(tag=tag, size=tag_file_size, count=len(tag_files)))
                    tag_file_size_human = '{:.02f} GiB'.format(tag_file_size / 1024 / 1024 / 1024)
                    tag_disk_size_human.append(f'{human_tag.ljust(longest_tag)} - {tag_file_size_human} '
                                               f'(Files: {len(tag_files)})')
                    # tag_disk_size_human.append(f'Size: {tag_file_size_human}, Files: {len(tag_files)}, Tag: "{tag}"')
                    # accumulate chunk guids used for this tag and count their size too
                    tag_chunk_guids = set()
                    for fm in tag_files:
                        for cp in fm.chunk_parts:
                            tag_chunk_guids.add(cp.guid_num)

                    tag_chunk_size = sum(c.file_size for c in manifest.chunk_data_list.elements if c.guid_num in tag_chunk_guids)
                    tag_download_size.append(dict(tag=tag, size=tag_chunk_size, count=len(tag_chunk_guids)))
                    tag_chunk_size_human = '{:.02f} GiB'.format(tag_chunk_size / 1024 / 1024 / 1024)
                    tag_download_size_human.append(f'{human_tag.ljust(longest_tag)} - {tag_chunk_size_human} '
                                                   f'(Chunks: {len(tag_chunk_guids)})')

            manifest_info.append(InfoItem('Disk size by install tag', 'tag_disk_size', tag_disk_size_human or 'N/A', tag_disk_size))
            manifest_info.append(InfoItem('Download size by install tag', 'tag_download_size', tag_download_size_human or 'N/A', tag_download_size))

        if not args.json:

            def print_info_item(item: InfoItem):
                if item.value is None:
                    print(f'- {item.name}: (None)')
                elif isinstance(item.value, list):
                    print(f'- {item.name}:')
                    for list_item in item.value:
                        print(' + ', list_item)
                elif isinstance(item.value, dict):
                    print(f'- {item.name}:')
                    for k, v in item.value.items():
                        print(' + ', k, ':', v)
                else:
                    print(f'- {item.name}: {item.value}')

            if info_items['game']:
                print('\nGame Information:')
                for info_item in info_items['game']:
                    print_info_item(info_item)
            if info_items['install']:
                print('\nInstallation information:')
                for info_item in info_items['install']:
                    print_info_item(info_item)
            if info_items['manifest']:
                print('\nManifest information:')
                for info_item in info_items['manifest']:
                    print_info_item(info_item)

            if not any(info_items.values()):
                print('No game information available.')
        else:
            json_out = dict(game=dict(), install=dict(), manifest=dict())
            for info_item in info_items['game']:
                json_out['game'][info_item.json_name] = info_item.json_value
            for info_item in info_items['install']:
                json_out['install'][info_item.json_name] = info_item.json_value
            for info_item in info_items['manifest']:
                json_out['manifest'][info_item.json_name] = info_item.json_value
            # set empty items to null
            for key, value in json_out.items():
                if not value:
                    json_out[key] = None
            return self._print_json(json_out, args.pretty_json)

    def cleanup(self):
        before = self.core.lgd.get_dir_size()
        # delete metadata
        logger.debug('Removing app metadata...')
        self.core.lgd.clean_metadata(app_names=[])

        logger.debug('Removing tmp data')
        self.core.lgd.clean_tmp_data()

        after = self.core.lgd.get_dir_size()
        logger.info(f'Cleanup complete! Removed {(before - after) / 1024 / 1024:.02f} MiB.')

    def get_token(self, args):
        if not self.core.login(force_refresh=args.bearer):
            logger.error('Login failed!')
            return

        if args.bearer:
            args.json = True
            token = dict(
                token_type='bearer',
                access_token=self.core.egs.user['access_token'],
                expires_in=self.core.egs.user['expires_in'],
                expires_at=self.core.egs.user['expires_at'],
                account_id=self.core.egs.user['account_id']
            )
        else:
            token = self.core.egs.get_asset_token()

        if args.json:
            if args.pretty_json:
                print(json.dumps(token, indent=2, sort_keys=True))
            else:
                print(json.dumps(token))
            return
        logger.info(f'Exchange code: {token["code"]}')


def main():
    parser = argparse.ArgumentParser(description=f'UEVaultManager v{__version__} - "{__codename__}"')
    parser.register('action', 'parsers', HiddenAliasSubparsersAction)

    # general arguments
    parser.add_argument('-H', '--full-help', dest='full_help', action='store_true', help='Show full help (including individual command help)')
    parser.add_argument('-v', '--debug', dest='debug', action='store_true', help='Set loglevel to debug')
    parser.add_argument('-y', '--yes', dest='yes', action='store_true', help='Default to yes for all prompts')
    parser.add_argument('-V', '--version', dest='version', action='store_true', help='Print version and exit')
    parser.add_argument('-c', '--config-file', dest='config_file', action='store', metavar='<path/name>', help=argparse.SUPPRESS)
    parser.add_argument('-J', '--pretty-json', dest='pretty_json', action='store_true', help='Pretty-print JSON')
    parser.add_argument(
        '-A',
        '--api-timeout',
        dest='api_timeout',
        action='store',
        type=float,
        default=10,
        metavar='<seconds>',
        help='API HTTP request timeout (default: 10 seconds)'
    )

    # all the commands
    subparsers = parser.add_subparsers(title='Commands', dest='subparser_name', metavar='<command>')
    auth_parser = subparsers.add_parser('auth', help='Authenticate with the Epic Games Store')
    clean_parser = subparsers.add_parser('cleanup', help='Remove old temporary, metadata, and manifest files')
    info_parser = subparsers.add_parser('info', help='Prints info about specified app name or manifest')
    list_parser = subparsers.add_parser('list', aliases=('list-assets',), hide_aliases=True, help='List available assets')
    list_files_parser = subparsers.add_parser('list-files', help='List files in manifest')
    status_parser = subparsers.add_parser('status', help='Show UEVaultManager status information')
    verify_parser = subparsers.add_parser('verify', help='Verify a asset\'s local files', aliases=('verify-asset',), hide_aliases=True)

    # hidden commands have no help text
    get_token_parser = subparsers.add_parser('get-token')

    # Positional arguments
    list_files_parser.add_argument('app_name', nargs='?', metavar='<App Name>', help='Name of the app (optional)')
    verify_parser.add_argument('app_name', help='Name of the app', metavar='<App Name>')
    info_parser.add_argument('app_name_or_manifest', help='App name or manifest path/URI', metavar='<App Name/Manifest URI>')

    # Flags
    auth_parser.add_argument(
        '--import', dest='import_egs_auth', action='store_true', help='Import Epic Games Launcher authentication data (logs out of EGL)'
    )
    auth_parser.add_argument(
        '--code',
        dest='auth_code',
        action='store',
        metavar='<authorization code>',
        help='Use specified authorization code instead of interactive authentication'
    )
    auth_parser.add_argument(
        '--token',
        dest='ex_token',
        action='store',
        metavar='<exchange token>',
        help='Use specified exchange token instead of interactive authentication'
    )
    auth_parser.add_argument(
        '--sid', dest='session_id', action='store', metavar='<session id>', help='Use specified session id instead of interactive authentication'
    )
    auth_parser.add_argument('--delete', dest='auth_delete', action='store_true', help='Remove existing authentication (log out)')
    auth_parser.add_argument('--disable-webview', dest='no_webview', action='store_true', help='Do not use embedded browser for login')

    list_parser.add_argument(
        '-T',
        '--third-party',
        '--include-non-installable',
        dest='include_noasset',
        action='store_true',
        default=False,
        help='Include apps that are not installable (e.g. that have to be activated on Origin)'
    )
    list_parser.add_argument('--csv', dest='csv', action='store_true', help='List assets in CSV format')
    list_parser.add_argument('--tsv', dest='tsv', action='store_true', help='List assets in TSV format')
    list_parser.add_argument('--json', dest='json', action='store_true', help='List assets in JSON format')
    list_parser.add_argument('--force-refresh', dest='force_refresh', action='store_true', help='Force a refresh of all assets metadata')

    list_files_parser.add_argument(
        '--force-download', dest='force_download', action='store_true', help='Always download instead of using on-disk manifest'
    )

    list_files_parser.add_argument(
        '--manifest', dest='override_manifest', action='store', metavar='<uri>', help='Manifest URL or path to use instead of the CDN one'
    )
    list_files_parser.add_argument('--csv', dest='csv', action='store_true', help='Output in CSV format')
    list_files_parser.add_argument('--tsv', dest='tsv', action='store_true', help='Output in TSV format')
    list_files_parser.add_argument('--json', dest='json', action='store_true', help='Output in JSON format')
    list_files_parser.add_argument(
        '--hashlist', dest='hashlist', action='store_true', help='Output file hash list in hashcheck/sha1sum -c compatible format'
    )
    list_files_parser.add_argument(
        '--install-tag', dest='install_tag', action='store', metavar='<tag>', type=str, help='Show only files with specified install tag'
    )

    status_parser.add_argument('--offline', dest='offline', action='store_true', help='Only print offline status information, do not login')
    status_parser.add_argument('--json', dest='json', action='store_true', help='Show status in JSON format')

    clean_parser.add_argument('--keep-manifests', dest='keep_manifests', action='store_true', help='Do not delete old manifests')

    info_parser.add_argument('--offline', dest='offline', action='store_true', help='Only print info available offline')
    info_parser.add_argument('--json', dest='json', action='store_true', help='Output information in JSON format')

    get_token_parser.add_argument('--json', dest='json', action='store_true', help='Output information in JSON format')
    get_token_parser.add_argument('--bearer', dest='bearer', action='store_true', help='Return fresh bearer token rather than an exchange code')

    args, extra = parser.parse_known_args()

    if args.version:
        print(f'UEVaultManager version "{__version__}", codename "{__codename__}"')
        exit(0)

    if not args.subparser_name or args.full_help:
        print(parser.format_help())

        if args.full_help:
            # Commands that should not be shown in full help/list of commands (e.g. aliases)
            _hidden_commands = {'download', 'update', 'repair', 'get-token', 'verify-asset', 'list-assets'}
            # Print the help for all the subparsers. Thanks stackoverflow!
            print('Individual command help:')
            subparsers = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
            for choice, subparser in subparsers.choices.items():
                if choice in _hidden_commands:
                    continue
                print(f'\nCommand: {choice}')
                print(subparser.format_help())
        elif os.name == 'nt':
            from UEVaultManager.lfs.windows_helpers import double_clicked
            if double_clicked():
                print('Please note that this is not the intended way to run UEVaultManager.')
                print('Follow https://github.com/LaurentOngaro/UEVaultManager/wiki/Setup-Instructions to set it up properly')
                subprocess.Popen(['cmd', '/K', 'echo>nul'])
        return

    cli = UEVaultManagerCLI(override_config=args.config_file, api_timeout=args.api_timeout)
    ql = cli.setup_threaded_logging()

    config_ll = cli.core.lgd.config.get('UEVaultManager', 'log_level', fallback='info')
    if config_ll == 'debug' or args.debug:
        logging.getLogger().setLevel(level=logging.DEBUG)
        # keep requests quiet
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)

    if hasattr(args, 'platform'):
        if not args.platform:
            os_default = 'Mac' if sys_platform == 'darwin' else 'Windows'
            args.platform = cli.core.lgd.config.get('UEVaultManager', 'default_platform', fallback=os_default)
        elif args.platform not in ('Win32', 'Windows', 'Mac'):
            logger.warning(f'Platform "{args.platform}" may be invalid. Valid ones are: Windows, Win32, Mac.')

    # if --yes is used as part of the subparsers arguments manually set the flag in the main parser.
    if '-y' in extra or '--yes' in extra:
        args.yes = True

    # technically args.func() with setdefaults could work (see docs on subparsers)
    # but that would require all funcs to accept args and extra...
    try:
        if args.subparser_name == 'auth':
            cli.auth(args)
        elif args.subparser_name in {'list', 'list-assets'}:
            cli.list_assets(args)
        elif args.subparser_name == 'list-files':
            cli.list_files(args)
        elif args.subparser_name == 'status':
            cli.status(args)
        elif args.subparser_name == 'info':
            cli.info(args)
        elif args.subparser_name == 'cleanup':
            cli.cleanup()
        elif args.subparser_name == 'get-token':
            cli.get_token(args)
    except KeyboardInterrupt:
        logger.info('Command was aborted via KeyboardInterrupt, cleaning up...')

    # Disable the update message if JSON/TSV/CSV outputs are used
    disable_update_message = False
    if hasattr(args, 'json'):
        disable_update_message = args.json
    if not disable_update_message and hasattr(args, 'tsv'):
        disable_update_message = args.tsv
    if not disable_update_message and hasattr(args, 'csv'):
        disable_update_message = args.csv

    # show note if update is available
    if not disable_update_message and cli.core.update_available and cli.core.update_notice_enabled():
        if update_info := cli.core.get_update_info():
            print(f'\nAn update available!')
            print(f'- New version: {update_info["version"]} - "{update_info["name"]}"')
            print(f'- Release summary:\n{update_info["summary"]}\n- Release URL: {update_info["gh_url"]}')
            if update_info['critical']:
                print('! This update is recommended as it fixes major issues.')
            elif 'downloads' in update_info:
                dl_platform = 'windows'
                if sys_platform == 'darwin':
                    dl_platform = 'macos'
                elif sys_platform == 'linux':
                    dl_platform = 'linux'

                print(f'\n- Download URL: {update_info["downloads"][dl_platform]}')

    cli.core.exit()
    ql.stop()
    exit(0)


if __name__ == '__main__':
    # required for pyinstaller on Windows, does nothing on other platforms.
    freeze_support()
    main()
