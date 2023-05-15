# coding=utf-8
"""
Implementation for:
- UEVaultManagerCLI: command line interface for UEVaultManager
"""
import argparse
import csv
import json
import logging
import os
import shutil
import subprocess
import webbrowser
from collections import namedtuple
from datetime import datetime
from logging.handlers import QueueListener
from multiprocessing import freeze_support, Queue as MPQueue
from platform import platform
from sys import exit, stdout, platform as sys_platform
import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
# noinspection PyPep8Naming
import UEVaultManager.tkgui.modules.UEVMGuiClass as gui_w  # using the shortest variable name for globals for convenience
from UEVaultManager import __version__, __codename__
from UEVaultManager.api.egs import create_empty_assets_extras
from UEVaultManager.core import AppCore, CSV_headings
from UEVaultManager.models.exceptions import InvalidCredentialsError
from UEVaultManager.tkgui.modules.ProgressWindowsClass import ProgressWindow
from UEVaultManager.tkgui.modules.SaferDictClass import SaferDict
from UEVaultManager.utils.cli import str_to_bool, check_and_create_path, create_list_from_string
from UEVaultManager.utils.custom_parser import HiddenAliasSubparsersAction

logging.basicConfig(format='[%(name)s] %(levelname)s: %(message)s', level=logging.INFO)


