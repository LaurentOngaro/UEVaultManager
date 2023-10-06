# coding=utf-8
"""
Implementation for:
- UEVaultManagerCLI: command line interface for UEVaultManager.
"""
import argparse
import csv
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import webbrowser
from collections import namedtuple
from datetime import datetime
from logging.handlers import QueueListener
from multiprocessing import freeze_support, Queue as MPQueue
from platform import platform
from shutil import rmtree
from tkinter import filedialog

import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
# noinspection PyPep8Naming
from UEVaultManager import __codename__ as UEVM_codename, __version__ as UEVM_version
from UEVaultManager.api.egs import create_empty_assets_extra, GrabResult, is_asset_obsolete
from UEVaultManager.api.uevm import UpdateSeverity
from UEVaultManager.core import AppCore, default_datetime_format
from UEVaultManager.lfs.utils import copy_folder, path_join
from UEVaultManager.models.Asset import Asset
from UEVaultManager.models.csv_sql_fields import csv_sql_fields, CSVFieldState, get_csv_field_name_list, is_on_state, is_preserved
from UEVaultManager.models.exceptions import InvalidCredentialsError
from UEVaultManager.models.UEAssetDbHandlerClass import UEAssetDbHandler
from UEVaultManager.models.UEAssetScraperClass import UEAssetScraper
from UEVaultManager.tkgui.main import init_gui
from UEVaultManager.tkgui.modules.cls.ChoiceFromListWindowClass import ChoiceFromListWindow
from UEVaultManager.tkgui.modules.cls.DisplayContentWindowClass import DisplayContentWindow
from UEVaultManager.tkgui.modules.cls.ProgressWindowClass import ProgressWindow
from UEVaultManager.tkgui.modules.cls.SaferDictClass import SaferDict
from UEVaultManager.tkgui.modules.cls.UEVMGuiClass import UEVMGui
from UEVaultManager.tkgui.modules.cls.UEVMGuiHiddenRootClass import UEVMGuiHiddenRoot
from UEVaultManager.tkgui.modules.functions import box_message, box_yesno, create_file_backup, custom_print, \
    make_modal, show_progress  # simplier way to use the custom_print function
from UEVaultManager.tkgui.modules.functions import json_print_key_val
from UEVaultManager.tkgui.modules.types import DataSourceType
from UEVaultManager.utils.cli import check_and_create_file, get_boolean_choice, get_max_threads, remove_command_argument, str_is_bool, str_to_bool
from UEVaultManager.utils.HiddenAliasSubparsersActionClass import HiddenAliasSubparsersAction

# add the parent folder to the sys.path list, to run the script from the command line without import module error
# must be done before importing project module (ex: global.py)
# this code has been replaced by using script to launch the application as a module (as it the path is added automatically)
# path = os.path.realpath(os.path.dirname(os.path.dirname(__file__)))
# if path not in sys.path:
#     sys.path.insert(0, path)

logging.basicConfig(format='[%(name)s] %(levelname)s: %(message)s', level=logging.INFO)


def init_gui_args(args, additional_args=None) -> None:
    """
    Initialize the GUI arguments using the CLI arguments.
    :param args: args of the command line.
    :param additional_args: dict of additional arguments to add.
    """
    # args can not be used as it because it's an object that mainly run as a dict (but it's not)
    # so we need to convert it to a dict first
    temp_dict = vars(args)
    temp_dict['csv'] = True  # force csv output
    temp_dict['gui'] = True
    if additional_args is not None:
        temp_dict.update(additional_args)
    # create a SaferDict object from the dict (it will avoid errors when trying to access non-existing keys)
    gui_g.UEVM_cli_args = SaferDict({})
    # copy the dict content to the SaferDict object
    gui_g.UEVM_cli_args.copy_from(temp_dict)


def init_progress_window(text: str, args, logger=None, callback: callable = None) -> (bool, ProgressWindow):
    """
    Initialize the progress window.
    :param text: text to display in the progress window.
    :param args: args of the command line.
    :param logger: logger to use.
    :param callback: callback function to call while progress updating.
    :return: (True if the UEVMGui window already existed | False, ProgressWindow).
    """
    gui_g.UEVM_log_ref = logger

    # check if the GUI is already running
    if gui_g.UEVM_gui_ref is None:
        # create a fake root because ProgressWindow must always be a top level window
        gui_g.UEVM_gui_ref = UEVMGuiHiddenRoot()
        uewm_gui_exists = False
    else:
        uewm_gui_exists = True
    force_refresh = True if args.force_refresh else False
    pw = show_progress(
        parent=gui_g.UEVM_gui_ref,
        text=text,
        quit_on_close=not uewm_gui_exists,
        function=callback,
        function_parameters={
            'filter_category': gui_g.UEVM_filter_category,
            'force_refresh': force_refresh,
        }
    )
    return uewm_gui_exists, pw


def init_display_window(logger=None, message: str = 'Starting command...') -> (bool, DisplayContentWindow):
    """
    Initialize the display window.
    :param logger: logger to use.
    :param message: message to display at start.
    :return: (True if the UEVMGui window already existed | False, DisplayContentWindow).
    """
    gui_g.UEVM_log_ref = logger

    # check if the GUI is already running
    if gui_g.UEVM_gui_ref is None:
        # create a fake root because DisplayContentWindow must always be a top level window
        gui_g.UEVM_gui_ref = UEVMGuiHiddenRoot()
        uewm_gui_exists = False
    else:
        uewm_gui_exists = True
    if gui_g.display_content_window_ref is not None:
        gui_g.display_content_window_ref.close_window()

    gui_g.display_content_window_ref = DisplayContentWindow(title='UEVM command output', quit_on_close=not uewm_gui_exists)
    gui_g.display_content_window_ref.display(message, False)
    # make_modal(gui_g.display_content_window_ref) # no modal here, will prevent display update by the function

    return uewm_gui_exists, gui_g.display_content_window_ref