class UEVaultManagerCLI:
    """
    Command line interface for UEVaultManager
    :param override_config: path to a config file to use instead of the default one
    :param api_timeout: timeout for API requests
    """

    def __init__(self, override_config=None, api_timeout=None):
        self.core = AppCore(override_config, timeout=api_timeout)
        self.logger = logging.getLogger('Cli')
        self.logging_queue = None

    def setup_threaded_logging(self) -> QueueListener:
        """
        Setup logging for the CLI
        """
        self.logging_queue = MPQueue(-1)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(name)s] %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        ql = QueueListener(self.logging_queue, handler)
        ql.start()
        return ql

    def _resolve_aliases(self, name: str) -> str:
        """
        Resolve an alias
        :param name: name to resolve
        :return: real name
        """
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

    def create_file_backup(self, file_src: str) -> None:
        """
        Create a backup of a file
        :param file_src: path to the file to back up
        """
        # make a backup of the existing file

        # for files defined relatively to the config folder
        file_src = file_src.replace('~/.config', self.core.lgd.path)

        if not file_src:
            return
        try:
            file_name_no_ext, file_ext = os.path.splitext(file_src)
            file_backup = f'{file_name_no_ext}.BACKUP_{datetime.now().strftime("%y-%m-%d_%H-%M-%S")}{file_ext}'
            shutil.copy(file_src, file_backup)
            self.logger.info(f'File {file_src} has been copied to {file_backup}')
        except FileNotFoundError:
            self.logger.info(f'File {file_src} has not been found')

    def create_log_file_backup(self) -> None:
        """
        Create a backup of the log files
        """
        self.create_file_backup(self.core.ignored_assets_filename_log)
        self.create_file_backup(self.core.notfound_assets_filename_log)
        self.create_file_backup(self.core.bad_data_assets_filename_log)

    def create_asset_from_data(
        self, item, asset_id: str, no_text_data: str, no_int_data: int, no_float_data: float, bool_true_data: bool, bool_false_data: bool
    ) -> (str, dict):
        """
        Create a dict containing all the data for an asset
        :param item: item to get data from
        :param asset_id: id of the asset
        :param no_text_data: text to use if no text data is found
        :param no_int_data: int value to use if no int data is found
        :param no_float_data: float value to use if no float data is found
        :param bool_true_data: bool (True) value to use if no bool data is found
        :param bool_false_data: bool (False) value to use if no bool data is found
        :return: (asset_id, dict containing all the data for an asset)
        """
        record = {}
        metadata = item.metadata
        uid = metadata['id']
        category = metadata['categories'][0]['path']
        separator = ','
        try:
            tmp_list = [separator.join(item.get('compatibleApps')) for item in metadata['releaseInfo']]
            compatible_versions = separator.join(tmp_list)
        except TypeError as error:
            self.logger.warning(f'Error getting compatibleApps {item.app_name} : {error!r}')
            compatible_versions = no_text_data
        thumbnail_url = ''
        try:
            thumbnail_url = metadata['keyImages'][2]['url']  # 'Image' with 488 height
        except IndexError:
            self.logger.debug(f'asset {item.app_name} has no image')
        date_added = datetime.now().strftime(self.core.default_datetime_format)
        extras_data = None
        try:
            extras_data = self.core.lgd.get_item_extras(item.app_name)
        except AttributeError as error:
            self.logger.warning(f'Error getting extra data for {item.app_name} : {error!r}')
        if extras_data is None:
            extras_data = create_empty_assets_extras(item.app_name)
        asset_url = no_text_data
        review = no_int_data
        price = no_float_data
        purchased = bool_false_data
        supported_versions = no_text_data
        page_title = no_text_data
        grab_result = no_int_data
        try:
            asset_url = extras_data['asset_url']
            review = extras_data['review']
            price = extras_data['price']
            purchased = extras_data['purchased']
            supported_versions = extras_data['supported_versions']
            page_title = extras_data['page_title']
            grab_result = extras_data['grab_result']
        except (TypeError, KeyError) as error:
            self.logger.warning(f'Key not found in extra data for {item.app_name} : {error!r}')

        if self.core.engine_version_for_obsolete_assets == '' or supported_versions == '' or supported_versions == no_text_data:
            obsolete = bool_false_data
        else:
            supported_versions_list = supported_versions.lower().replace('UE_', '')
            supported_versions_list = create_list_from_string(supported_versions_list)
            obsolete = bool_true_data
            for _, version in enumerate(supported_versions_list):
                if version == '':
                    continue
                else:
                    if float(self.core.engine_version_for_obsolete_assets) >= float(version):
                        obsolete = bool_false_data
                        break
        try:
            values = (
                # dans les infos
                asset_id  # 'asset_id'
                , item.app_name  # 'App name'
                , item.app_title  # 'App title'
                , category  # 'Category'
                , thumbnail_url  # 'Image' with 488 height
                , asset_url  # 'Url'
                , item.app_version('Windows')  # 'UE Version'
                , compatible_versions  # compatible_versions
                , review  # 'Review'
                , metadata['developer']  # 'Developer'
                , metadata['description']  # 'Description'
                , uid  # 'Uid'
                , metadata['creationDate']  # 'Creation Date'
                , metadata['lastModifiedDate']  # 'Update Date'
                , metadata['status']  # 'status'
                # Modified Fields when added into the file
                , date_added  # 'Date Added'
                , price  # 'Price'
                , no_float_data  # 'Old Price'
                , bool_false_data  # 'On Sale'
                , purchased  # 'Purchased'
                , obsolete  # 'obsolete'
                # Extracted from page, can be compared with value in metadata. Coud be used to if check data grabbing if OK
                , supported_versions  # 'supported versions'
                , page_title  # 'page title'
                , grab_result  # 'grab result'
                # Modified Fields when added into the file
                , no_text_data  # 'Comment'
                , no_float_data  # 'Stars'
                , no_text_data  # 'Asset Folder'
                , bool_false_data  # 'Must Buy'
                , no_text_data  # 'Test result
                , no_text_data  # 'Installed Folder'
                , no_text_data  # 'Alternative'
            )
            record = dict(zip(CSV_headings.keys(), values))
        except TypeError:
            self.logger.error(f'Could not create record for {item.app_name}')

        return asset_id, record

    def auth(self, args) -> None:
        """
        Handle authentication
        :param args: options passed to the command
        """
        if args.auth_delete:
            self.core.lgd.invalidate_userdata()
            self.logger.info('User data deleted.')
            return

        try:
            self.logger.info('Testing existing login data if present...')
            if self.core.login():
                self.logger.info(
                    'Stored credentials are still valid, if you wish to switch to a different '
                    'account, run "UEVaultManager auth --delete" and try again.'
                )
                return
        except ValueError:
            pass
        except InvalidCredentialsError:
            self.logger.error('Stored credentials were found but were no longer valid. Continuing with login...')
            self.core.lgd.invalidate_userdata()

        # Force an update check and notice in case there are API changes
        self.core.check_for_updates(force=True)
        self.core.force_show_update = True

        if args.import_egs_auth:
            self.logger.info('Importing login session from the Epic Launcher...')
            try:
                if self.core.auth_import():
                    self.logger.info('Successfully imported login session from EGS!')
                    self.logger.info(f'Now logged in as user "{self.core.lgd.userdata["displayName"]}"')
                    return
                else:
                    self.logger.warning('Login session from EGS seems to no longer be valid.')
                    self.core.clean_exit(1)
            except Exception as error:
                self.logger.error(f'No EGS login session found, please login manually. (Exception: {error!r})')
                self.core.clean_exit(1)

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
                    self.logger.info(f'Successfully logged in as "{self.core.lgd.userdata["displayName"]}" via WebView')
                else:
                    self.logger.error('WebView login attempt failed, please see log for details.')
                return
        elif args.session_id:
            exchange_token = self.core.auth_sid(args.session_id)
        elif args.auth_code:
            auth_code = args.auth_code
        elif args.ex_token:
            exchange_token = args.ex_token

        if not exchange_token and not auth_code:
            self.logger.fatal('No exchange token/authorization code, cannot login.')
            return

        if exchange_token and self.core.auth_ex_token(exchange_token):
            self.logger.info(f'Successfully logged in as "{self.core.lgd.userdata["displayName"]}"')
        elif auth_code and self.core.auth_code(auth_code):
            self.logger.info(f'Successfully logged in as "{self.core.lgd.userdata["displayName"]}"')
        else:
            self.logger.error('Login attempt failed, please see log for details.')

    def list_assets(self, args) -> None:
        """
        List assets in the vault
        :param args: options passed to the command
        """

        def update_and_merge_csv_record_data(_asset, _items_in_file, _no_data_value) -> []:
            """
            Updates the data of the asset with the data from the items in the file
            :param _asset: asset to update
            :param _items_in_file: list of items in the file
            :param _no_data_value: value to use when no data is available
            :return: list of values to be written in the CSV file
            """
            _asset_id = _asset[0]
            _csv_record = list(_asset[1].values())  # we need a list for the CSV comparison, not a dict
            # merge data from the items in the file (if exists) and those get by the application
            # items_in_file must be a dict of dicts
            if _items_in_file.get(_asset_id):
                item_in_file = _items_in_file.get(_asset_id)
                if len(item_in_file.keys()) != len(CSV_headings.keys()):
                    self.logger.error(
                        f'In the existing file, asset {_asset_id} has not the same number of keys as the CSV headings. This asset is ignored and its values will be overwritten'
                    )
                    return _csv_record
                else:
                    # loops through its columns
                    index = 0
                    price_index = 0
                    _price = float(_no_data_value)
                    old_price = float(_no_data_value)
                    on_sale = _no_data_value
                    for key, keep_value_in_file in CSV_headings.items():
                        if item_in_file[key] is None:
                            self.logger.error(
                                f'In the existing file, asset {_asset_id} has no column named {key}. This asset is ignored and its values will be overwritten'
                            )
                            # print(f' CHECK for asset {_asset_id}')
                            return _csv_record
                        else:
                            if keep_value_in_file:
                                _csv_record[index] = item_in_file[key]
                            # Get the old price in the previous file
                            if key == 'Price':
                                price_index = index
                                try:
                                    _price = float(_csv_record[price_index])
                                    old_price = float(
                                        item_in_file[key]
                                    )  # NOTE: the 'old price' is the 'price' saved in the file, not the 'old_price' in the file
                                except Exception as _error:
                                    self.logger.warning(f'Old Price value can not be converted for asset {_asset_id}\nError:{_error!r}')
                        index += 1

                # compute the price related fields
                if price_index > 0 and (isinstance(old_price, int) or isinstance(old_price, float)):
                    on_sale = True if _price > old_price else False
                _csv_record[price_index + 1] = old_price
                _csv_record[price_index + 2] = on_sale
            return _csv_record

        def update_and_merge_json_record_data(_asset, _items_in_file, _no_float_value: float, _no_bool_false_value: bool) -> dict:
            """
            Updates the data of the asset with the data from the items in the file
            :param _asset: asset to update
            :param _items_in_file: list of items in the file
            :param _no_float_value:  value to use when no float data is available
            :param _no_bool_false_value: value (False) to use when no bool data is available
            :return:
            """
            _asset_id = _asset[0]
            _json_record = _asset[1]

            # merge data from the items in the file (if exists) and those get by the application
            # items_in_file is a dict of dict
            if _items_in_file.get(_asset_id):
                # loops through its columns
                _price = float(_no_float_value)
                old_price = float(_no_float_value)
                on_sale = _no_bool_false_value
                for key, keep_value_in_file in CSV_headings.items():
                    if keep_value_in_file and _items_in_file[_asset_id].get(key):
                        _json_record[key] = _items_in_file[_asset_id][key]

                # Get the old price in the previous file
                try:
                    _price = float(_json_record['Price'])
                    old_price = float(
                        _items_in_file[_asset_id]['Price']
                    )  # NOTE: the 'old price' is the 'price' saved in the file, not the 'old_price' in the file
                except Exception as _error:
                    self.logger.warning(f'Old Price values can not be converted for asset {_asset_id}\nError:{_error!r}')

                # compute the price related fields
                if isinstance(old_price, int) or isinstance(old_price, float):
                    on_sale = True if _price > old_price else False
                _json_record['Old Price'] = old_price
                _json_record['On Sale'] = on_sale
            return _json_record

        self.logger.info('Logging in...')
        if not self.core.login():
            self.logger.error('Login failed, cannot continue!')
            self.core.clean_exit(1)

        if args.force_refresh:
            self.logger.info('Refreshing asset list, this may take a while...')
        else:
            self.logger.info('Getting asset list... (this may take a while)')

        if args.filter_category:
            gui_g.UEVM_filter_category = args.filter_category

        if gui_g.UEVM_filter_category != '' and gui_g.UEVM_filter_category != gui_g.s.default_category_for_all:
            self.logger.info(f'The String "{gui_g.UEVM_filter_category }" will be search in Assets category')

        gui_g.progress_window_ref = None
        progress_window = None
        if args.gui:
            # check if the GUI is already running
            if gui_g.UEVM_gui_ref is None:
                # create a fake root because ProgressWindow must always be a top level window
                gui_g.UEVM_gui_ref = gui_w.UEVMGuiHiddenRoot()
                uewm_gui_exists = False
            else:
                uewm_gui_exists = True
            # create and use a progress window (as a top level window)
            gui_g.UEVM_log_ref = self.logger
            progress_window = ProgressWindow(
                title="Updating Assets List",
                quit_on_close=not uewm_gui_exists,
                width=300,
                height=150,
                max_value=200,
                show_start_button=False,
                show_stop_button=True,
                function=self.core.get_asset_list,
                function_parameters={
                    'filter_category': gui_g.UEVM_filter_category,
                    'force_refresh': args.force_refresh
                }
            )
            if uewm_gui_exists:
                # if the main gui is running, we already have a tk.mainloop running
                # we need to constantly update the progress bar
                while not progress_window.must_end:
                    progress_window.update()
            else:
                # if the main gui is not running, we need to start a tk.mainloop
                progress_window.mainloop()

            items = progress_window.get_result()

        else:
            items = self.core.get_asset_list(platform='Windows', filter_category=args.filter_category, force_refresh=args.force_refresh)

        if args.include_non_asset:
            na_items = self.core.get_non_asset_library_items(skip_ue=False)
            items.extend(na_items)

        no_int_data = 0
        no_float_value = 0.0
        no_text_data = ''
        no_bool_true_data = True
        no_bool_false_data = False

        # sort assets by name in reverse (to have the latest version first
        items = sorted(items, key=lambda x: x.app_name.lower(), reverse=True)

        # use a dict to store records and avoid duplicates (asset with the same asset_id and a different asset_name)
        assets_to_output = {}
        # create a minimal and full dict of data from existing assets
        assets_in_file = {}

        cpt = 0
        cpt_max = len(items)
        if gui_g.progress_window_ref is not None:
            gui_g.progress_window_ref.reset(new_value=0, new_text="Merging assets data...", new_max_value=len(items))
        for item in items:
            if gui_g.progress_window_ref is not None and not gui_g.progress_window_ref.update_and_continue(increment=1):
                return
            cpt += 1
            # notes:
            #   asset_id is not unique because somme assets can have the same asset_id but with several UE versions
            #   app_name is unique because it includes the unreal version
            #   we use asset_id as key because we don't want to have several entries for the same asset
            #   some asset won't have asset_infos (mainly when using the -T option), in that case we use the app_title as asset_id
            if item.asset_infos.get('Windows'):
                asset_id = item.asset_infos['Windows'].asset_id
            else:
                asset_id = item.app_title

            if assets_to_output.get(asset_id):
                self.logger.debug(f'Asset {asset_id} already present in the list (usually with another ue version)')
            else:
                asset_id, asset = self.create_asset_from_data(
                    item, asset_id, no_text_data, no_int_data, no_float_value, no_bool_true_data, no_bool_false_data
                )  # asset is a dict
                assets_to_output[asset_id] = asset

            if self.core.verbose_mode:
                self.logger.info(f'Asset id={asset_id} has been created from data. Done {cpt}/{cpt_max} items')

        # output with extended info
        if args.output and (args.csv or args.tsv or args.json) and self.core.create_output_backup:
            self.create_file_backup(args.output)

        if args.csv or args.tsv:
            if args.output:
                file_src = args.output
                # If the output file exists, we read its content to keep some data
                try:
                    with open(file_src, 'r', encoding='utf-8') as output:
                        csv_file_content = csv.DictReader(output)
                        # get the data (it's a dict)
                        for csv_record in csv_file_content:
                            # noinspection PyTypeChecker
                            asset_id = csv_record['Asset_id']
                            assets_in_file[asset_id] = csv_record
                        output.close()
                except (FileExistsError, OSError, UnicodeDecodeError, StopIteration):
                    self.logger.warning(f'Could not read CSV record from the file {args.output}')

                # write the content of the file to keep some data
                if not check_and_create_path(file_src):
                    self.logger.critical(f'Could not create folder for {file_src}')
                    self.core.clean_exit(1)
                # reopen file for writing
                output = open(file_src, 'w', encoding='utf-8')
            else:
                output = stdout
            # end if args.output:

            try:
                writer = csv.writer(output, dialect='excel-tab' if args.tsv else 'excel', lineterminator='\n')
                writer.writerow(CSV_headings.keys())
                cpt = 0
                if gui_g.progress_window_ref is not None:
                    gui_g.progress_window_ref.reset(
                        new_value=0, new_text="Writing assets into csv file...", new_max_value=len(assets_to_output.items())
                    )
                for asset in sorted(assets_to_output.items()):
                    if gui_g.progress_window_ref is not None and not gui_g.progress_window_ref.update_and_continue(increment=1):
                        return
                    asset_id = asset[0]
                    try:
                        if len(assets_in_file) > 0:
                            csv_record_merged = update_and_merge_csv_record_data(asset, assets_in_file, no_int_data)
                        else:
                            csv_record_merged = list(asset[1].values())
                        cpt += 1
                        writer.writerow(csv_record_merged)
                    except (OSError, UnicodeEncodeError, TypeError) as error:
                        self.logger.error(f'Could not write CSV record for {asset_id} into {args.output}\nError:{error!r}')
            except OSError:
                self.logger.error(f'Could not write list result to {args.output}')
            output.close()
            self.logger.info(
                f'\n======\n{cpt} assets have been printed or saved (without duplicates due to different UE versions)\nOperation Finished\n======\n'
            )
            if args.gui and progress_window is not None:
                progress_window.close_window()
            return
        # end if args.csv or args.tsv:

        if args.json:
            if args.output:
                file_src = args.output
                # If the output file exists, we read its content to keep some data
                try:
                    with open(file_src, 'r', encoding='utf-8') as output:
                        assets_in_file = json.load(output)
                        output.close()
                except (FileExistsError, OSError, UnicodeDecodeError, StopIteration, json.decoder.JSONDecodeError):
                    self.logger.warning(f'Could not read Json record from the file {args.output}')

                # write the content of the file to keep some data
                if not check_and_create_path(file_src):
                    self.logger.critical(f'Could not create folder for {file_src}')
                    self.core.clean_exit(1)
                # reopen file for writing
                output = open(file_src, 'w', encoding='utf-8')
            else:
                output = stdout
            # end if args.output:

            try:
                cpt = 0
                json_content = {}
                if gui_g.progress_window_ref is not None:
                    gui_g.progress_window_ref.reset(
                        new_value=0, new_text="Writing assets into json file...", new_max_value=len(assets_to_output.items())
                    )
                for asset in sorted(assets_to_output.items()):
                    if gui_g.progress_window_ref is not None and not gui_g.progress_window_ref.update_and_continue(increment=1):
                        return
                    asset_id = asset[0]
                    if len(assets_in_file) > 0:
                        json_record_merged = update_and_merge_json_record_data(asset, assets_in_file, no_float_value, no_bool_false_data)
                    else:
                        json_record_merged = asset[1]
                    #      output.write(",\n")
                    try:
                        asset_id = json_record_merged['Asset_id']
                        json_content[asset_id] = json_record_merged
                        cpt += 1
                    except (OSError, UnicodeEncodeError, TypeError) as error:
                        self.logger.error(f'Could not write Json record for {asset_id} into {args.output}\nError:{error!r}')

                json.dump(json_content, output, indent=2)
            except OSError:
                self.logger.error(f'Could not write list result to {args.output}')
            output.close()
            self.logger.info(
                f'\n======\n{cpt} assets have been printed or saved (without duplicates due to different UE versions)\nOperation Finished\n======\n'
            )
            if args.gui and progress_window is not None:
                progress_window.close_window()
            return
        # end if args.json:

        # here, no other output has been done before, so we print the asset in a quick format to the console
        print('\nAvailable UE Assets:')
        for asset in items:
            version = asset.app_version('Windows')
            print(f' * {asset.app_title.strip()} (App name: {asset.app_name} | Version: {version})')
        print(f'\nTotal: {len(items)}')

    def list_files(self, args):
        """
        List files for a given app name or manifest url/path
        :param args: options passed to the command
        :return:
        """
        if not args.override_manifest and not args.app_name:
            print('You must provide either a manifest url/path or app name!')
            return
        elif args.app_name:
            args.app_name = self._resolve_aliases(args.app_name)

        # check if we even need to log in
        if args.override_manifest:
            self.logger.info(f'Loading manifest from "{args.override_manifest}"')
            manifest_data, _ = self.core.get_uri_manifest(args.override_manifest)
        else:
            self.logger.info(f'Logging in and downloading manifest for {args.app_name}')
            if not self.core.login():
                self.logger.error('Login failed! Cannot continue with download process.')
                self.core.clean_exit(1)
            update_meta = args.force_refresh
            item = self.core.get_item(args.app_name, update_meta=update_meta)
            if not item:
                self.logger.critical(f'Could not fetch metadata for "{args.app_name}" (check spelling/account ownership)')
                self.core.clean_exit(1)
            manifest_data, _ = self.core.get_cdn_manifest(item, platform='Windows')

        manifest = self.core.load_manifest(manifest_data)
        files = sorted(manifest.file_manifest_list.elements, key=lambda a: a.filename.lower())

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
                self.logger.info(f'Install tags: {", ".join(sorted(install_tags))}')

    def status(self, args) -> None:
        """
        Print the information about the vault and the assets available
        :param args: options passed to the command
        """
        if not args.offline:
            try:
                if not self.core.login():
                    self.logger.error('Log in failed!')
                    self.core.clean_exit(1)
            except ValueError:
                pass
            # if automatic checks are off force an update here
            self.core.check_for_updates(force=True)

        if not self.core.lgd.userdata:
            user_name = '<not logged in>'
            args.offline = True
        else:
            user_name = self.core.lgd.userdata['displayName']

        assets_available = len(self.core.get_asset_list(update_assets=not args.offline))
        if args.json:
            return self._print_json(dict(account=user_name, assets_available=assets_available, config_directory=self.core.lgd.path), args.pretty_json)

        print(f'Epic account: {user_name}')
        print(f'Assets available: {assets_available}')
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

    def info(self, args) -> None:
        """
        Print information about a given app name or manifest url/path
        :param args: options passed to the command
        """
        name_or_path = args.app_name_or_manifest
        app_name = manifest_uri = None
        if os.path.exists(name_or_path) or name_or_path.startswith('http'):
            manifest_uri = name_or_path
        else:
            app_name = self._resolve_aliases(name_or_path)

        if not args.offline and not manifest_uri:
            try:
                if not self.core.login():
                    self.logger.error('Log in failed!')
                    self.core.clean_exit(1)
            except ValueError:
                pass

        # lists that will be printed or turned into JSON data
        info_items = dict(assets=list(), manifest=list(), install=list())
        InfoItem = namedtuple('InfoItem', ['name', 'json_name', 'value', 'json_value'])

        update_meta = not args.offline and args.force_refresh

        item = self.core.get_item(app_name, update_meta=update_meta, platform='Windows')
        if item and not self.core.asset_available(item, platform='Windows'):
            self.logger.warning(
                f'Asset information for "{item.app_name}" is missing, this may be due to the asset '
                f'not being available on the selected platform or currently logged-in account.'
            )
            args.offline = True

        manifest_data = None
        # entitlements = None
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
                self.logger.info('Asset not installed and offline mode enabled, cannot load manifest.')
        elif item:
            # entitlements = self.core.egs.get_user_entitlements()
            egl_meta = self.core.egs.get_item_info(item.namespace, item.catalog_item_id)
            item.metadata = egl_meta
            # Get manifest if asset exists for current platform
            if 'Windows' in item.asset_infos:
                manifest_data, _ = self.core.get_cdn_manifest(item, 'Windows')

        if item:
            asset_infos = info_items['assets']
            asset_infos.append(InfoItem('App name', 'app_name', item.app_name, item.app_name))
            asset_infos.append(InfoItem('Title', 'title', item.app_title, item.app_title))
            asset_infos.append(InfoItem('Latest version', 'version', item.app_version('Windows'), item.app_version('Windows')))
            all_versions = {k: v.build_version for k, v in item.asset_infos.items()}
            asset_infos.append(InfoItem('All versions', 'platform_versions', all_versions, all_versions))

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

            def print_info_item(local_item: InfoItem) -> None:
                """
                Prints an info item to the console
                :param local_item:  The info item to print
                """
                if local_item.value is None:
                    print(f'- {local_item.name}: (None)')
                elif isinstance(local_item.value, list):
                    print(f'- {local_item.name}:')
                    for list_item in local_item.value:
                        print(' + ', list_item)
                elif isinstance(local_item.value, dict):
                    print(f'- {local_item.name}:')
                    for k, v in local_item.value.items():
                        print(' + ', k, ':', v)
                else:
                    print(f'- {local_item.name}: {local_item.value}')

            if info_items.get('asset'):
                print('\nAsset Information:')
                for info_item in info_items['asset']:
                    print_info_item(info_item)
            if info_items.get('install'):
                print('\nInstallation information:')
                for info_item in info_items['install']:
                    print_info_item(info_item)
            if info_items.get('manifest'):
                print('\nManifest information:')
                for info_item in info_items['manifest']:
                    print_info_item(info_item)

            if not any(info_items.values()):
                print('No asset information available.')
        else:
            json_out = dict(asset=dict(), install=dict(), manifest=dict())
            if info_items.get('asset'):
                for info_item in info_items['asset']:
                    json_out['asset'][info_item.json_name] = info_item.json_value
            if info_items.get('install'):
                for info_item in info_items['install']:
                    json_out['install'][info_item.json_name] = info_item.json_value
            if info_items.get('manifest'):
                for info_item in info_items['manifest']:
                    json_out['manifest'][info_item.json_name] = info_item.json_value
            # set empty items to null
            for key, value in json_out.items():
                if not value:
                    json_out[key] = None
            return self._print_json(json_out, args.pretty_json)

    def cleanup(self, args) -> None:
        """
        Cleans up the local assets data folders and logs
        :param args: options passed to the command
        """
        before = self.core.lgd.get_dir_size()

        # delete metadata
        if args.delete_metadata:
            self.logger.debug('Removing app metadata...')
            self.core.lgd.clean_metadata()

        # delete extras data
        if args.delete_extras_data:
            self.logger.debug('Removing app extras data...')
            self.core.lgd.clean_extras()

        # delete log and backup
        self.logger.debug('Removing logs and backups...')
        self.core.lgd.clean_logs_and_backups()

        self.logger.debug('Removing manifests...')
        self.core.lgd.clean_manifests()

        self.logger.debug('Removing tmp data')
        self.core.lgd.clean_tmp_data()

        after = self.core.lgd.get_dir_size()
        self.logger.info(f'Cleanup complete! Removed {(before - after) / 1024 / 1024:.02f} MiB.')

    def get_token(self, args) -> None:
        """
        Gets the access token for the current user
        :param args: options passed to the command
        """
        if not self.core.login(force_refresh=args.bearer):
            self.logger.error('Login failed!')
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
        self.logger.info(f'Exchange code: {token["code"]}')

    def edit_assets(self, args) -> None:
        """
        Edit assets in the database using a GUI
        :param args: options passed to the command
        """
        if not args.input:
            input_filename = gui_g.s.csv_filename
            self.logger.warning('The file to read data from has not been precised by the --input command option. The default file name will be used.')
        else:
            input_filename = gui_f.path_from_relative_to_absolute(args.input)

        app_icon_filename = gui_f.path_from_relative_to_absolute(gui_g.s.app_icon_filename)
        gui_g.UEVM_log_ref = self.logger
        gui_g.UEVM_cli_ref = self
        # args can not be used as it because it's an object that mainly run as a dict (but it's not)
        # so we need to convert it to a dict first
        temp_dict = vars(args)
        # set output file name from the input one. Used by the "rebuild file content" button (or rebuild_data method)
        temp_dict['output'] = input_filename
        temp_dict['csv'] = True  # force csv output
        temp_dict['gui'] = True
        # create a SaferDict object from the dict (it will avoid errors when trying to access non-existing keys)
        gui_g.UEVM_cli_args = SaferDict({})
        # copy the dict content to the SaferDict object
        gui_g.UEVM_cli_args.copy_from(temp_dict)

        gui_g.UEVM_gui_ref = gui_w.UEVMGui(
            title=gui_g.s.app_title,
            width=gui_g.s.app_width,
            height=gui_g.s.app_height,
            icon=app_icon_filename,
            screen_index=0,
            file=input_filename,
            show_open_file_dialog=not os.path.isfile(input_filename),
        )
        gui_g.UEVM_gui_ref.mainloop()
        # gui_g.UEVM_gui_ref.quit()