class UEVaultManagerCLI:
    """
    Command line interface for UEVaultManager.
    :param override_config: path to a config file to use instead of the default one.
    :param api_timeout: timeout for API requests.
    """
    is_gui = False  # class property to be accessible by static methods
    release_index = -1  # the release id selected for an asset installation

    def __init__(self, override_config=None, api_timeout=(7, 7)):  # timeout could be a float or a tuple  (connect timeout, read timeout) in s
        self.core = AppCore(override_config, timeout=api_timeout)
        self.logger = logging.getLogger('Cli')
        self.logging_queue = None

    @staticmethod
    def _print_json(data, pretty=False):
        if pretty:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            print(json.dumps(data))

    @staticmethod
    def _log_and_gui_message(log_function: callable, message: str, quit_on_error=True) -> None:
        """
        Wrapper to log a message using a log function AND use a messagebox to display the message if the gui is active.
        :param log_function: function to use to log.
        :param message: message to log.
        :param quit_on_error: whether we quit the application.
        """
        if UEVaultManagerCLI.is_gui:
            if gui_g.display_content_window_ref is not None:
                gui_g.display_content_window_ref.close_window()
            box_message(message, level='error' if quit_on_error else 'warning')  # level='error' will force the application to quit
            # log_function() is called in box_message
        else:
            log_function(message)
            name = log_function.__name__
            # check if name contains 'error' or 'critical' to quit the application
            if quit_on_error and ('error' in name or 'critical' in name or 'fatal' in name):
                sys.exit(1)

    @staticmethod
    def _log_and_gui_display(log_function: callable, message: str) -> None:
        """
        Wrapper to log a message using a log function AND use a DisplayWindows to display the message if the gui is active.
        :param log_function: function to use to log.
        :param message: message to log.
        """
        log_function(message)
        if UEVaultManagerCLI.is_gui and gui_g.display_content_window_ref is not None:
            gui_g.display_content_window_ref.display(message)

    def _init_data_for_gui(self, args) -> (str, DataSourceType):
        data_source_type = DataSourceType.FILE
        use_database = False
        use_input = False
        try:
            use_database = args.database
            use_input = args.input
        except AttributeError:
            pass
        if use_database:
            data_source = args.database
            data_source_type = DataSourceType.SQLITE
            self.logger.info(f'The database {data_source} will be used to read data from')
        elif use_input:
            data_source = args.input
            self.logger.info(f'The file {data_source} will be used to read data from')
        else:
            data_source = gui_g.s.csv_filename
            self.logger.warning('The file to read data from has not been set by the --input command option. The default file name will be used.')

        data_source = gui_fn.path_from_relative_to_absolute(data_source)
        data_source = os.path.normpath(data_source)

        gui_g.s.app_icon_filename = gui_fn.path_from_relative_to_absolute(gui_g.s.app_icon_filename)
        gui_g.UEVM_log_ref = self.logger
        gui_g.UEVM_cli_ref = self
        return data_source, data_source_type

    def setup_threaded_logging(self) -> QueueListener:
        """
        Setup logging for the CLI.
        """
        self.logging_queue = MPQueue(-1)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(name)s] %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        ql = QueueListener(self.logging_queue, handler)
        ql.start()
        return ql

    def create_log_file_backup(self) -> None:
        """
        Create a backup of the log files.
        """
        create_file_backup(self.core.ignored_assets_filename_log, logger=self.logger, path=self.core.uevmlfs.path)
        create_file_backup(self.core.notfound_assets_filename_log, logger=self.logger, path=self.core.uevmlfs.path)
        create_file_backup(self.core.bad_data_assets_filename_log, logger=self.logger, path=self.core.uevmlfs.path)
        create_file_backup(self.core.scan_assets_filename_log, logger=self.logger, path=self.core.uevmlfs.path)

    # noinspection PyUnusedLocal
    def create_asset_from_data(
        self, item, asset_id: str, no_text_data: str, no_int_data: int, no_float_data: float, bool_true_data: bool, bool_false_data: bool
    ) -> (str, dict):
        """
        Create a dict containing all the data for an asset.
        :param item: item to get data from.
        :param asset_id: id of the asset.
        :param no_text_data: text to use if no text data is found.
        :param no_int_data: int value to use if no int data is found.
        :param no_float_data: float value to use if no float data is found.
        :param bool_true_data: bool (True) value to use if no bool data is found.
        :param bool_false_data: bool (False) value to use if no bool data is found.
        :return: (asset_id, dict containing all the data for an asset).

        Notes:
            This method is only used when getting OWNED assets data with the "old" method used by legendary
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
        date_added = datetime.now().strftime(default_datetime_format)
        extra_data = None
        try:
            extra_data = self.core.uevmlfs.get_item_extra(item.app_name)
        except AttributeError as error:
            self.logger.warning(f'Error getting extra data for {item.app_name} : {error!r}')
        if extra_data is None:
            extra_data = create_empty_assets_extra(item.app_name)
        origin = 'Marketplace'  # by default the asset are from the "MarketPlace"
        asset_url = extra_data.get('asset_url', no_text_data)
        review = extra_data.get('review', no_int_data)
        price = extra_data.get('price', no_float_data)
        discount_price = extra_data.get('discount_price', no_float_data)
        supported_versions = extra_data.get('supported_versions', no_text_data)
        page_title = extra_data.get('page_title', no_text_data)
        grab_result = extra_data.get('grab_result', GrabResult.NO_ERROR.name)
        # next fields are missing in some assets pages
        discount_percentage = extra_data.get('discount_percentage', no_int_data)
        discounted = extra_data.get('discounted', bool_false_data)
        owned = extra_data.get('owned', bool_true_data)
        obsolete = is_asset_obsolete(supported_versions, self.core.engine_version_for_obsolete_assets)
        try:
            values = (
                # be ins the same order as csv_sql_fields keys, with explufind the SQL_ONLY fields
                asset_id  # 'asset_id'
                , item.app_name  # 'App name'
                , item.app_title  # 'App title'
                , category  # 'Category'
                , review  # 'Review'
                , metadata['developer']  # 'Developer'
                , metadata['description']  # 'Description'
                , metadata['status']  # 'Status'
                , discount_price  # 'Discount price'
                , discount_percentage  # 'Discount percentage'
                , discounted  # 'Discounted'
                , owned  # 'Owned'
                , obsolete  # 'Obsolete'
                , supported_versions  # 'Supported versions'
                , grab_result  # 'Grab result'
                , price  # 'Price'
                , no_float_data  # 'Old price'
                # User Fields
                , no_text_data  # 'Comment'
                , no_float_data  # 'Stars'
                , bool_false_data  # 'Must buy'
                , no_text_data  # 'Test result
                , no_text_data  # 'Installed folders'
                , no_text_data  # 'Alternative'
                , origin  # 'Origin
                , bool_false_data  # 'Added manually'
                # less important fields
                , page_title  # 'Page title'
                , thumbnail_url  # 'Image' with 488 height
                , asset_url  # 'Url'
                , compatible_versions  # compatible_versions
                , date_added  # 'Date added'
                , metadata['creationDate']  # 'Creation date'
                , metadata['lastModifiedDate']  # 'Update date'
                , item.app_version('Windows')  # 'UE version'
                , uid  # 'Uid'
            )
            record = dict(zip(get_csv_field_name_list(), values))
        except TypeError:
            self.logger.error(f'Could not create record for {item.app_name}')

        return asset_id, record

    def auth(self, args) -> None:
        """
        Handle authentication.
        :param args: options passed to the command.
        """
        uewm_gui_exists = False
        dw = None
        if UEVaultManagerCLI.is_gui:
            uewm_gui_exists, dw = init_display_window(self.logger)

        if args.auth_delete:
            if not self.core.uevmlfs.userdata:
                self._log_and_gui_display(self.logger.info, "You are not logged in. You have to run the auth command to log in.")
                return
            else:
                self.core.uevmlfs.invalidate_userdata()
                self._log_and_gui_display(self.logger.info, "User data deleted. You'll have to run the auth command again to log in.")
                return
        try:
            self._log_and_gui_display(self.logger.info, 'Testing existing login data if present...')
            if self.core.login():
                msg = 'Stored credentials are still valid, if you wish to switch to a different account.\nRun "UEVaultManager auth --delete" and try again.'
                msg += '\nOr check the "Delete auth (login)" options in the Options panel.' if uewm_gui_exists else ''
                self._log_and_gui_display(self.logger.info, msg)
                return
        except ValueError:
            pass
        except InvalidCredentialsError:
            self.core.uevmlfs.invalidate_userdata()
            message = 'Stored credentials were found but were no longer valid. Continuing with login...'
            self._log_and_gui_message(self.logger.error, message, quit_on_error=False)

        # Force an update check and notice in case there are API changes
        self.core.check_for_updates(force=True)
        self.core.force_show_update = True

        if args.import_egs_auth:
            self._log_and_gui_display(self.logger.info, 'Importing login session from the Epic Launcher...')
            try:
                if self.core.auth_import():
                    self._log_and_gui_display(self.logger.info, 'Successfully imported login session from EGS!')
                    self._log_and_gui_display(self.logger.info, f'Now logged in as user "{self.core.uevmlfs.userdata["displayName"]}"')
                    return
                else:
                    self._log_and_gui_display(self.logger.warning, 'Login session from EGS seems to no longer be valid.')
                    self.core.clean_exit(1)
            except Exception as error:
                message = f'No EGS login session found, please log in manually. (Exception: {error!r})'
                self._log_and_gui_message(self.logger.critical, message)

        exchange_token = ''
        auth_code = ''
        if not args.auth_code and not args.session_id:
            # only import here since pywebview import is slow
            from UEVaultManager.utils.WebviewWindowClass import webview_available, do_webview_login

            if not webview_available or args.no_webview or self.core.webview_killswitch:
                # unfortunately the captcha stuff makes a complete CLI login flow kinda impossible right now...
                custom_print('Please log in via the epic web login!')
                url = 'https://legendary.gl/epiclogin'
                webbrowser.open(url)
                custom_print(f'If the web page did not open automatically, please manually open the following URL: {url}')
                auth_code = input('Please enter the "authorizationCode" value from the JSON response: ')
                auth_code = auth_code.strip()
                if auth_code[0] == '{':
                    tmp = json.loads(auth_code)
                    auth_code = tmp['authorizationCode']
                else:
                    auth_code = auth_code.strip('"')
            else:
                if do_webview_login(callback_code=self.core.auth_ex_token):
                    self._log_and_gui_display(
                        self.logger.info, f'Successfully logged in as "{self.core.uevmlfs.userdata["displayName"]}" via WebView'
                    )
                else:
                    message = 'WebView login attempt failed, please see log for details.'
                    self._log_and_gui_message(self.logger.error, message, quit_on_error=False)
                if uewm_gui_exists:
                    dw.close_window()
                return
        elif args.session_id:
            exchange_token = self.core.auth_sid(args.session_id)
        elif args.auth_code:
            auth_code = args.auth_code
        elif args.ex_token:
            exchange_token = args.ex_token

        if not exchange_token and not auth_code:
            self.logger.critical('No exchange token/authorization code, can not log in.')
            return

        if exchange_token and self.core.auth_ex_token(exchange_token):
            self.logger.info(f'Successfully logged in as "{self.core.uevmlfs.userdata["displayName"]}"')
        elif auth_code and self.core.auth_code(auth_code):
            self.logger.info(f'Successfully logged in as "{self.core.uevmlfs.userdata["displayName"]}"')
        else:
            message = 'Login attempt failed, please see log for details.'
            self._log_and_gui_message(self.logger.error, message)

        if not uewm_gui_exists:
            gui_g.UEVM_gui_ref.mainloop()

    def list_assets(self, args) -> None:
        """
        List assets in the vault.
        :param args: options passed to the command.
        """

        def update_and_merge_csv_record_data(_asset_id: str, _asset_data: {}, _items_in_file, _no_data_value) -> []:
            """
            Updates the data of the asset with the data from the items in the file.
            :param _asset_id: id of the asset to update.
            :param _asset_data: data of the asset to update.
            :param _items_in_file: list of items in the file.
            :param _no_data_value: value to use when no data is available.
            :return: list of values to be written in the CSV file.
            """
            # merge data from the items in the file (if exists) and those get by the application
            # items_in_file must be a dict of dicts
            csv_fields_count = len(get_csv_field_name_list())
            _csv_record = list(_asset_data.values())  # we need a list for the CSV comparison, not a dict
            if _items_in_file.get(_asset_id):
                item_in_file = _items_in_file.get(_asset_id)
                if len(item_in_file.keys()) != csv_fields_count:
                    self.logger.error(
                        f'In the existing file, asset {_asset_id} has not the same number of keys as the CSV headings. This asset is ignored and its values will be overwritten'
                    )
                    return _csv_record
                else:
                    # loops through its columns to UPDATE the data with EXISTING VALUE if its state is PRESERVED
                    # !! no data cleaning must be done here !!!!
                    price_index = 0
                    _price = float(_no_data_value)
                    old_price = float(_no_data_value)
                    for index, csv_field in enumerate(get_csv_field_name_list()):
                        preserved_value_in_file = is_preserved(csv_field_name=csv_field)
                        value = item_in_file.get(csv_field, None)
                        if value is None:
                            self.logger.warning(f'In the existing data, asset {_asset_id} has no column named {csv_field}.')
                            continue

                        # get rid of 'None' values in CSV file
                        if value == gui_g.s.empty_cell:
                            _csv_record[index] = ''
                            continue

                        value = str(value)
                        # Get the old price in the previous file
                        if csv_field == 'Price':
                            price_index = index
                            _price = gui_fn.convert_to_float(_csv_record[price_index])
                            old_price = gui_fn.convert_to_float(
                                item_in_file[csv_field]
                            )  # Note: the 'old price' is the 'price' saved in the file, not the 'old_price' in the file
                        elif csv_field == 'Origin':
                            # all the folders when the asset came from are stored in a comma separated list
                            if isinstance(value, str):
                                folder_list = value.split(',')
                            else:
                                folder_list = value if value else []
                            # add the new folder to the list without duplicates
                            if _csv_record[index] not in folder_list:
                                folder_list.append(_csv_record[index])
                            # update the list in the CSV record
                            _csv_record[index] = ','.join(folder_list)

                        if preserved_value_in_file:
                            _csv_record[index] = str_to_bool(value) if str_is_bool(value) else value
                    # end for key, state in csv_sql_fields.items()
                    if price_index > 0:
                        _csv_record[price_index + 1] = old_price
                # end ELSE if len(item_in_file.keys()) != csv_fields_count
            # end if _items_in_file.get(_asset_id)
            # print(f'debug here')
            return _csv_record

        # end update_and_merge_csv_record_data

        def update_and_merge_json_record_data(_asset, _items_in_file, _no_float_value: float, _no_bool_false_value: bool) -> dict:
            """
            Updates the data of the asset with the data from the items in the file.
            :param _asset: asset to update.
            :param _items_in_file: list of items in the file.
            :param _no_float_value:  value to use when no float data is available.
            :param _no_bool_false_value: value (False) to use when no bool data is available.
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
                for field, state in csv_sql_fields.items():
                    preserved_value_in_file = is_preserved(csv_field_name=field)
                    if preserved_value_in_file and _items_in_file[_asset_id].get(field):
                        _json_record[field] = _items_in_file[_asset_id][field]

                # Get the old price in the previous file
                try:
                    _price = float(_json_record['Price'])
                    old_price = float(
                        _items_in_file[_asset_id]['Price']
                    )  # Note: the 'old price' is the 'price' saved in the file, not the 'old_price' in the file
                except Exception as _error:
                    self.logger.warning(f'Old price values can not be converted for asset {_asset_id}\nError:{_error!r}')
                _json_record['Old price'] = old_price
            return _json_record

        # end def update_and_merge_json_record_data

        if self.core.create_log_backup:
            self.create_log_file_backup()

        # open log file for assets if necessary
        self.core.setup_assets_loggers()
        self.core.egs.notfound_logger = self.core.notfound_logger
        self.core.egs.ignored_logger = self.core.ignored_logger

        output = sys.stdout  # by default, we output to sys.stdout

        if args.output:
            file_src = args.output
            # test if the folder is writable
            if not check_and_create_file(file_src):
                message = f'Could not create result file {file_src}. Quiting Application...'
                self._log_and_gui_message(self.logger.critical, message)

        self.logger.info('Login...')
        if not self.core.login(raise_error=False):
            message = 'You are not connected or log in failed.\nYou should log first or check your credential.\n.'
            self._log_and_gui_message(self.logger.error, message)
            return

        if args.force_refresh:
            self.logger.info(
                'force_refresh option is active ...\nRefreshing asset list, this will take several minutes to acheived depending on the internet connection...'
            )
        else:
            self.logger.info('Getting asset list... (this may take a while)')

        if args.filter_category and args.filter_category != gui_g.s.default_value_for_all:
            gui_g.UEVM_filter_category = args.filter_category
            self.logger.info(f'The String "{args.filter_category}" will be search in Assets category')

        gui_g.progress_window_ref = None
        pw = None
        if UEVaultManagerCLI.is_gui:
            uewm_gui_exists, pw = init_progress_window(text='Updating Assets List', args=args, logger=self.logger, callback=self.core.get_asset_list)
            if uewm_gui_exists:
                # if the main gui is running, we already have a tk.mainloop running
                # we need to constantly update the progress bar
                while not pw.must_end:
                    pw.update()
            else:
                # if the main gui is not running, we need to start a tk.mainloop
                pw.mainloop()
            items = pw.get_result()
        else:
            items = self.core.get_asset_list(platform='Windows', filter_category=args.filter_category, force_refresh=args.force_refresh)

        if args.include_non_asset:
            na_items = self.core.get_non_asset_library_items(skip_ue=False)
            items.extend(na_items)

        if not items:
            self.logger.info('No assets found!')
            return

        no_int_data = 0
        no_float_value = 0.0
        no_text_data = ''
        no_bool_true_data = True
        no_bool_false_data = False
        cpt = 0
        cpt_max = len(items)

        # use a dict to store records and avoid duplicates (asset with the same asset_id and a different asset_name)
        assets_to_output = {}
        # create a minimal and full dict of data from existing assets
        assets_in_file = {}

        # sort assets by name in reverse (to have the latest version first
        items = sorted(items, key=lambda x: x.app_name.lower(), reverse=True)

        if gui_g.progress_window_ref is not None:
            gui_g.progress_window_ref.reset(new_value=0, new_text="Merging asset's data...", new_max_value=cpt_max)
        for item in items:
            if gui_g.progress_window_ref is not None and not gui_g.progress_window_ref.update_and_continue(increment=1):
                return
            cpt += 1
            # Note:
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
            create_file_backup(args.output)

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
                    self.logger.warning(f'Could not read CSV record from the file {file_src}')
                # reopen file for writing
                output = open(file_src, 'w', encoding='utf-8')
            # end if args.output:

            writer = csv.writer(output, dialect='excel-tab' if args.tsv else 'excel', lineterminator='\n')
            writer.writerow(get_csv_field_name_list())
            cpt = 0
            if gui_g.progress_window_ref is not None:
                gui_g.progress_window_ref.reset(new_value=0, new_text="Writing assets into csv file...", new_max_value=len(assets_to_output.items()))
            for asset in sorted(assets_to_output.items()):
                asset_id = asset[0]
                if gui_g.progress_window_ref is not None and not gui_g.progress_window_ref.update_and_continue(increment=1):
                    return
                asset_data = asset[1]
                for key in asset_data.keys():
                    # clean the asset data by removing the columns that are not in the csv field name list
                    ignore_in_csv = is_on_state(csv_field_name=key, states=[CSVFieldState.ASSET_ONLY, CSVFieldState.SQL_ONLY], default=False)
                    if ignore_in_csv:
                        print(f'{key} must be ignored in CSV. Removing it from the asset data')
                        del (asset_data[key])

                if len(assets_in_file) > 0:
                    csv_record_merged = update_and_merge_csv_record_data(asset_id, asset_data, assets_in_file, no_int_data)
                else:
                    csv_record_merged = list(asset_data.values())
                cpt += 1
                writer.writerow(csv_record_merged)

        # end if args.csv or args.tsv:

        if args.json:
            if args.output:
                file_src = args.output
                # If the output file exists, we read its content to keep some data
                try:
                    with open(file_src, 'r', encoding='utf-8') as output:
                        assets_in_file = json.load(output)
                except (FileExistsError, OSError, UnicodeDecodeError, StopIteration, json.decoder.JSONDecodeError):
                    self.logger.warning(f'Could not read Json record from the file {args.output}')
                # reopen file for writing
                output = open(file_src, 'w', encoding='utf-8')
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
                        message = f'Could not write Json record for {asset_id} into {args.output}\nError:{error!r}'
                        self.logger.error(message)

                json.dump(json_content, output, indent=2)
            except OSError:
                message = f'Could not write list result to {args.output}'
                self._log_and_gui_message(self.logger.error, message, quit_on_error=False)

            # end if args.json:

        if args.csv or args.tsv or args.json or UEVaultManagerCLI.is_gui:
            # close the opened file
            if output is not None:
                output.close()
            self.logger.info(
                f'\n======\n{cpt} assets have been printed or saved (without duplicates due to different UE versions)\nOperation Finished\n======\n'
            )
            if UEVaultManagerCLI.is_gui:
                # During the editabletable initial rebuild_data process, the window will not close
                # So we try to close it several times
                # max_tries = 3
                # pw.quit_on_close = True  # gentle quit
                # tries = 0
                # while progress_window is not None and pw.winfo_viewable() and tries < max_tries:
                #     pw.close_window()
                #     time.sleep(0.2)
                #     tries += 1
                # pw.quit_on_close = False  # force destroy the window
                # pw.close_window()
                pw.quit_on_close = False
                pw.close_window(destroy_window=True)
            return

        # here, no other output has been done before, so we print the asset in a quick format to the console
        print('\nAvailable UE Assets:')
        for asset in items:
            version = asset.app_version('Windows')
            print(f' * {asset.app_title.strip()} (Asset name: {asset.app_name} | Version: {version})')
        print(f'\nTotal: {len(items)}')

    def list_files(self, args):
        """
        List files for a given asset name or manifest url/path.
        :param args: options passed to the command.
        :return:
        """
        if not args.override_manifest and not args.app_name:
            print('You must provide either a manifest url/path or asset name!')
            return

        # check if we even need to log in
        if args.override_manifest:
            self.logger.info(f'Loading manifest from "{args.override_manifest}"')
            manifest_data, _ = self.core.get_uri_manifest(args.override_manifest)
        else:
            self.logger.info(f'Login and downloading manifest for {args.app_name}')
            if not self.core.login(raise_error=False):
                message = 'You are not connected or log in failed.\nYou should log first or check your credential.\nCannot continue with download process.'
                self._log_and_gui_message(self.logger.error, message, quit_on_error=False)
                return
            update_meta = args.force_refresh
            item = self.core.get_item(args.app_name, update_meta=update_meta)
            if not item:
                message = f'Could not fetch metadata for "{args.app_name}" (check spelling/account ownership)'
                self._log_and_gui_message(self.logger.error, message, quit_on_error=False)
                return

            manifest_data, _, status_code = self.core.get_cdn_manifest(item, platform='Windows')

        manifest = self.core.load_manifest(manifest_data)
        files = sorted(manifest.file_manifest_list.elements, key=lambda a: a.filename.lower())

        content = ''
        if args.hashlist:
            for fm in files:
                content += f'{fm.hash.hex()} *{fm.filename}\n'
        elif args.csv or args.tsv:
            writer = csv.writer(sys.stdout, dialect='excel-tab' if args.tsv else 'excel', lineterminator='\n')
            writer.writerow(['path', 'hash', 'size', 'install_tags'])
            writer.writerows((fm.filename, fm.hash.hex(), fm.file_size, '|'.join(fm.install_tags)) for fm in files)
        elif args.json:
            _files = [
                dict(filename=fm.filename, sha_hash=fm.hash.hex(), install_tags=fm.install_tags, file_size=fm.file_size, flags=fm.flags)
                for fm in files
            ]
            print(content)
            return self._print_json(_files, args.pretty_json)
        else:
            install_tags = set()
            for fm in files:
                content += fm.filename + '\n'
                for t in fm.install_tags:
                    install_tags.add(t)
            if install_tags:
                # use the log output so this isn't included when piping file list into file
                self.logger.info(f'Install tags: {", ".join(sorted(install_tags))}')

        if UEVaultManagerCLI.is_gui:
            uewm_gui_exists, _ = init_display_window(self.logger)
            custom_print(content, keep_mode=False)  # as it, next print will not keep the content
            if not uewm_gui_exists:
                gui_g.UEVM_gui_ref.mainloop()
        else:
            print(content)

    def status(self, args) -> None:
        """
        Print the information about the vault and the available assets.
        :param args: options passed to the command.
        """
        uewm_gui_exists = False
        if UEVaultManagerCLI.is_gui:
            uewm_gui_exists, _ = init_display_window(self.logger)

        if not args.offline:
            try:
                if not self.core.login(raise_error=False):
                    message = 'You are not connected or log in failed.\nYou should log first or check your credential.\n'
                    self._log_and_gui_message(self.logger.error, message, quit_on_error=False)
                    return
            except ValueError:
                pass
            # if automatic checks are off force an update here
            self.core.check_for_updates(force=True)

        if not self.core.uevmlfs.userdata:
            user_name = '<not logged in>'
            args.offline = True
        else:
            user_name = self.core.uevmlfs.userdata['displayName']

        cache_information = self.core.uevmlfs.get_assets_cache_info()
        update_information = self.core.uevmlfs.get_online_version_saved()
        last_update = update_information.get('last_update', '')
        update_information = update_information.get('data', None)
        last_cache_update = cache_information.get('last_update', '')
        if last_update != '':
            last_update = time.strftime("%x", time.localtime(last_update))
        if last_cache_update != '':
            last_cache_update = time.strftime("%x", time.localtime(last_cache_update))

        json_content = {
            'Epic account': user_name,  #
            'Last data update': last_update,
            'Last cache update': last_cache_update,
            'Config directory': self.core.uevmlfs.path,
            'Platform': f'{platform()} ({os.name})',
            'Current version': f'{UEVM_version} - {UEVM_codename}',
        }
        if not args.offline:
            owned_assets = len(self.core.get_asset_list(update_assets=args.force_refresh))
            json_content['Assets owned'] = owned_assets
            json_content['Update available'] = 'yes' if self.core.update_available else 'no'

            if self.core.update_available and update_information is not None:
                json_content['Update info'] = '\n'
                json_content['New version'] = f'{update_information["version"]} - {update_information["codename"]}'
                json_content['Release summary'] = update_information['summary']
                json_content['Release Url'] = update_information['release_url']
                json_content['Update recommendation'] = update_information['severity']

        if args.json:
            return self._print_json(json_content, args.pretty_json)

        if UEVaultManagerCLI.is_gui:
            json_print_key_val(json_content, output_on_gui=True)
            if not uewm_gui_exists:
                gui_g.UEVM_gui_ref.mainloop()
        else:
            json_print_key_val(json_content)

        # prevent update message on close
        self.core.update_available = False

    def info(self, args) -> None:
        """
        Print information about a given Asset name or manifest url/path.
        :param args: options passed to the command.
        """
        name_or_path = args.app_name_or_manifest or args.app_name
        show_all_info = args.all
        app_name = manifest_uri = None
        if os.path.exists(name_or_path) or name_or_path.startswith('http'):
            manifest_uri = name_or_path
        else:
            app_name = name_or_path
        if not args.offline and not manifest_uri:
            try:
                if not self.core.login(raise_error=False):
                    message = 'You are not connected or log in failed.\nYou should log first or check your credential.\n'
                    self._log_and_gui_message(self.logger.error, message, quit_on_error=False)
                    return
            except ValueError:
                pass

        # lists that will be printed or turned into JSON data
        info_items = dict(assets=[], manifest=[], install=[])
        InfoItem = namedtuple('InfoItem', ['name', 'json_name', 'value', 'json_value'])

        update_meta = not args.offline and args.force_refresh

        # check the item using the UEVM method (old)
        item = self.core.get_item(app_name, update_meta=update_meta, platform='Windows')
        message = f'Asset information for "{app_name}" is missing, this may be due to the asset not being available on the selected platform or currently logged-in account.'
        if item and not self.core.asset_available(item, platform='Windows'):
            self._log_and_gui_message(self.logger.warning, message)
            args.offline = True
        else:
            # check the item using the EGS method (new)
            try:
                json_data_egs, json_message = UEAssetScraper.read_json_file(app_name)
                if json_message != '':
                    self._log_and_gui_message(self.logger.warning, json_message, quit_on_error=False)
                    item = None
                else:
                    json_data_uevm = UEAssetScraper.json_data_mapping(json_data_egs)
                    item = Asset.from_json(json_data_uevm)  # create an object from the asset class using the json data
            except (Exception, ):
                item = None
        if not item or item is None:
            self._log_and_gui_message(self.logger.warning, message, quit_on_error=False)
            args.offline = True
        manifest_data = None
        install_tags = {''}

        # entitlements = None
        # load installed manifest or URI
        if args.offline or manifest_uri:
            if manifest_uri and manifest_uri.startswith('http'):
                r = self.core.egs.unauth_session.get(manifest_uri)
                r.raise_for_status()
                manifest_data = r.content
            elif manifest_uri and os.path.exists(manifest_uri):
                with open(manifest_uri, 'rb') as file:
                    manifest_data = file.read()
            else:
                self.logger.info('Asset not installed and offline mode enabled, can not load manifest.')
        elif item:
            # entitlements = self.core.egs.get_user_entitlements()
            try:
                egl_meta, status_code = self.core.egs.get_item_info(item.namespace, item.catalog_item_id)
                if status_code != 200:
                    self._log_and_gui_display(
                        self.logger.error,
                        f'\nYou can only get information about assets you own !\nFailed to fetch metadata for {item.app_name}: reponse code = {status_code}'
                    )
                    return
            except (Exception, ) as error:
                self._log_and_gui_display(
                    self.logger.error,
                    f'\nYou can only get information about assets you own !\nFailed to fetch metadata for {item.app_name}: {error!r}'
                )
                return
            item.metadata = egl_meta
            try:
                # Get manifest if asset exists for current platform
                if 'Windows' in item.asset_infos:
                    manifest_data, base_urls, status_code = self.core.get_cdn_manifest(item, 'Windows')
            except (Exception, ) as error:
                if error.response.status_code == 404:
                    message = f'\nThe manifest data is not available for the assets {item.app_name}. You can try to install it using the Epic Game Launcher'
                else:
                    message = f'\nYou can only get information about assets you own!\nFailed to get manifest for the asset {item.app_name}'
                self._log_and_gui_display(self.logger.error, message)
                return
        if item:
            asset_infos = info_items['assets']
            asset_infos.append(InfoItem('Asset name', 'app_name', item.app_name, item.app_name))
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
            manifest_info.append(InfoItem('Manifest asset name', 'app_name', manifest.meta.app_name, manifest.meta.app_name))
            manifest_info.append(InfoItem('Build version', 'build_version', manifest.meta.build_version, manifest.meta.build_version))
            manifest_info.append(InfoItem('Build ID', 'build_id', manifest.meta.build_id, manifest.meta.build_id))
            if show_all_info:
                manifest_info.append(InfoItem('Launch EXE', 'launch_exe', manifest.meta.launch_exe or 'N/A', manifest.meta.launch_exe))
                manifest_info.append(
                    InfoItem('Launch Command', 'launch_command', manifest.meta.launch_command or '(None)', manifest.meta.launch_command)
                )
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

                if manifest.meta.uninstall_action_path:
                    human_list = [
                        f'Uninstaller path: {manifest.meta.uninstall_action_path}',
                        f'Uninstaller args: {manifest.meta.uninstall_action_args or "(None)"}',
                    ]
                    manifest_info.append(
                        InfoItem(
                            'Uninstaller', 'uninstaller', human_list,
                            dict(path=manifest.meta.uninstall_action_path, args=manifest.meta.uninstall_action_args)
                        )
                    )
                else:
                    manifest_info.append(InfoItem('Uninstaller', 'uninstaller', None, None))

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
            self.core.uevmlfs.set_asset_size(item.app_name, total_size)  # update the global list AND save it into a json file
            file_size = '{:.02f} GiB'.format(total_size / 1024 / 1024 / 1024)
            manifest_info.append(InfoItem('Disk size (uncompressed)', 'disk_size', file_size, total_size))
            # total chunk size
            total_size = sum(c.file_size for c in manifest.chunk_data_list.elements)
            chunk_size = '{:.02f} GiB'.format(total_size / 1024 / 1024 / 1024)
            manifest_info.append(InfoItem('Download size (compressed)', 'download_size', chunk_size, total_size))

            if show_all_info:
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
                        tag_files = [
                            fm for fm in manifest.file_manifest_list.elements if (tag in fm.install_tags) or (not tag and not fm.install_tags)
                        ]
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
                        tag_download_size_human.append(
                            f'{human_tag.ljust(longest_tag)} - {tag_chunk_size_human} '
                            f'(Chunks: {len(tag_chunk_guids)})'
                        )

                manifest_info.append(InfoItem('Disk size by install tag', 'tag_disk_size', tag_disk_size_human or 'N/A', tag_disk_size))
                manifest_info.append(
                    InfoItem('Download size by installation tag', 'tag_download_size', tag_download_size_human or 'N/A', tag_download_size)
                )

        if not args.json:

            def print_info_item(local_item: InfoItem) -> None:
                """
                Prints an info item to the console.
                :param local_item:  The info item to print.
                """
                if local_item.value is None:
                    custom_print(f'- {local_item.name}: (None)')
                elif isinstance(local_item.value, list):
                    custom_print(f'- {local_item.name}:')
                    for list_item in local_item.value:
                        custom_print(' + ', list_item)
                elif isinstance(local_item.value, dict):
                    custom_print(f'- {local_item.name}:')
                    for k, v in local_item.value.items():
                        custom_print(f' + {k} : {v}')
                else:
                    custom_print(f'- {local_item.name}: {local_item.value}')

            if UEVaultManagerCLI.is_gui:
                uewm_gui_exists, _ = init_display_window(self.logger)
            else:
                uewm_gui_exists = False

            if info_items.get('asset'):
                custom_print('Asset Information:')
                for info_item in info_items['asset']:
                    print_info_item(info_item)
            if info_items.get('install'):
                custom_print('Installation information:')
                for info_item in info_items['install']:
                    print_info_item(info_item)
            if info_items.get('manifest'):
                custom_print('Manifest information:')
                for info_item in info_items['manifest']:
                    print_info_item(info_item)

            if not any(info_items.values()):
                custom_print('No asset information available.')
            custom_print(keep_mode=False)  # as it, next print will not keep the content
            if UEVaultManagerCLI.is_gui and not uewm_gui_exists:
                gui_g.UEVM_gui_ref.mainloop()
        else:
            json_out = dict(asset={}, install={}, manifest={})
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
        Cleans up the local asset's data folders and logs.
        :param args: options passed to the command.
        """
        uewm_gui_exists = False
        if UEVaultManagerCLI.is_gui:
            uewm_gui_exists, _ = init_display_window(self.logger)
        deleted_size = 0
        custom_print('Cleaning files and folders\n===============\n')

        # delete log and backup
        message = 'Removing logs and backups...'
        custom_print(message)
        deleted_size += self.core.uevmlfs.clean_logs_and_backups()

        message = 'Removing manifests...'
        custom_print(message)
        deleted_size += self.core.uevmlfs.clean_manifests()

        message = 'Removing tmp data...'
        custom_print(message)
        deleted_size += self.core.uevmlfs.clean_tmp_data()

        message = 'Removing cache data...'
        custom_print(message)
        deleted_size += self.core.uevmlfs.clean_cache_data()

        # delete metadata
        if args.delete_scraping_data:
            message = 'Removing scraping data...'
            custom_print(message)
            deleted_size += self.core.uevmlfs.clean_scrapping()

        if args.delete_metadata:
            message = 'Removing asset metadata...'
            custom_print(message)
            deleted_size += self.core.uevmlfs.clean_metadata(names_to_keep=[])

        # delete extra data
        if args.delete_extra_data:
            message = 'Removing asset extra data...'
            custom_print(message)
            deleted_size += self.core.uevmlfs.clean_extra(names_to_keep=[])

        message = f'Cleanup complete! Removed {deleted_size / 1024 / 1024:.02f} MiB.'
        self.logger.info(message)
        custom_print(message, keep_mode=False)

        if not uewm_gui_exists and gui_g.UEVM_gui_ref is not None:
            gui_g.UEVM_gui_ref.mainloop()

    def get_token(self, args) -> None:
        """
        Get the access token for the current user.
        :param args: options passed to the command.
        """
        if not self.core.login(force_refresh=args.bearer, raise_error=False):
            message = 'You are not connected or log in failed.\nYou should log first or check your credential.\n'
            self._log_and_gui_message(self.logger.error, message, quit_on_error=False)
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
            token = self.core.egs.get_item_token()

        if args.json:
            if args.pretty_json:
                print(json.dumps(token, indent=2, sort_keys=True))
            else:
                print(json.dumps(token))
            return
        self.logger.info(f'Exchange code: {token["code"]}')

    def edit(self, args) -> None:
        """
        Edit assets in the database using a GUI.
        :param args: options passed to the command.
        """

        data_source, data_source_type = self._init_data_for_gui(args)

        # set output file name from the input one. Used by the "rebuild" button (or rebuild_data method)
        init_gui_args(args, additional_args={'output': data_source})

        if not self.core.login(raise_error=False):
            message = 'You are not connected or log in failed.\nYou should log first or check your credential.\nSome functionalities could be disabled and data could be wrong.'
            self._log_and_gui_message(self.logger.warning, message, quit_on_error=False)

        rebuild = False
        if not os.path.isfile(data_source):
            is_valid, data_source = gui_fn.create_empty_file(data_source)
            rebuild = True
            if not is_valid:
                message = f'Error while creating the empty result file with the given path. The following file {data_source} will be used as default'
                self._log_and_gui_message(self.logger.error, message, quit_on_error=False)
                # fix invalid input/output file name in arguments to avoid futher errors in file path checks
                args.input = data_source
                args.output = data_source
                gui_g.UEVM_cli_args['input'] = data_source
                gui_g.UEVM_cli_args['output'] = data_source
        gui_g.UEVM_gui_ref = UEVMGui(
            title=gui_g.s.app_title_long,
            icon=gui_g.s.app_icon_filename,
            screen_index=0,
            data_source_type=data_source_type,
            data_source=data_source,
            rebuild_data=rebuild
        )
        gui_g.UEVM_gui_ref.mainloop()
        # print('Exiting...')  #
        # gui_g.UEVM_gui_ref.quit()

    def scrap_assets(self, args) -> None:
        """
        Scrap assets from the Epic Games Store or from previously saved files.
        :param args: options passed to the command

        Notes:
            Unlike the list_asset method, this method is not intended to be called through the GUI. So there is no need to add a ProgressWindow setup here.
        """
        if not args.offline:
            load_from_files = False
            try:
                if not self.core.login(raise_error=False):
                    message = 'You are not connected or log in failed.\nYou should log first or check your credential.\n'
                    self._log_and_gui_message(self.logger.error, message, quit_on_error=False)
                    return
            except ValueError:
                pass
            # if automatic checks are off force an update here
            self.core.check_for_updates(force=True)
        else:
            load_from_files = True
        # important to keep this value in sync with the one used in the EditableTable and UEVMGui classes
        # still true ?
        # ue_asset_per_page = gui_g.s.rows_per_page
        ue_asset_per_page = 100  # a bigger value will be refused by UE API

        if gui_g.s.testing_switch == 1:
            start_row = 0  # test only, shorter list
            # start_row = 1700  # test only, very shorter list
            max_threads = 0  # test only, see exceptions
            owned_assets_only = True  # True for test only
        else:
            start_row = 0
            max_threads = get_max_threads()
            owned_assets_only = False

        if args.force_refresh:
            load_from_files = False
        scraper = UEAssetScraper(
            start=start_row,
            assets_per_page=ue_asset_per_page,
            max_threads=max_threads,
            store_in_db=True,
            store_in_files=True,
            store_ids=False,  # useless for now
            load_from_files=load_from_files,
            engine_version_for_obsolete_assets=self.core.engine_version_for_obsolete_assets,
            core=self.core,  # VERY IMPORTANT: pass the code object to the scraper to keep the same session
            cli_args=args
        )

        scraper.gather_all_assets_urls(empty_list_before=True, owned_assets_only=owned_assets_only)
        scraper.save(owned_assets_only=owned_assets_only)

    def set_release_index(self, value):
        """
        Set the release id. Callback for the ChoiceFromListWindow
        :param value: the value selected in the list
        """
        self.release_index = value

    def install_asset(self, args):
        """
        Installs an asset.
        :param args: options passed to the command.
        """
        uewm_gui_exists = gui_g.UEVM_gui_ref is not None
        if args.subparser_name == 'download':
            args.no_install = True
        if args.clean_dowloaded_data and args.no_install:
            self._log_and_gui_message(
                self.logger.error,
                'You have selected to not install the asset and to not keep the downloaded data.\nSo, nothing can be done for you.\nCommand is aborted',
                quit_on_error=not uewm_gui_exists
            )
            return False

        if not self.core.login():
            self._log_and_gui_message(
                self.logger.error,
                'You are not connected or log in failed.\nYou should log first or check your credential.\nCommand is aborted',
                quit_on_error=not uewm_gui_exists
            )
            return False

        # we use the "old" method (i.e. legendary way) to get the Asset, because we need to access to the metadata and its "base_urls"
        # that is not available in the "new" method (i.e. new API way)
        # Anyway, we can only install asset we own, so the "old" method is enough
        asset = self.core.get_item(args.app_name, update_meta=args.force_refresh)
        # asset_id = asset.metadata.get('appId', None)
        if not asset:
            self._log_and_gui_message(
                self.logger.error,
                f'Metadata are not available for "{args.app_name}".\nYou can only install an asset you own.\nInstallation can not be done.\nCommand is aborted',
                quit_on_error=not uewm_gui_exists
            )
            return False
        categories = asset.metadata.get('categories', None)
        category = categories[0]['path'] if categories else ''
        release_info = asset.metadata.get('releaseInfo', None)
        catalog_item_id = asset.catalog_item_id
        is_plugin = category and 'plugin' in category.lower()
        installed_in_engine = False
        # get version list from release info
        releases = []
        version_choice = {}
        if release_info is not None and len(release_info) > 0:
            # TODO: only keep releases that are compatible with the version of the selected project.
            for index, item in enumerate(reversed(release_info)):  # reversed to have the latest release first
                asset_id = item.get('appId', None)
                release_title = item.get('versionTitle', '') or asset_id
                compatible_list = item.get('compatibleApps', None)
                date_added = item.get('dateAdded', '')
                # Convert the string to a datetime object
                datetime_obj = datetime.strptime(date_added, "%Y-%m-%dT%H:%M:%S.%fZ")
                # Format the datetime object as "YYYY-MM-DD"
                formatted_date = datetime_obj.strftime("%Y-%m-%d")
                if asset_id is not None and release_title is not None and compatible_list is not None:
                    # remove 'UE_' from items of the compatible_list
                    compatible_list = [item.replace('UE_', '') for item in compatible_list]
                    data = {
                        'title': release_title,  #
                        'asset_id': asset_id,  #
                        'compatible': compatible_list,  #
                    }
                    compatible_str = ','.join(compatible_list)
                    desc = f'Release id: {asset_id}\nTitle: {release_title}\nRelease Date: {formatted_date}\nUE Versions: {compatible_str}'
                    version_choice[release_title] = {'value': index, 'desc': desc}
                    releases.append(data)
        release_selected = releases[-1]  # by default, we take the lastest release
        if uewm_gui_exists:
            # create a windows to choose the release
            sub_title = 'In the list below, Select the closest version that matches your project or engine version'
            cw = ChoiceFromListWindow(
                window_title='UEVM: select release',
                title='Choose the release to download',
                sub_title=sub_title,
                choices=version_choice,
                set_value_func=self.set_release_index,
                default_value=''
            )
            make_modal(cw)
            # NOTE: the next line will only be executed when the ChoiceFromListWindow will be closed AND the self.set_release_index methode been called
            if self.release_index >= 0:
                try:
                    release_selected = releases[self.release_index]
                except IndexError:
                    self._log_and_gui_display(
                        self.logger.warning, 'The selected release could not be found. The latest one as been selected by default.\n'
                    )

        release_name = release_selected['asset_id']
        release_title = release_selected['title']
        install_path_base = args.install_path if args.install_path is not None else ''

        folders_to_check = []
        if not install_path_base and not args.no_install:
            if uewm_gui_exists:
                if is_plugin and box_yesno('This asset is a plugin. Do you want to install it into an engine folder ?'):
                    install_path_base = filedialog.askdirectory(
                        title='Select the BASE folder of the Engine version to install the plugin into', initialdir=gui_g.s.last_opened_engine
                    )
                    if install_path_base:
                        # remove all existing subfolder in the selected part that is in the subpath 'Engine/Plugins/Marketplace'
                        path_to_check = os.path.normpath(install_path_base)
                        path_parts = gui_g.s.ue_plugin_install_subfolder.split('/')
                        # get subfolder by reverse order (start by the latest)
                        path_parts_temp = path_parts.copy()
                        while len(path_parts_temp):
                            last_part = path_parts_temp.pop()
                            # remove the last part if it is the last part of the path
                            if last_part.lower() == os.path.basename(path_to_check).lower():
                                path_to_check = os.path.dirname(path_to_check)
                        # the plugin contains all the subfolder, no need to ass them to the installation folder
                        install_path_base = path_to_check
                        # check if the "engine folder structure" is correct
                        # here we have removed all the subfolder of the path, so we recreate and add the "valid" subpath
                        subpath = os.path.join(*path_parts)  # NO path_join here because it will create an absolute path
                        path_to_check = path_join(path_to_check, subpath)
                        if not os.path.isdir(
                            os.path.dirname(path_to_check)
                        ):  # we remove the last part here (i.e. 'Marketplace') because it does not exist in a new installed engine
                            self._log_and_gui_message(
                                self.logger.error,
                                f'You have selected a folder that seems to be invalid.\nThe {path_to_check} could not be found.\nCommand is aborted',
                                quit_on_error=not uewm_gui_exists
                            )
                            return False
                        else:
                            installed_in_engine = True
                            if install_path_base:
                                gui_g.s.last_opened_engine = install_path_base  # we save only the "base engine" path
                else:
                    install_path_base = filedialog.askdirectory(
                        title='Select a project to install the asset into', initialdir=gui_g.s.last_opened_project
                    )
                    if install_path_base:
                        gui_g.s.last_opened_project = install_path_base

        if not install_path_base:
            if not args.no_install:
                self._log_and_gui_message(
                    self.logger.error,
                    'You have selected to install the asset but no install path has been given.\nSo, nothing can be done for you.\nCommand is aborted',
                    quit_on_error=not uewm_gui_exists
                )
                return False
        else:
            # remove the 'Content' at the end of the path if present
            # to avoid copying the sub_folder folder inside the sub_folder
            sub_folder = gui_g.s.ue_asset_content_subfolder
            if os.path.basename(install_path_base).lower() == sub_folder.lower():  # MUST BE LOWERCASE for comparison
                install_path_base = os.path.dirname(install_path_base)
            folders_to_check.append(install_path_base)

        if UEVaultManagerCLI.is_gui:
            uewm_gui_exists, dw = init_display_window(self.logger)
            dw.keep_existing = True  # because init_display_window will set it to False
            dw.clean()
            message = f'Starting Download of Release "{release_title}"' if args.no_install else f'Starting Installation of Release "{release_title}"'
            dw.display(message)

        if args.vault_cache:
            args.clean_dowloaded_data = False
            # in the vaultCache, the data is in a subfolder named like the release of the Asset
            sub_folder = gui_g.s.ue_plugin_vaultcache_subfolder
            download_path = path_join(self.core.egl.vault_cache_folder, release_name, sub_folder)
            self._log_and_gui_display(
                self.logger.info, 'Use the vault cache folder to store the downloaded asset.\nOther download options will be ignored.\n'
            )
        else:
            # the downloaded data should always have a "Content" inside
            sub_folder = gui_g.s.ue_asset_content_subfolder
            download_path = args.download_path
            # remove the sub_folder at the end of the path if present
            # to avoid copying the sub_folder folder inside the sub_folder
            if os.path.basename(download_path).lower() == sub_folder.lower():  # MUST BE LOWERCASE for comparison
                download_path = os.path.dirname(download_path)
            download_path = path_join(download_path, sub_folder)

        # normpath is usefull for future comparisons
        download_path = os.path.normpath(download_path)
        install_path_base = os.path.normpath(install_path_base)

        self._log_and_gui_display(self.logger.info, f'Preparing download for {release_title}...')
        dlm, analysis, installed_asset = self.core.prepare_download(
            base_asset=asset,  # contains generic info of the base asset for all releases, NOT the selected release
            release_name=release_name,
            release_title=release_title,
            download_folder=download_path,
            install_folder=install_path_base,
            no_resume=args.no_resume,
            max_shm=args.shared_memory,
            max_workers=args.max_workers,
            reuse_last_install=args.reuse_last_install,
            dl_optimizations=args.order_opt,
            override_manifest=args.override_manifest,
            override_base_url=args.override_base_url,
            preferred_cdn=args.preferred_cdn,
            disable_https=args.disable_https,
        )
        if install_path_base and not args.no_install and analysis.already_installed and not box_yesno(
            f'The selected asset as already been installed in "{install_path_base}".\nDo you want to continue ?'
        ):
            self._log_and_gui_display(self.logger.info, f'Asset already installed.\nOperation aborted by user.')
            return False

        self._log_and_gui_display(self.logger.info, f'Install size: {analysis.install_size / 1024 / 1024:.02f} MiB')
        compression = (1 - (analysis.dl_size / analysis.uncompressed_dl_size)) * 100 if analysis.uncompressed_dl_size else 0
        self._log_and_gui_display(
            self.logger.info, f'Download size: {analysis.dl_size / 1024 / 1024:.02f} MiB (Compression savings: {compression:.01f}%)'
        )
        self._log_and_gui_display(
            self.logger.info,
            f'Reusable size: {analysis.reuse_size / 1024 / 1024:.02f} MiB (chunks) / {analysis.unchanged / 1024 / 1024:.02f} MiB (unchanged / skipped)'
        )
        self._log_and_gui_display(
            self.logger.info, 'Downloads are resumable, you can interrupt the download with CTRL-C and resume it using the same command later on.'
        )
        folders_to_check.append(download_path)
        res = self.core.check_installation_conditions(analysis=analysis, folders=folders_to_check, ignore_space_req=args.ignore_free_space)
        message_list = []

        if res.warnings or res.failures:
            message_list.append('\nInstallation requirements check returned the following results:')
            for message in res.warnings:
                message_list.append(' - Warning:' + message)
            for message in res.failures:
                message_list.append(' ! Failure:' + message)
            self._log_and_gui_display(self.logger.warning, '\n'.join(message_list))

        if res.failures:
            self._log_and_gui_message(self.logger.critical, 'Installation can not proceed.\nCommand is aborted', quit_on_error=not uewm_gui_exists)
            # not in GUI self.core.clean_exit(1)  # previous line could not quit
            return False

        if not args.yes:
            if not get_boolean_choice(f'Do you wish to install {release_title} ?'):  # todo: use a gui yes/no if gui is enabled
                print('Aborting...')
                # not in GUI self.core.clean_exit(0)
                return False
        start_t = time.time()
        try:
            # set up logging stuff (should be moved somewhere else later)
            dlm.logging_queue = self.logging_queue
            dlm.proc_debug = args.dlm_debug
            dlm.start()
            dlm.join()
        except Exception as error:
            end_t = time.time()
            self._log_and_gui_display(self.logger.info, f'Installation failed after {end_t - start_t:.02f} seconds.')
            self._log_and_gui_display(
                self.logger.warning,
                f'The following exception occurred while waiting for the downloader to finish: {error!r}.\nTry restarting the process.\nIf it continues to fail please open an issue on GitHub.'
            )
        else:
            end_t = time.time()
            download_path = dlm.download_dir  # it could have been changed by the dlm
            message = f'Finished download process in {end_t - start_t:.02f} seconds.\nFiles has been downloaded in {dlm.download_dir}'
            self._log_and_gui_display(self.logger.info, message)
            start_t = time.time()
            message = ''
            if not args.no_install:
                self._log_and_gui_display(self.logger.info, 'Start copying downloaded data to install folder...')
                subfolder = gui_g.s.ue_plugin_vaultcache_subfolder if is_plugin else gui_g.s.ue_asset_content_subfolder
                # copy the downloaded data to the installation folder
                download_path_subfolder = os.path.basename(download_path).lower()
                # the downloaded data should always have a "Content" inside
                # so, we need to add it to the src_folder if it is not already there to avoid copying the content folder inside the content folder
                if download_path_subfolder == subfolder.lower():
                    src_folder = download_path
                else:
                    src_folder = path_join(download_path, subfolder)
                if is_plugin:
                    # note: the folder has already been checked when selected
                    if installed_in_engine:
                        dest_folder = install_path_base
                    else:
                        # if the plugin is not installed in an engine, we have to change the destination folder structure to install it IN the "Plugins" subfolder of the destination
                        src_folder = path_join(src_folder, gui_g.s.ue_plugin_install_subfolder)  # add the plugin subpath to the source folder
                        src_folder = os.path.dirname(src_folder)  # remove the last part (ie the "plugin name" subfolder) to get the "base" folder
                        dest_folder = path_join(
                            install_path_base, gui_g.s.ue_plugin_project_subfolder
                        )  # add the plugin subpath for "projects" to the destination folder
                else:
                    install_path_subfolder = os.path.basename(installed_asset.install_path).lower()
                    if install_path_subfolder == gui_g.s.ue_asset_content_subfolder.lower():
                        dest_folder = installed_asset.install_path
                    else:
                        dest_folder = path_join(installed_asset.install_path, gui_g.s.ue_asset_content_subfolder)
                if dest_folder and copy_folder(
                    src_folder, dest_folder, check_copy_size=not installed_in_engine
                ):  # We DON'T check the size if the plugin is installed in an engine because it's too long
                    self.core.uevmlfs.set_installed_asset(release_name, installed_asset.__dict__)
                    if args.database:
                        db_handler = UEAssetDbHandler(database_name=args.database)
                        db_handler.add_to_installed_folders(catalog_item_id=catalog_item_id, folders_to_add=[installed_asset.install_path])
                    message += f'\nAsset have been installed in "{installed_asset.install_path}"'
                else:
                    message += f'\nAsset could not be installed in "{installed_asset.install_path}"'
            if args.vault_cache and installed_asset.manifest_path:
                # copy the manifest file to the vault cache folder
                parent_path = os.path.dirname(download_path)
                message += f'\nThe manifest file has been copied in {parent_path}.'
                # manifest_filename = path_join(parent_path, 'manifest.json')
                manifest_filename = path_join(parent_path, 'manifest')
                shutil.copy(installed_asset.manifest_path, manifest_filename)
            elif args.clean_dowloaded_data:
                message += '\nDownloaded data have been deleted.'
                # delete the dlm.download_dir folder
                rmtree(download_path)
                self.core.uevmlfs.clean_tmp_data()
            end_t = time.time()
            message += f'\n\nProcess finished in {end_t - start_t:.02f} seconds.'
            self._log_and_gui_display(self.logger.info, message)
        # if uewm_gui_exists:
        #     dw.close_window()
        return True

    @staticmethod
    def print_version():
        """
        Prints the version of UEVaultManager and exit.
        """
        print(f'UEVaultManager version "{UEVM_version}", codename "{UEVM_codename}"')
        sys.exit(0)

    @staticmethod
    def print_help(args, parser=None, forced=False) -> None:
        """
        Prints the help for the command.
        :param args:.
        :param parser: command line parser. If not provided, gui_g.UEVM_parser_ref will be used.
        :param forced: whether the help will be printed even if the --help option is not present.
        """
        if parser is None:
            parser = gui_g.UEVM_parser_ref
        if parser is None:
            return
        uewm_gui_exists = False

        if args.full_help or forced:
            if UEVaultManagerCLI.is_gui:
                uewm_gui_exists, _ = init_display_window()
            custom_print(keep_mode=False, text=parser.format_help())

            # Commands that should not be shown in full help/list of commands (e.g. aliases)
            _hidden_commands = {'download', 'update', 'repair', 'get-token', 'verify-asset', 'list-assets'}
            # Print the help for all the subparsers. Thanks stackoverflow!
            custom_print(text='Individual command help:')
            # noinspection PyProtectedMember,PyUnresolvedReferences
            subparsers = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
            # noinspection PyUnresolvedReferences
            for choice, subparser in subparsers.choices.items():
                if choice in _hidden_commands:
                    continue
                custom_print(text=f'\nCommand: {choice}')
                custom_print(text=subparser.format_help())
        elif os.name == 'nt':
            from UEVaultManager.lfs.windows_helpers import double_clicked
            if double_clicked():
                custom_print(text='Please note that this is not the intended way to run UEVaultManager.')
                custom_print(text='If you want to start it without arguments, you can start it in edit mode by default.')
                custom_print(text='For that, you must set the line start_in_edit_mode=true in the configuration file.')
                custom_print(text='More info on usage and configuration can be found in https://github.com/LaurentOngaro/UEVaultManager#readme')
                subprocess.Popen(['cmd', '/K', 'echo>nul'])
        else:
            # on non-windows systems
            # UEVaultManagerCLI.print_help(args, parser=parser, forced=True)
            UEVaultManagerCLI.print_version()
            return

        if UEVaultManagerCLI.is_gui and not uewm_gui_exists:
            gui_g.UEVM_gui_ref.mainloop()

    def run_test(self, _args) -> None:
        """
        Run a test command using a CLI prompt. Just for developpers.
        """
        print('UEVaultManager RUN TEST')
        print('"opening a manifest file from disk...')
        # read manifest_data from file
        file_path = "G:/Assets/pour UE/02 Warez/Environments/Elite_Landscapes_Desert_III/EliteLane90e1a8f98bbV1/manifest"
        json_print_key_val(self.core.open_manifest_file(file_path))


def main():
    """
    Main function.
    """
    # Set output encoding to UTF-8 if not outputting to a terminal
    try:
        # noinspection PyUnresolvedReferences
        sys.stdout.reconfigure(encoding='utf-8')
    except (Exception, ):
        pass
    parser = argparse.ArgumentParser(description=f'UEVaultManager v{UEVM_version} - "{UEVM_codename}"')
    parser.register('action', 'parsers', HiddenAliasSubparsersAction)

    # general arguments
    parser.add_argument('-H', '--full-help', dest='full_help', action='store_true', help='Show full help (including individual command help)')
    parser.add_argument('-d', '--debug', dest='debug', action='store_true', help='Set loglevel to debug')
    parser.add_argument('-y', '--yes', dest='yes', action='store_true', help='Default to yes for all prompts')
    # noinspection DuplicatedCode
    parser.add_argument('-V', '--version', dest='version', action='store_true', help='Print version and exit')
    parser.add_argument('-T', '--runtest', dest='runtest', action='store_true', help='Run a test command using a CLI prompt. Just for developpers')
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
        default=(7, 7),
        metavar='<seconds>',
        help='API HTTP request timeout (default: 10 seconds)'
    )  # timeout could be a float or a tuple  (connect timeout, read timeout) in s
    parser.add_argument(
        '-g', '--gui', dest='gui', action='store_true', help='Display additional information using gui elements like dialog boxes or progress window'
    )
    gui_g.UEVM_parser_ref = parser

    # all the commands
    subparsers = parser.add_subparsers(title='Commands', dest='subparser_name', metavar='<command>')
    auth_parser = subparsers.add_parser('auth', help='Authenticate with the Epic Games Store')
    clean_parser = subparsers.add_parser('cleanup', help='Remove old temporary, metadata, and manifest files')
    info_parser = subparsers.add_parser('info', help='Prints info about specified asset or manifest')
    list_parser = subparsers.add_parser('list', aliases=('list-assets', ), help='List owned assets')
    list_files_parser = subparsers.add_parser('list-files', help='List files in manifest')
    status_parser = subparsers.add_parser('status', help='Show UEVaultManager status information')
    edit_parser = subparsers.add_parser('edit', aliases=('edit-assets', ), help='Edit the assets list file')
    scrap_parser = subparsers.add_parser('scrap', aliases=('scrap-assets', ), help='Scrap all the available assets on the marketplace')
    install_parser = subparsers.add_parser('install', aliases=('download', ), help='Download or Install an asset')
    # hidden commands have no help text
    get_token_parser = subparsers.add_parser('get-token')

    # Positional arguments
    install_parser.add_argument('app_name', nargs='?', metavar='<App Name>', help='Uid of the Asset to install')
    list_files_parser.add_argument('app_name', nargs='?', metavar='<App Name>', help='Uid of the Asset to list files from')
    info_parser.add_argument('app_name_or_manifest', help='Uid of the Asset to get info from or manifest path', metavar='<App Name/Manifest URI>')

    # Flags for parsers
    #####
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

    ######
    clean_parser.add_argument(
        '-m,'
        '--delete-metadata', dest='delete_metadata', action='store_true', help='Also delete metadata files. They are kept by default'
    )
    clean_parser.add_argument(
        '-e,'
        '--delete-extra-data', dest='delete_extra_data', action='store_true', help='Also delete extra data files. They are kept by default'
    )
    clean_parser.add_argument(
        '-s,'
        '--delete-scraping-data',
        dest='delete_scraping_data',
        action='store_true',
        help='Also delete scraping data files. They are kept by default'
    )
    # noinspection DuplicatedCode
    clean_parser.add_argument('-g', '--gui', dest='gui', action='store_true', help='Display the output in a windows instead of using the console')

    ######
    info_parser.add_argument('--offline', dest='offline', action='store_true', help='Only print info available offline')
    info_parser.add_argument('--json', dest='json', action='store_true', help='Output information in JSON format')
    info_parser.add_argument(
        '-f',
        '--force-refresh',
        dest='force_refresh',
        action='store_true',
        help="Force a refresh of all asset's metadata. It could take some time ! If not forced, the cached data will be used"
    )
    info_parser.add_argument('-a', '--all', dest='all', action='store_true', help='Display all the information even if non-relevant for an asset')
    info_parser.add_argument('-g', '--gui', dest='gui', action='store_true', help='Display the output in a windows instead of using the console')

    #####
    list_parser.add_argument('--csv', dest='csv', action='store_true', help='Output in CSV format')
    list_parser.add_argument('--tsv', dest='tsv', action='store_true', help='Output in TSV format')
    # noinspection DuplicatedCode
    list_parser.add_argument('--json', dest='json', action='store_true', help='Output in JSON format')
    list_parser.add_argument(
        '-f',
        '--force-refresh',
        dest='force_refresh',
        action='store_true',
        help="Force a refresh of all asset's metadata. It could take some time ! If not forced, the cached data will be used"
    )
    list_parser.add_argument(
        '-fc',
        '--filter-category',
        dest='filter_category',
        action='store',
        help='Filter assets by category. Search against the asset category in the marketplace. Search is case-insensitive and can be partial'
    )
    list_parser.add_argument(
        '-o', '--output', dest='output', metavar='<path/name>', action='store', help='The file name (with path) where the list should be written'
    )
    list_parser.add_argument(
        '-T', '--third-party', dest='include_non_asset', action='store_true', default=False, help='Also list assets that are not installable.'
    )
    list_parser.add_argument(
        '-g', '--gui', dest='gui', action='store_true', help='Display additional information using gui elements like dialog boxes or progress window'
    )

    #####
    # noinspection DuplicatedCode
    list_files_parser.add_argument(
        '--manifest', dest='override_manifest', action='store', metavar='<uri>', help='Manifest URL or path to use instead of the CDN one'
    )
    list_files_parser.add_argument('--csv', dest='csv', action='store_true', help='Output in CSV format')
    list_files_parser.add_argument('--tsv', dest='tsv', action='store_true', help='Output in TSV format')
    list_files_parser.add_argument('--json', dest='json', action='store_true', help='Output in JSON format')
    # noinspection DuplicatedCode
    list_files_parser.add_argument(
        '--hashlist', dest='hashlist', action='store_true', help='Output file hash list in hash Check/sha1 sum -c compatible format'
    )
    list_files_parser.add_argument(
        '-f',
        '--force-refresh',
        dest='force_refresh',
        action='store_true',
        help="Force a refresh of all asset's metadata. It could take some time ! If not forced, the cached data will be used"
    )
    list_files_parser.add_argument(
        '-g', '--gui', dest='gui', action='store_true', help='Display the output in a windows instead of using the console'
    )

    #####
    status_parser.add_argument('--offline', dest='offline', action='store_true', help='Only print offline status information, do not log in')
    # noinspection DuplicatedCode
    status_parser.add_argument('--json', dest='json', action='store_true', help='Show status in JSON format')
    status_parser.add_argument(
        '-f',
        '--force-refresh',
        dest='force_refresh',
        action='store_true',
        help="Force a refresh of all asset's metadata. It could take some time ! If not forced, the cached data will be used"
    )
    status_parser.add_argument('-g', '--gui', dest='gui', action='store_true', help='Display the output in a windows instead of using the console')

    ######
    edit_parser.add_argument(
        '-i',
        '--input',
        dest='input',
        metavar='<path/name>',
        action='store',
        help='The file name (with path) where the list should be read from (it exludes the --database option)'
    )
    edit_parser.add_argument(
        '-db',
        '--database',
        dest='database',
        metavar='<path/name>',
        action='store',
        help='The sqlite file name (with path) where the list should be read from (it exludes the --input option)'
    )
    # not use for now
    # edit_parser.add_argument('--csv', dest='csv', action='store_true', help='Input file is in CSV format')
    # edit_parser.add_argument('--tsv', dest='tsv', action='store_true', help='Input file is in TSV format')
    # edit_parser.add_argument('--json', dest='json', action='store_true', help='Input file is in JSON format')
    ######
    scrap_parser.add_argument(
        '-f',
        '--force-refresh',
        dest='force_refresh',
        action='store_true',
        help="Force a refresh of all asset's data. It could take some time ! If not forced, the cached data will be used"
    )
    # noinspection DuplicatedCode
    scrap_parser.add_argument(
        '--offline', dest='offline', action='store_true', help='Use previous saved data files (json) instead of grabing urls and scapping new data'
    )
    scrap_parser.add_argument('-g', '--gui', dest='gui', action='store_true', help='Display the output in a windows instead of using the console')

    ######
    install_parser.add_argument(
        '-i', '--install-path', dest='install_path', action='store', metavar='<path>', help='Path where the Asset will be installed'
    )
    install_parser.add_argument(
        '-dp',
        '--download-path',
        dest='download_path',
        action='store',
        metavar='<path>',
        help='Path where the Asset will be downloaded. If empty, the Epic launcher Vault cache will be used.'
    )
    install_parser.add_argument(
        '-f',
        '--force-refresh',
        dest='force_refresh',
        action='store_true',
        help="Force a refresh of all asset's data. It could take some time ! If not forced, the cached data will be used"
    )
    install_parser.add_argument(
        '-vc',
        '--vault-cache',
        dest='vault_cache',
        action='store_true',
        help='Use the vault cache folder to store the downloaded asset. It uses Epic Game Launcher setting to get this value.'  #
        + 'In that case, the download_path option will be ignored'
    )
    install_parser.add_argument(
        '-c',
        '--clean-dowloaded-data',
        dest='clean_dowloaded_data',
        action='store_true',
        help='Delete the folder with dowloaded data. Keep the installed version if it has been installed.'
    )
    install_parser.add_argument(
        '--max-shared-memory',
        dest='shared_memory',
        action='store',
        metavar='<size>',
        type=int,
        help='Maximum amount of shared memory to use (in MiB), default: 1 GiB'
    )
    install_parser.add_argument(
        '--max-workers',
        dest='max_workers',
        action='store',
        metavar='<num>',
        type=int,
        help='Maximum amount of download workers, default: min(2 * CPUs, 16)'
    )
    install_parser.add_argument(
        '--manifest',
        dest='override_manifest',
        action='store',
        metavar='<uri>',
        help='Manifest URL or path to use instead of the CDN one (e.g. for downgrading)'
    )
    install_parser.add_argument(
        '--base-url',
        dest='override_base_url',
        action='store',
        metavar='<url>',
        help='Base URL to download from (e.g. to test or switch to a different CDNs)'
    )
    install_parser.add_argument('--no-resume', dest='no_resume', action='store_true', help='Force Download all files / ignore resume')
    install_parser.add_argument('--download-only', '--no-install', dest='no_install', action='store_true', help='Do not install asset after download')
    install_parser.add_argument(
        '-r',
        '--reuse-last-install',
        dest='reuse_last_install',
        action='store_true',
        help='If the asset has been previouly installed, the installation folder will be reused. In that case, the install-path option will be ignored'
    )
    install_parser.add_argument(
        '--dlm-debug', dest='dlm_debug', action='store_true', help='Set download manager and worker processes\' loglevel to debug'
    )
    install_parser.add_argument(
        '--enable-reordering',
        dest='order_opt',
        action='store_true',
        help='Enable reordering optimization to reduce RAM requirements '
        'during download (may have adverse results for some titles)'
    )
    install_parser.add_argument(
        '--timeout',
        dest='timeout',
        action='store',
        metavar='<sec>',
        type=int,
        help='Connection and read timeout for downloader (default: 10 seconds)'
    )
    install_parser.add_argument(
        '--ignore-free-space', dest='ignore_free_space', action='store_true', help='Do not abort if not enough free space is available'
    )
    install_parser.add_argument(
        '--preferred-cdn',
        dest='preferred_cdn',
        action='store',
        metavar='<hostname>',
        help='Set the hostname of the preferred CDN to use when available'
    )
    install_parser.add_argument(
        '--no-https', dest='disable_https', action='store_true', help='Download games via plaintext HTTP (like EGS), e.g. for use with a lan cache'
    )

    ######
    get_token_parser.add_argument('--json', dest='json', action='store_true', help='Output information in JSON format')
    get_token_parser.add_argument('--bearer', dest='bearer', action='store_true', help='Return fresh bearer token rather than an exchange code')

    # Note: this line prints the full help and quit if not other command is available
    args, extra = parser.parse_known_args()

    cli = UEVaultManagerCLI(override_config=args.config_file, api_timeout=args.api_timeout)

    if args.version:
        UEVaultManagerCLI.print_version()
        return

    if args.runtest:
        cli.run_test(args)
        return

    start_in_edit_mode = str_to_bool(cli.core.uevmlfs.config.get('UEVaultManager', 'start_in_edit_mode', fallback=False))

    if not start_in_edit_mode and (not args.subparser_name or args.full_help):
        UEVaultManagerCLI.print_help(args=args, parser=parser)
        return

    ql = cli.setup_threaded_logging()

    conf_log_level = cli.core.uevmlfs.config.get('UEVaultManager', 'log_level', fallback='info')
    if conf_log_level == 'debug' or args.debug:
        cli.core.verbose_mode = True
        logging.getLogger().setLevel(level=logging.DEBUG)
        # keep requests quiet
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)

    cli.core.create_output_backup = str_to_bool(cli.core.uevmlfs.config.get('UEVaultManager', 'create_output_backup', fallback=True))
    cli.core.create_log_backup = str_to_bool(cli.core.uevmlfs.config.get('UEVaultManager', 'create_log_backup', fallback=True))
    cli.core.verbose_mode = str_to_bool(cli.core.uevmlfs.config.get('UEVaultManager', 'verbose_mode', fallback=False))
    cli.ue_assets_max_cache_duration = int(cli.core.uevmlfs.config.get('UEVaultManager', 'ue_assets_max_cache_duration', fallback=1296000))

    cli.core.ignored_assets_filename_log = cli.core.uevmlfs.config.get('UEVaultManager', 'ignored_assets_filename_log', fallback='')
    cli.core.notfound_assets_filename_log = cli.core.uevmlfs.config.get('UEVaultManager', 'notfound_assets_filename_log', fallback='')
    cli.core.bad_data_assets_filename_log = cli.core.uevmlfs.config.get('UEVaultManager', 'bad_data_assets_filename_log', fallback='')
    cli.core.scan_assets_filename_log = cli.core.uevmlfs.config.get('UEVaultManager', 'scan_assets_filename_log', fallback='')

    cli.core.engine_version_for_obsolete_assets = cli.core.uevmlfs.config.get(
        'UEVaultManager', 'engine_version_for_obsolete_assets', fallback=gui_g.s.engine_version_for_obsolete_assets
    )

    # copy the name of the config file used to the gui global variable
    gui_g.s.config_file = cli.core.uevmlfs.config_file

    # if --yes is used as part of the subparsers arguments manually set the flag in the main parser.
    if '-y' in extra or '--yes' in extra:
        args.yes = True

    try:
        UEVaultManagerCLI.is_gui = args.gui
    except (AttributeError, KeyError):
        UEVaultManagerCLI.is_gui = False

    # technically args.func() with set defaults could work (see docs on subparsers)
    # but that would require all funcs to accept args and extra...
    try:
        if args.subparser_name == 'auth':
            cli.auth(args)
        elif args.subparser_name == 'cleanup':
            cli.cleanup(args)
        elif args.subparser_name == 'info':
            cli.info(args)
        elif args.subparser_name in {'list', 'list-assets'}:
            cli.list_assets(args)
        elif args.subparser_name == 'list-files':
            cli.list_files(args)
        elif args.subparser_name == 'status':
            cli.status(args)
        elif args.subparser_name in {'edit', 'edit-assets'}:
            if args.database and args.input:
                remove_command_argument(edit_parser, 'input')
            args.gui = True
            UEVaultManagerCLI.is_gui = True
            cli.edit(args)
        elif args.subparser_name in {'scrap', 'scrap-assets'}:
            args.gui = True
            UEVaultManagerCLI.is_gui = True
            cli.scrap_assets(args)
        elif args.subparser_name in {'download', 'install'}:
            cli.install_asset(args)
        elif args.subparser_name == 'get-token':
            cli.get_token(args)
        elif start_in_edit_mode:
            args.gui = True
            UEVaultManagerCLI.is_gui = True
            args.subparser_name = 'edit'
            args.input = init_gui(False)
            cli.edit(args)
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
            print(f'- New version: {update_info["version"]} - "{update_info["codename"]}"')
            print(f'- Release summary:\n{update_info["summary"]}')
            if update_info['severity'] == UpdateSeverity.HIGH.name:
                print('! This update is recommended as it fixes major issues.')
                print(f'\n- Release URL: {update_info["release_url"]}')
    ql.stop()
    cli.core.clean_exit(0)


if __name__ == '__main__':
    # required for pyinstaller on Windows, does nothing on other platforms.
    freeze_support()
    main()