def main():
    """
    Main function
    """
    parser = argparse.ArgumentParser(description=f'UEVaultManager v{__version__} - "{__codename__}"')
    parser.register('action', 'parsers', HiddenAliasSubparsersAction)

    # general arguments
    parser.add_argument('-H', '--full-help', dest='full_help', action='store_true', help='Show full help (including individual command help)')
    parser.add_argument('-d', '--debug', dest='debug', action='store_true', help='Set loglevel to debug')
    parser.add_argument('-y', '--yes', dest='yes', action='store_true', help='Default to yes for all prompts')
    parser.add_argument('-V', '--version', dest='version', action='store_true', help='Print version and exit')
    parser.add_argument(
        '-c', '--config-file', dest='config_file', action='store', metavar='<path/name>', help='Overwrite the default configuration file name to use'
    )
    parser.add_argument('-J', '--pretty-json', dest='pretty_json', action='store_true', help='Pretty-print JSON. Improve readability')
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
    edit_parser = subparsers.add_parser('edit', aliases=('edit-assets',), hide_aliases=True, help='Edit the assets list file')

    # hidden commands have no help text
    get_token_parser = subparsers.add_parser('get-token')

    # Positional arguments
    list_files_parser.add_argument('app_name', nargs='?', metavar='<App Name>', help='Name of the app (optional)')
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
        '-T', '--third-party', dest='include_non_asset', action='store_true', default=False, help='Include assets that are not installable.'
    )
    list_parser.add_argument('--csv', dest='csv', action='store_true', help='Output in in CSV format')
    list_parser.add_argument('--tsv', dest='tsv', action='store_true', help='Output in in TSV format')
    list_parser.add_argument('--json', dest='json', action='store_true', help='Output in in JSON format')
    list_parser.add_argument('-f', '--force-refresh', dest='force_refresh', action='store_true', help='Force a refresh of all assets metadata')
    list_parser.add_argument(
        '-g',
        '--gui',
        dest='gui',
        action='store_true',
        help='Display additional informations using gui elements like dialog boxes or progress window'
    )
    list_parser.add_argument(
        '-fc',
        '--filter-category',
        dest='filter_category',
        action='store',
        help='Filter assets by category. Search against the asset category in the marketplace. Search is case insensitive and can be partial'
    )
    list_parser.add_argument(
        '-o', '--output', dest='output', metavar='<path/name>', action='store', help='The file name (with path) where the list should be written'
    )

    list_files_parser.add_argument(
        '--manifest', dest='override_manifest', action='store', metavar='<uri>', help='Manifest URL or path to use instead of the CDN one'
    )
    list_files_parser.add_argument('--csv', dest='csv', action='store_true', help='Output in CSV format')
    list_files_parser.add_argument('--tsv', dest='tsv', action='store_true', help='Output in TSV format')
    list_files_parser.add_argument('--json', dest='json', action='store_true', help='Output in JSON format')
    list_files_parser.add_argument(
        '--hashlist', dest='hashlist', action='store_true', help='Output file hash list in hashCheck/sha1sum -c compatible format'
    )
    list_files_parser.add_argument('-f', '--force-refresh', dest='force_refresh', action='store_true', help='Force a refresh of all assets metadata')

    status_parser.add_argument('--offline', dest='offline', action='store_true', help='Only print offline status information, do not login')
    status_parser.add_argument('--json', dest='json', action='store_true', help='Show status in JSON format')

    clean_parser.add_argument(
        '-m,'
        '--delete-metadata', dest='delete_metadata', action='store_true', help='Also delete metadata files. They are kept by default'
    )
    clean_parser.add_argument(
        '-e,'
        '--delete-extras-data', dest='delete_extras_data', action='store_true', help='Also delete extras data files. They are kept by default'
    )

    info_parser.add_argument('--offline', dest='offline', action='store_true', help='Only print info available offline')
    info_parser.add_argument('--json', dest='json', action='store_true', help='Output information in JSON format')
    info_parser.add_argument('-f', '--force-refresh', dest='force_refresh', action='store_true', help='Force a refresh of all assets metadata')

    get_token_parser.add_argument('--json', dest='json', action='store_true', help='Output information in JSON format')
    get_token_parser.add_argument('--bearer', dest='bearer', action='store_true', help='Return fresh bearer token rather than an exchange code')

    edit_parser.add_argument(
        '-i', '--input', dest='input', metavar='<path/name>', action='store', help='The file name (with path) where the list should be read from'
    )
    # not use for now
    # edit_parser.add_argument('--csv', dest='csv', action='store_true', help='Input file is in CSV format')
    # edit_parser.add_argument('--tsv', dest='tsv', action='store_true', help='Input file is in TSV format')
    # edit_parser.add_argument('--json', dest='json', action='store_true', help='Input file is in JSON format')

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
            # noinspection PyProtectedMember,PyUnresolvedReferences
            subparsers = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
            # noinspection PyUnresolvedReferences
            for choice, subparser in subparsers.choices.items():
                if choice in _hidden_commands:
                    continue
                print(f'\nCommand: {choice}')
                print(subparser.format_help())
        elif os.name == 'nt':
            from UEVaultManager.lfs.windows_helpers import double_clicked
            if double_clicked():
                print('Please note that this is not the intended way to run UEVaultManager.')
                print('Follow https://github.com/LaurentOngaro/UEVaultManager#readme to set it up properly')
                subprocess.Popen(['cmd', '/K', 'echo>nul'])
        return

    cli = UEVaultManagerCLI(override_config=args.config_file, api_timeout=args.api_timeout)
    ql = cli.setup_threaded_logging()

    conf_log_level = cli.core.lgd.config.get('UEVaultManager', 'log_level', fallback='info')
    if conf_log_level == 'debug' or args.debug:
        cli.core.verbose_mode = True
        logging.getLogger().setLevel(level=logging.DEBUG)
        # keep requests quiet
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)

    cli.core.create_output_backup = str_to_bool(cli.core.lgd.config.get('UEVaultManager', 'create_output_backup', fallback=True))
    cli.core.create_log_backup = str_to_bool(cli.core.lgd.config.get('UEVaultManager', 'create_log_backup', fallback=True))
    cli.core.verbose_mode = str_to_bool(cli.core.lgd.config.get('UEVaultManager', 'verbose_mode', fallback=False))
    cli.ue_assets_max_cache_duration = int(cli.core.lgd.config.get('UEVaultManager', 'ue_assets_max_cache_duration', fallback=1296000))

    cli.core.ignored_assets_filename_log = cli.core.lgd.config.get('UEVaultManager', 'ignored_assets_filename_log', fallback='')
    cli.core.notfound_assets_filename_log = cli.core.lgd.config.get('UEVaultManager', 'notfound_assets_filename_log', fallback='')
    cli.core.bad_data_assets_filename_log = cli.core.lgd.config.get('UEVaultManager', 'bad_data_assets_filename_log', fallback='')

    cli.core.engine_version_for_obsolete_assets = cli.core.lgd.config.get('UEVaultManager', 'engine_version_for_obsolete_assets', fallback='4.26')

    if cli.core.create_log_backup:
        cli.create_log_file_backup()

    # open log file for assets if necessary
    cli.core.setup_assets_logging()
    cli.core.egs.notfound_logger = cli.core.notfound_logger
    cli.core.egs.ignored_logger = cli.core.ignored_logger

    # if --yes is used as part of the subparsers arguments manually set the flag in the main parser.
    if '-y' in extra or '--yes' in extra:
        args.yes = True

    # technically args.func() with set defaults could work (see docs on subparsers)
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
            cli.cleanup(args)
        elif args.subparser_name == 'get-token':
            cli.get_token(args)
        elif args.subparser_name in {'edit', 'edit-assets'}:
            cli.edit_assets(args)
    except KeyboardInterrupt:
        cli.logger.info('Command was aborted via KeyboardInterrupt, cleaning up...')

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

    cli.core.clean_exit()
    ql.stop()
    exit(0)


if __name__ == '__main__':
    # required for pyinstaller on Windows, does nothing on other platforms.
    freeze_support()
    main()
