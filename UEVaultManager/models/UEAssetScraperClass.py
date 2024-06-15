# coding=utf-8
"""
Implementation for:
- UEAssetScraper: class that handles scraping data from the Unreal Engine Marketplace.
"""
import concurrent.futures
import csv
import json
import logging
import os
import random
import time
from datetime import datetime
from itertools import chain
from threading import current_thread

from requests import ReadTimeout

import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.api.egs import is_asset_obsolete
from UEVaultManager.core import AppCore
from UEVaultManager.lfs.utils import path_join
from UEVaultManager.models.csv_sql_fields import convert_data_to_csv, csv_sql_fields, debug_parsed_data, get_csv_field_name_list, \
    get_sql_field_name_list, get_sql_preserved_fields, is_on_state, is_preserved
from UEVaultManager.models.types import CSVFieldState, DateFormat, GetDataResult
from UEVaultManager.models.UEAssetClass import UEAsset
from UEVaultManager.models.UEAssetDbHandlerClass import UEAssetDbHandler
from UEVaultManager.tkgui.modules.cls.FakeProgressWindowClass import FakeProgressWindow
from UEVaultManager.tkgui.modules.functions import box_yesno, update_loggers_level
from UEVaultManager.tkgui.modules.functions_no_deps import check_and_convert_list_to_str
from UEVaultManager.tkgui.modules.types import DataSourceType
from UEVaultManager.tkgui.modules.types import GrabResult
from UEVaultManager.utils.cli import str_is_bool, str_to_bool


# noinspection PyPep8Naming
class UEAS_Settings:
    """
    Settings for the class when running as main.
    """
    # set the number of rows to retrieve per page
    # As the asset are saved individually by default, this value is only use for pagination in the files that store the url
    # it speeds up the process of requesting the asset list
    ue_asset_per_page = 100
    datasource_filename = gui_g.s.sqlite_filename
    if gui_g.s.testing_switch == 1:
        # shorter and faster list for testing only
        # disabling threading is used for debugging (fewer exceptions are raised if threads are used)
        threads = 0  # set to 0 to disable threading
        start_row = 15000
        stop_row = 15000 + gui_g.s.testing_assets_limit
        clean_db = False
        load_data_from_files = False
    else:
        threads = 16
        start_row = 0
        stop_row = 0  # 0 means no limit
        clean_db = True
        load_data_from_files = False  # by default the scraper will rebuild the database from scratch


class ScrapTask:
    """
    A class that handles scraping data from the Unreal Engine Marketplace.
    :param caller: UEAssetScraper object.
    :param log_func: function to use to log messages. Defaults to print.
    :param task_name: name of the task. Defaults to ''.

    """

    def __init__(self, caller, log_func: callable = None, task_name: str = '', url: str = '', owned_assets_only: bool = False):
        self.caller = caller
        self.name = f'ScrapTask_{gui_fn.shorten_text(url, limit=35, prefix="_")}' if not task_name else task_name
        self.log_func = log_func if log_func else print
        self.url = url
        self.owned_assets_only = owned_assets_only

    def __call__(self):
        self.log_func(f'START OF ScrapTask {self.name} at {datetime.now()}')
        result = self.caller.get_data_from_url(
            self.url
        )  # Note: If a captcha is present, this call will be made as a not connected user, so we can't get the "owned" flag value anymore
        self.log_func(f'END OF ScrapTask {self.name} at {datetime.now()}')
        return result

    def interrupt(self, message: str = '') -> None:
        """
        Interrupt the task.
        :param message: additional message to log.
        """
        self.log_func(f'INTERRUPTION OF ScrapTask {self.name} at {datetime.now()}:{message}')


class UEAssetScraper:
    """
    A class that handles scraping data from the Unreal Engine Marketplace.
    It saves the data in json files and/or in a sqlite database.
    :param datasource_filename: name of the database or file to save the data to.
    :param use_database: True to use a database for reading missing data (ex tags names) and save data in a sqlite database. Defaults to True.
    :param start: starting index for the data to retrieve. Defaults to 0.
    :param stop: ending index for the data to retrieve. Defaults to 0.
    :param assets_per_page: number of items to retrieve per request. Defaults to 100.
    :param sort_by: field to sort by. Defaults to 'effectiveDate'.
    :param sort_order: sort order. Defaults to 'ASC'.
    :param max_threads: maximum number of threads to use. Defaults to 8. Set to 0 to disable multithreading.
    :param save_parsed_to_files: True to store data in json file. Defaults to True. Could create lots of files (1 file per asset).
    :param load_from_files: True to load the data from files instead of scraping it. Defaults to False. If set to True, save_parsed_to_files will be set to False and use_database will be set to True.
    :param keep_intermediate_files: True to keep the intermediate json files. Defaults to None. If None, the files will be kept only if debug_mode is True.
    :param store_ids: True to store and save the IDs of the assets. Defaults to False. Could be memory consuming.
    :param clean_database: True to clean the database before saving the data. Defaults to False.
    :param debug_mode: True to enable debug mode. Defaults to False.
    :param offline_mode: True to enable offline mode. Defaults to False.
    :param progress_window: ProgressWindow object. Defaults to None. If None, a new ProgressWindow object will be created.
    :param core: AppCore object. Defaults to None. If None, a new AppCore object will be created.
    :param timeout: timeout for the request. Could be a float or a tuple of float (connect timeout, read timeout).
    :param filter_category: category to filter the data. Defaults to '' (no filter).
    """

    logger = logging.getLogger(__name__.split('.')[-1])  # keep only the class name
    update_loggers_level(logger)

    def __init__(
        self,
        datasource_filename: str = '',
        use_database: bool = True,
        start: int = 0,
        stop: int = 0,
        assets_per_page: int = 100,
        sort_by: str = 'effectiveDate',  # other values: 'title','currentPrice','discountPercentage'
        sort_order: str = 'DESC',  # other values: 'ASC'
        max_threads: int = 8,
        save_parsed_to_files: bool = True,
        load_from_files: bool = False,
        keep_intermediate_files=None,
        store_ids: bool = False,
        clean_database: bool = False,
        debug_mode=False,
        offline_mode=False,
        progress_window=None,  # don't use a typed annotation here to avoid import
        core: AppCore = None,
        timeout: (float, float) = (7, 7),
        filter_category: str = ''
    ) -> None:
        self._last_run_filename: str = 'last_run.json'
        self._urls_list_filename: str = 'urls_list.txt'
        self._threads_count: int = 0
        self._files_count: int = 0
        self._thread_executor = None
        self._scraped_data = []  # the scraper scraped_data. Increased on each call to get_data_from_url(). Could be huge !!
        self._ignored_asset_names = []

        self._data_source: str = datasource_filename
        self._scraped_ids = []  # store IDs of all items
        self._owned_asset_ids = []  # store IDs of all owned items
        self._urls = []  # list of all urls to scrap

        self.use_database: bool = use_database
        self.start: int = start
        self.stop: int = stop
        self.assets_per_page: int = assets_per_page
        self.sort_by: str = sort_by
        self.sort_order: str = sort_order
        self.max_threads: int = max_threads if gui_g.s.use_threads else 0
        self.save_parsed_to_files: bool = save_parsed_to_files
        self.load_from_files: bool = load_from_files
        self.keep_intermediate_files: bool = keep_intermediate_files if keep_intermediate_files is not None else gui_g.s.debug_mode
        self.store_ids = store_ids
        self.clean_database: bool = clean_database
        self.debug_mode = debug_mode
        self.offline_mode = offline_mode
        self.progress_window = progress_window or FakeProgressWindow()
        self.core = AppCore(timeout=timeout) if core is None else core
        if debug_mode and self.core and self.core.egs:
            self.core.egs.debug_mode = debug_mode
        self.timeout = timeout
        self.filter_category = filter_category

        self.asset_db_handler = None
        self.has_been_cancelled = False

        if not datasource_filename:
            message = 'Database mode is used but no database filename has been provided' if use_database else 'File mode is used but no filename has been provided'
            self._log(message, 'error')
            return
        if self.load_from_files:
            self.save_parsed_to_files = False  # no need to save if the source are the files , they won't be changes
            # self.use_database = True

        if (assets_per_page > 100) or (assets_per_page < 1):
            self.assets_per_page = 100
            self._log(f'assets_per_page must be between 1 and 100. Set to 100', 'error')

        message = f'UEAssetScraper initialized with max_threads= {max_threads}, start= {start}, stop= {stop}, assets_per_page= {assets_per_page}, sort_by= {sort_by}, sort_order= {sort_order}'
        message += f'\nData will be load from files in {gui_g.s.assets_data_folder}' if self.load_from_files else ''
        message += f'\nAsset Data will be saved in files in {gui_g.s.assets_data_folder}' if self.save_parsed_to_files else ''
        message += f'\nOwned Asset Data will be saved in files in {gui_g.s.owned_assets_data_folder}' if self.save_parsed_to_files else ''
        message += f'\nAsset Ids will be saved in {self._last_run_filename} or in database' if self.store_ids else ''
        if self.use_database:
            self.asset_db_handler = UEAssetDbHandler(self._data_source)
            message += f'\nData will be saved in DATABASE in {self._data_source}'
        else:
            message += f'\nData will be saved in FILE in {self._data_source}'
        if self.filter_category:
            message += f'The String "{self.filter_category}" will be search in Assets category'
        self._log(message)

    @property
    def scraped_data(self) -> list:
        """ Return the scraped data. """
        return self._scraped_data

    @property
    def data_source_filename(self):
        """ Get the name of the database to save the data to."""
        return self._data_source

    @data_source_filename.setter
    def data_source_filename(self, value: str):
        """ Set the name of the data source to save the data to."""
        if not value or self._data_source == value:
            return
        self._data_source = value
        if self.use_database:
            if self.asset_db_handler:
                self.asset_db_handler.init_connection()
            else:
                self.asset_db_handler = UEAssetDbHandler(self.data_source_filename)

    def _log(self, message: str, level: str = 'info'):
        level_lower = level.lower()
        if level_lower == 'debug':
            """ a simple wrapper to use when cli is not initialized"""
            if gui_g.UEVM_cli_ref is None and self.debug_mode:
                print(f'DEBUG: {message}')
            else:
                if gui_g.s.testing_switch >= 1:
                    # force printing debug messages when testing
                    self.logger.info(message)
                else:
                    self.logger.debug(message)
        elif level_lower == 'info':
            """ a simple wrapper to use when cli is not initialized"""
            if gui_g.UEVM_cli_ref is None:
                print(f'INFO: {message}')
            else:
                self.logger.info(message)
        elif level_lower == 'warning':
            """ a simple wrapper to use when cli is not initialized"""
            if gui_g.UEVM_cli_ref is None:
                print(f'WARNING: {message}')
            else:
                self.logger.warning(message)
        elif level_lower == 'error':
            """ a simple wrapper to use when cli is not initialized"""
            if gui_g.UEVM_cli_ref is None:
                print(f'ERROR: {message}')
            else:
                self.logger.error(message)

    def _log_for_task(self, message: str):
        """ a simple wrapper for a scraptask. It allows to set the level that could not be passed as parameter"""
        self._log(message, level='debug')

    def _parse_data(self, json_data_from_egs: dict = None) -> list:
        """
        Parse on or more asset data from the response of an url query.
        :param json_data_from_egs: dictionary containing the data to parse.
        :return: list of parsed data
        """
        returned_assets_json_data_parsed = []
        if not self.progress_window.continue_execution:
            # this could accur when running in threads and the process has been cancelled by the "stop" button
            return returned_assets_json_data_parsed

        if json_data_from_egs is None:
            return returned_assets_json_data_parsed
        try:
            # get the list of assets after a "scraping" of the json data using URL
            assets_json_data_from_egs = json_data_from_egs['data']['elements']
        except KeyError:
            # this exception is raised when data come from a json file. Not an issue
            # create a list of one asset when data come from a json file
            assets_json_data_from_egs = [json_data_from_egs]

        asset_db_handler = self.asset_db_handler
        use_database = self.use_database and asset_db_handler
        for one_asset_json_data_from_egs_ori in assets_json_data_from_egs:
            # !! ALL DATA HERE ARE STORED IN are already in json format. no need to decode them !!
            # WARNING: asset_data_ori WILL ALSO BE MODIFIED OUTSIDE the method and changed WILL BE SAVED in the json files

            # copy all existing data to the result_data to avoid missing one
            one_asset_json_data_parsed = one_asset_json_data_from_egs_ori.copy()
            uid = one_asset_json_data_from_egs_ori.get('id', '')
            if not uid:
                # this should never occur
                self._log(f'No id found for current asset. Passing to next asset', level='warning')
            else:
                asset_existing_data = {}
                if use_database:
                    try:
                        existing_data = asset_db_handler.get_assets_data(get_sql_preserved_fields(), uid)
                    except (Exception, ):
                        self._log(f'An error occurs with database when calling the get_assets_data method. Asset is skipped', level='error')
                        continue
                    asset_existing_data = existing_data.get(uid, {})
                categories = one_asset_json_data_from_egs_ori.get('categories', [])

                # releases
                # release_info = gui_fn.get_and_check_release_info(json_asset_data_ori.get('releaseInfo', []))
                release_info = list(one_asset_json_data_from_egs_ori.get('releaseInfo', []))
                one_asset_json_data_parsed['release_info'] = release_info
                latest_release = release_info[-1] if release_info else {}
                first_release = release_info[0] if release_info else {}

                # get app_name from asset_data or from the release_info
                app_name = one_asset_json_data_from_egs_ori.get('app_name', '')
                if not app_name:
                    app_name, found = self.core.uevmlfs.get_app_name_from_asset_data(one_asset_json_data_from_egs_ori.copy())
                    one_asset_json_data_parsed['app_name'] = app_name
                    if not found:
                        self._log(f'No app_name found for asset with id={uid}.The dummy value {app_name} has be used instead', level='warning')
                # add the app_name to the asset_data, and it will be saved in the json file
                one_asset_json_data_from_egs_ori['app_name'] = app_name
                origin = gui_g.s.origin_marketplace  # by default when scraped from marketplace
                date_now = datetime.now().strftime(DateFormat.csv)
                grab_result = GrabResult.NO_ERROR.name

                # make some calculation with the "raw" data
                # ------------
                # simple fields
                seller = one_asset_json_data_from_egs_ori.get('seller', {})
                author = seller.get('name', '') if seller else one_asset_json_data_from_egs_ori.get('developer', '')
                one_asset_json_data_parsed['author'] = author
                one_asset_json_data_parsed['page_title'] = one_asset_json_data_from_egs_ori['title']
                one_asset_json_data_parsed['origin'] = origin
                one_asset_json_data_parsed['update_date'] = date_now
                one_asset_json_data_parsed['downloaded_size'] = self.core.uevmlfs.get_asset_size(
                    app_name, gui_g.no_text_data
                )  # '' because we want the cell to be empty if no size

                # license
                description = one_asset_json_data_from_egs_ori.get('longDescription', '')
                lic_unknown = 'Unknown'
                license_type = lic_unknown  # by default
                for key, search in gui_g.s.license_types.items():
                    if key != lic_unknown and search in description:
                        license_type = key
                        break
                one_asset_json_data_parsed['license'] = license_type

                # thumbnail_url
                one_asset_json_data_parsed['thumbnail_url'] = one_asset_json_data_from_egs_ori.get('thumbnail', '')
                if not one_asset_json_data_parsed['thumbnail_url']:
                    try:
                        key_images = one_asset_json_data_from_egs_ori.get('keyImages', [])
                        # search for the image with the key 'Thumbnail'
                        for image in key_images:
                            if image['type'] == 'Thumbnail':
                                one_asset_json_data_parsed['thumbnail_url'] = image['url']
                                break
                    except IndexError:
                        self._log(f'asset {app_name} has no image', level='debug')

                # category and FILTER
                if categories:
                    category = categories[0].get('name', '') or categories[0].get('path', '') or ''
                    category = str(category)
                    category_lower = category.lower()
                    if self.filter_category and self.filter_category.lower() not in category_lower:
                        self._log(
                            f'{app_name} has been FILTERED by category ("{self.filter_category}" text not found in "{category_lower}").It has been added to the ignored_logger file'
                        )
                        self._ignored_asset_names.append(app_name)
                        if self.core.ignored_logger:
                            self.core.ignored_logger.info(app_name)
                        continue
                    else:
                        one_asset_json_data_parsed['category'] = category

                # asset_id
                try:
                    asset_id = latest_release['appId']
                except (Exception, ):
                    grab_result = GrabResult.NO_APPID.name
                    asset_id = uid  # that's not the REAL asset_id, we use the uid instead
                one_asset_json_data_parsed['asset_id'] = asset_id

                # asset slug and asset url
                # we keep UrlSlug here because it can arise from the scraped data
                asset_slug = (
                    one_asset_json_data_from_egs_ori.get('urlSlug', gui_g.no_text_data)  #
                    or one_asset_json_data_from_egs_ori.get('asset_slug', gui_g.no_text_data)
                )
                if asset_slug == gui_g.no_text_data:
                    asset_url = gui_g.no_text_data
                    self._log(f'No asset_slug found for asset id={uid}. Its asset_url will be empty', level='warning')
                else:
                    asset_url = self.core.egs.get_marketplace_product_url(asset_slug)
                one_asset_json_data_parsed['asset_slug'] = asset_slug
                one_asset_json_data_parsed['asset_url'] = asset_url
                if 'urlSlug' in one_asset_json_data_parsed:
                    one_asset_json_data_parsed.pop('urlSlug')  # we remove the duplicate field to avoid future mistakes

                # prices and discount
                price = self.core.egs.extract_price(one_asset_json_data_from_egs_ori.get('price', gui_g.no_text_data), asset_name=app_name)
                discount_price = self.core.egs.extract_price(one_asset_json_data_from_egs_ori.get('discount_price', gui_g.no_float_data))
                discount_percentage = int(one_asset_json_data_from_egs_ori.get('discount_percentage', gui_g.no_int_data))
                if one_asset_json_data_from_egs_ori.get('priceValue', 0) > 0:
                    # tbh the logic here is flawed as hell lol. discount should only be set if there's a discount Epic wtf
                    # price = asset_data['priceValue'] if asset_data['priceValue'] == asset_data['discountPriceValue'] else asset_data['discountPriceValue'] # here we keep the CURRENT price
                    price = float(one_asset_json_data_from_egs_ori['priceValue'])  # here we keep the NORMAL price
                    discount_price = float(one_asset_json_data_from_egs_ori['discountPriceValue'])
                    # price are in cents
                    price /= 100
                    discount_price /= 100
                    discount_percentage = 100 - int(one_asset_json_data_from_egs_ori['discountPercentage'])
                    # discount_percentage = 0.0 if (discount_price == 0.0 or price == 0.0 or discount_price == price) else int((price-discount_price) / price * 100.0)
                if discount_price == gui_g.no_int_data:
                    discount_price = price
                one_asset_json_data_parsed['price'] = price
                one_asset_json_data_parsed['discount_price'] = discount_price
                one_asset_json_data_parsed['discount_percentage'] = discount_percentage

                # old price
                old_price = asset_existing_data.get('price', gui_g.no_float_data)
                older_price = asset_existing_data.get('old_price', gui_g.no_float_data)
                one_asset_json_data_parsed['old_price'] = old_price if old_price else older_price

                # rating
                average_rating = one_asset_json_data_from_egs_ori.get('review', gui_g.no_int_data)
                rating_total = gui_g.no_int_data
                if one_asset_json_data_from_egs_ori.get('rating', ''):
                    try:
                        average_rating = one_asset_json_data_from_egs_ori['rating']['averageRating']
                        rating_total = one_asset_json_data_from_egs_ori['rating']['total']
                    except KeyError:
                        self._log(f'No rating for {one_asset_json_data_from_egs_ori["title"]}', 'debug')
                        # check if self has asset_db_handler
                        if use_database:
                            try:
                                average_rating, rating_total = asset_db_handler.get_rating_by_id(uid)
                            except (Exception,):
                                self._log(f'An error occurs with database when calling the get_rating_by_id method. Asset is skipped', level='error')
                                continue
                one_asset_json_data_parsed['review'] = average_rating
                one_asset_json_data_parsed['review_count'] = rating_total

                # custom attributes
                one_asset_json_data_parsed['custom_attributes'] = ''
                try:
                    custom_attributes = one_asset_json_data_from_egs_ori.get('customAttributes', '')
                    if isinstance(custom_attributes, dict):
                        # check for "has an external link"
                        custom_attributes = 'external_link:' + custom_attributes['BuyLink']['value'] if custom_attributes.get('BuyLink', '') else ''
                        one_asset_json_data_parsed['custom_attributes'] = custom_attributes
                except (KeyError, AttributeError):
                    one_asset_json_data_parsed['custom_attributes'] = gui_g.no_text_data

                # supported_versions
                supported_versions = ''
                try:
                    tmp_list = [check_and_convert_list_to_str(item.get('compatibleApps')) for item in release_info]
                    supported_versions = check_and_convert_list_to_str(tmp_list) or supported_versions
                except TypeError as error:
                    self._log(f'Error getting compatibleApps for asset with uid={uid}: {error!r}', level='debug')
                one_asset_json_data_parsed['supported_versions'] = supported_versions

                # dates
                # asset_data['creation_date'] = asset_data['creationDate']  # does not exist in when scraping from marketplace
                # we use the first realase date instead as it exist in both cases
                tmp_date = first_release.get('dateAdded', gui_g.no_text_data) if first_release else gui_g.no_text_data
                tmp_date = gui_fn.convert_to_datetime(tmp_date, formats_to_use=[DateFormat.epic, DateFormat.csv])
                tmp_date = gui_fn.convert_to_str_datetime(tmp_date, DateFormat.csv)
                one_asset_json_data_parsed['creation_date'] = tmp_date
                one_asset_json_data_parsed['date_added'] = asset_existing_data.get('date_added', date_now)

                # obsolete
                try:
                    engine_version_for_obsolete_assets = (
                        gui_g.UEVM_cli_ref.core.engine_version_for_obsolete_assets or gui_g.s.engine_version_for_obsolete_assets
                    )
                except (Exception, ):
                    engine_version_for_obsolete_assets = None
                one_asset_json_data_parsed['obsolete'] = is_asset_obsolete(supported_versions, engine_version_for_obsolete_assets)

                # grab_result and old_grab_result
                # old_grab_result = asset_existing_data.get(
                #     'grab_result', GrabResult.NO_ERROR.name
                # ) if asset_existing_data else GrabResult.NO_ERROR.name
                # if owned_assets_only and old_grab_result == GrabResult.NO_ERROR.name:
                #     # if no error occurs and if we only parse owned assets, the parsed data ARE less complete than the "normal" one
                #     # so, we set the grab result to PARTIAL
                #     grab_result = GrabResult.PARTIAL.name
                one_asset_json_data_parsed['grab_result'] = grab_result

                # we use copy data for user_fields to preserve user data
                if asset_existing_data.get('origin', '') == gui_g.s.origin_marketplace:
                    # Remove some existing fields to avoid keeping "incoherent" values when scraping EXISTING data from the marketplace
                    fields_to_remove = ['category', 'asset_url', 'added_manually']
                    asset_existing_data = {field: value for field, value in asset_existing_data.items() if field not in fields_to_remove}

                if asset_existing_data and use_database:
                    # for field in get_sql_user_fields():
                    for field in get_sql_preserved_fields():
                        existing_value = asset_existing_data.get(field, None)
                        if existing_value:
                            one_asset_json_data_parsed[field] = existing_value
                # installed_folders and tags
                installed_folders_str = one_asset_json_data_parsed.get('installed_folders', '')
                asset_installed = self.core.uevmlfs.get_installed_asset(asset_id)  # from current existing install
                if asset_installed:
                    asset_installed_folders = asset_installed.installed_folders
                    installed_folders_str = gui_fn.merge_lists_or_strings(installed_folders_str, asset_installed_folders)
                tags = one_asset_json_data_from_egs_ori.get('tags', [])
                if use_database:
                    try:
                        # get tag name from tag id and convert the list into a comma separated string
                        tags_str = asset_db_handler.convert_tag_list_to_string(tags)
                    except (Exception,):
                        self._log(f'An error occurs with database when calling the convert_tag_list_to_string method. Asset is skipped', level='error')
                        continue
                    # asset_data['installed_folders'] = installed_folders_str
                else:
                    # with no database, we don't have access to the tags table. So we keep the tags as a list of dicts and extract the names when exists
                    # tags could be a list of dicts (new version). Get all the "name" fields and save them into tags_str
                    try:
                        tags_str = ','.join([tag.get('name', '').title() for tag in tags])
                    except (Exception, ):
                        # no dict, so this is the oldest version, with just a list of ids
                        tags_str = check_and_convert_list_to_str(tags)
                    installed_folders_str = check_and_convert_list_to_str(one_asset_json_data_from_egs_ori.get('installed_folders', []))
                one_asset_json_data_parsed['installed_folders'] = installed_folders_str
                one_asset_json_data_parsed['tags'] = tags_str

                # we use an UEAsset object to store the data and create a valid dict from it
                ue_asset = UEAsset()
                ue_asset.init_from_dict(one_asset_json_data_parsed)
                data = ue_asset.get_data()
                if data.get('id', None) is None:
                    # this should never occur
                    self._log(f'No id found for current asset. Passing to next asset', level='warning')
                    continue
                # keep only fields that are in "valid" (filter all unused fields from the json file)
                cleaned_data = {key: data.get(key, '') for key in get_sql_field_name_list(include_asset_only=True)}
                returned_assets_json_data_parsed.append(cleaned_data)
                message = f'Asset with uid={uid} added to content: owned={ue_asset.get("owned")} creation_date={ue_asset.get("creation_date")}'
                self._log(message, 'debug')  # use debug here instead of info to avoid spamming the log file
                if self.store_ids:
                    try:
                        self._scraped_ids.append(uid)
                    except (AttributeError, TypeError) as error:
                        self._log(f'Error when adding uid to self.scraped_ids: {error!r}', 'debug')
            # end else if uid:
        # end for asset_data in json_data['data']['elements']:
        return returned_assets_json_data_parsed

    def _save_final_in_db(self, last_run_content: dict) -> bool:
        """
        Stores the asset data in the database.
        """
        if not self.use_database:
            return False
        # convert the list of ids to a string for the database only
        last_run_content['scraped_ids'] = check_and_convert_list_to_str(self._scraped_ids) if self.store_ids else ''

        if self.clean_database:
            # next line will delete all assets in the database
            if box_yesno(
                'Current settings and params are set to delete all existing data before rebuilding. All user fields values will be lost. Are you sure your want to do that ?'
            ):
                self.asset_db_handler.delete_all_assets(keep_added_manually=True)
        is_ok = self.asset_db_handler.set_assets(self._scraped_data)
        self.asset_db_handler.save_last_run(last_run_content)
        return is_ok

    def _update_and_merge_csv_record_data(self, _asset_id: str, _csv_field_name_list: [], _csv_record: [], _assets_in_file) -> list:
        """
        Updates the data of the asset with the data from the items in the file.
        :param _asset_id: id of the asset to update.
        :param _csv_field_name_list: list of the CSV field names.
        :param _csv_record: LIST of data of the asset to update. Must be sorted in the same order as csv_field_name_list.
        :param _assets_in_file: list of items in the file.
        :return: list of values to be written in the CSV file.
        """
        # merge data from the items in the file (if exists) and those get by the application
        # items_in_file must be a dict of dicts
        file_fields_count = len(_csv_field_name_list)
        if _assets_in_file.get(_asset_id):
            item_in_file = _assets_in_file.get(_asset_id)
            keys_check = item_in_file.keys()
            if gui_g.s.index_copy_col_name in keys_check:
                file_fields_count += 1
            if len(keys_check) != file_fields_count:
                self._log(
                    f'In the existing file, asset {_asset_id} has not the same number of keys as the CSV headings. This asset is ignored and its values will be overwritten',
                    'error'
                )
                return _csv_record
            else:
                # loops through its columns to UPDATE the data with EXISTING VALUE if its state is PRESERVED
                # !! no data cleaning must be done here !!!!
                price_index = 0
                _price = float(gui_g.no_float_data)
                old_price = float(gui_g.no_float_data)
                for index, _csv_field in enumerate(_csv_field_name_list):
                    preserved_value_in_file = is_preserved(csv_field_name=_csv_field)
                    value = item_in_file.get(_csv_field, None)
                    if value is None:
                        self._log(f'In the existing data, asset {_asset_id} has no column named {_csv_field}.', level='warning')
                        continue
                    # get rid of 'None' values in CSV file
                    if value in gui_g.s.cell_is_nan_list:
                        _csv_record[index] = ''
                        continue
                    value = str(value)
                    # Get the old price in the previous file
                    if _csv_field == 'Price':
                        price_index = index
                        _price = gui_fn.convert_to_float(_csv_record[price_index])
                        old_price = gui_fn.convert_to_float(
                            item_in_file[_csv_field]
                        )  # Note: 'old price' is the 'price' saved in the file, not the 'old_price' in the file
                    elif _csv_field == 'Origin':
                        # all the folders when the asset came from are stored in a comma separated list
                        if isinstance(value, str):
                            folder_list = value.split(',')
                        else:
                            folder_list = value if value else []
                        # add the new folder to the list without duplicates
                        if _csv_record[index] not in folder_list:
                            folder_list.append(_csv_record[index])
                        # update the list in the CSV record
                        _csv_record[index] = ','.join(folder_list)  # keep join() here to raise an error if installed_folders is not a list of strings

                    if preserved_value_in_file:
                        _csv_record[index] = str_to_bool(value) if str_is_bool(value) else value
                # end for key, state in csv_sql_fields.items()
                if price_index > 0:
                    _csv_record[price_index + 1] = old_price
            # end ELSE if len(item_in_file.keys()) != file_fields_count
        # end if _assets_in_file.get(_asset_id)
        # print(f'debug here')
        return _csv_record

        # end self._update_and_merge_csv_record_data

    def _update_and_merge_json_record_data(self, _asset, _assets_in_file, _no_float_value: float, _no_bool_false_value: bool) -> dict:
        """
        Updates the data of the asset with the data from the items in the file.
        :param _asset: asset to update.
        :param _assets_in_file: list of assets in the file.
        :param _no_float_value:  value to use when no float data is available.
        :param _no_bool_false_value: value (False) to use when no bool data is available.
        :return: dict of data of the asset to update.
        """
        _asset_id = _asset[0]
        _json_record = _asset[1]

        # merge data from the items in the file (if exists) and those get by the application
        # items_in_file is a dict of dict
        if _assets_in_file.get(_asset_id):
            # loops through its columns
            _price = float(_no_float_value)
            old_price = float(_no_float_value)
            for field, state in csv_sql_fields.items():
                preserved_value_in_file = is_preserved(csv_field_name=field)
                if preserved_value_in_file and _assets_in_file[_asset_id].get(field):
                    _json_record[field] = _assets_in_file[_asset_id][field]

            # Get the old price in the previous file
            try:
                _price = float(_json_record['Price'])
                old_price = float(
                    _assets_in_file[_asset_id]['Price']
                )  # Note: 'old price' is the 'price' saved in the file, not the 'old_price' in the file
            except Exception as _error:
                self._log(f'Old price values can not be converted for asset {_asset_id}\nError:{_error!r}', level='warning')
            _json_record['Old price'] = old_price
        return _json_record

    # end def update_and_merge_json_record_data

    def _save_final_in_file(self, filename: str = '', save_to_format: str = 'csv') -> bool:
        """
        Save the scraped data into a file.
        :param filename: name of the file to save the data to. Used only when use_database is False.
        :param save_to_format: format of the file to save the data. Sould be 'csv','tcsv' or 'json'. Used only when use_database is False.
        :return: True if the data have been saved, False otherwise.
        """
        assets_to_output = {}
        asset_count = 0
        assets_in_file = {}
        output = None
        self.progress_window.reset(new_value=0, new_text="Converting data to csv...It could take some time", new_max_value=len(self._scraped_data))
        for asset_data in self._scraped_data:
            if not self.progress_window.update_and_continue(increment=1):
                return False
            asset_id = asset_data['asset_id']
            assets_to_output[asset_id] = convert_data_to_csv(sql_asset_data=asset_data)

        if save_to_format == 'tcsv' or save_to_format == 'csv':
            # If the output file exists, we read its content to keep some data
            try:
                with open(filename, 'r', encoding='utf-8') as output:
                    csv_file_content = csv.DictReader(output)
                    # get the data (it's a dict)
                    for csv_record in csv_file_content:
                        # noinspection PyTypeChecker
                        csv_record = dict(csv_record)
                        if 'urlSlug' in csv_record:
                            del (csv_record['urlSlug'])  # we remove the duplicate field to avoid future mistakes
                        asset_id = csv_record['Asset_id']
                        assets_in_file[asset_id] = csv_record
                    output.close()
            except (FileExistsError, OSError, UnicodeDecodeError, StopIteration):
                self._log(f'Could not read CSV record from the file {filename}', level='warning')
            # reopen file for writing
            output = open(filename, 'w', encoding='utf-8')
            writer = csv.writer(output, dialect='excel-tab' if save_to_format == 'tcsv' else 'excel', lineterminator='\n')

            # get final the csv fields name list by
            csv_field_name_list = get_csv_field_name_list()
            columns_infos = gui_g.s.get_column_infos(DataSourceType.FILE)
            sorted_cols_by_pos = dict(sorted(columns_infos.items(), key=lambda item: item[1]['pos']))
            new_csv_field_name_list = []
            # add the csv fields in the same order as in the columns_infos
            for col_name in sorted_cols_by_pos:
                if col_name in csv_field_name_list:
                    new_csv_field_name_list.append(col_name)
            # add the csv fields that could be missing in the columns_infos
            for col_name in csv_field_name_list:
                if col_name not in csv_field_name_list:
                    new_csv_field_name_list.append(col_name)

            # remove the "index copy" field from the list
            if gui_g.s.index_copy_col_name in new_csv_field_name_list:
                new_csv_field_name_list.remove(gui_g.s.index_copy_col_name)

            writer.writerow(new_csv_field_name_list)
            self.progress_window.reset(new_value=0, new_text="Writing assets into csv file...", new_max_value=len(assets_to_output.items()))
            for asset_id, asset_data in assets_to_output.items():
                if not self.progress_window.update_and_continue(increment=1):
                    return False
                for key in asset_data.keys():
                    # clean the asset data by removing the columns that are not in the csv field name list
                    ignore_in_csv = is_on_state(csv_field_name=key, states=[CSVFieldState.ASSET_ONLY], default=False)
                    if ignore_in_csv:
                        self._log(f'{key} must be ignored in CSV. Removing it from the asset data', 'debug')
                        del (asset_data[key])

                csv_record = []  # values must be sorted by the csv field name
                for csv_field in new_csv_field_name_list:
                    csv_record.append(asset_data.get(csv_field, gui_g.no_text_data))

                if len(assets_in_file) > 0:
                    csv_record_merged = self._update_and_merge_csv_record_data(
                        _asset_id=asset_data['Asset_id'],
                        _csv_field_name_list=new_csv_field_name_list,
                        _csv_record=csv_record,
                        _assets_in_file=assets_in_file
                    )
                else:
                    csv_record_merged = csv_record
                asset_count += 1
                writer.writerow(csv_record_merged)

        elif save_to_format == 'json':
            # TODO: test the json result file
            # If the output file exists, we read its content to keep some data
            try:
                with open(filename, 'r', encoding='utf-8') as output:
                    assets_in_file = json.load(output)
            except (FileExistsError, OSError, UnicodeDecodeError, StopIteration, json.decoder.JSONDecodeError):
                self._log(f'Could not read Json record from the file {filename}', level='warning')
            # reopen file for writing
            output = open(filename, 'w', encoding='utf-8')
            json_content = {}
            self.progress_window.reset(new_value=0, new_text="Writing assets into json file...", new_max_value=len(assets_to_output.items()))
            for asset_id, asset_data in assets_to_output:
                if not self.progress_window.update_and_continue(increment=1):
                    return False
                if len(assets_in_file) > 0:
                    json_record_merged = self._update_and_merge_json_record_data(
                        asset_data, assets_in_file, gui_g.no_float_data, gui_g.no_bool_false_data
                    )
                else:
                    json_record_merged = asset_data
                try:
                    asset_id = json_record_merged['Asset_id']
                    json_content[asset_id] = json_record_merged
                    asset_count += 1
                except (OSError, UnicodeEncodeError, TypeError) as error:
                    message = f'Could not write Json record for {asset_id} into {filename}\nError:{error!r}'
                    self._log(message, level='error')
            json.dump(json_content, output, indent=2)

        # close the opened file
        if output is not None:
            output.close()
        self._log(f'\n======\n{asset_count} assets have been saved (without duplicates due to different UE versions)\nOperation Finished\n======\n')
        return True

    def _stop_executor(self) -> None:
        """
        Cancel all outstanding tasks and shut down the executor.
        """
        self._thread_executor.shutdown(wait=False, cancel_futures=True)

    def _future_has_ended(self, future_param):
        self._log(f'{future_param} has ended.', 'debug')
        # HERE WE CAN'T UPDATE the progress window because it's not in the main thread
        # the next lines raise does nothing because the stop button state is never updated
        # if not self.progress_window.continue_execution:
        #     self._log(f'{future_param} has been cancelled. Waiting all others to be terminated.', 'info')
        #     self.progress_window.close_window()  # must be done here because we will never return to the caller
        #     self._stop_executor()

    def gather_all_assets_urls(self, egs_available_assets_count: int = -1, empty_list_before=True, save_result=True) -> int:
        """
        Gather all the URLs (with pagination) to be parsed and stores them in a list for further use.
        :param egs_available_assets_count: number of assets available on the marketplace. If not given, it will be retrieved from the EGS API.
        :param empty_list_before: whether the list of URLs is emptied before adding the new ones.
        :param save_result: whether the list of URLs is saved into a text file.
        :return: number of assets to be scraped or -1 if the offline mode is active or if the process has been interrupted.
        """
        if self.offline_mode:
            self._log('The offline mode is active. No online data could be retreived')
            return -1
        start_time = time.time()
        if egs_available_assets_count <= 0:
            egs_available_assets_count = self.core.egs.get_available_assets_count()
        if empty_list_before:
            self._urls = []
        if self.stop <= 0 < egs_available_assets_count:
            self.stop = egs_available_assets_count
        assets_to_scrap = self.stop - self.start
        pages_count = int(assets_to_scrap / self.assets_per_page)
        if (assets_to_scrap % self.assets_per_page) > 0:
            pages_count += 1
        self.progress_window.reset(new_value=0, new_text='Gathering URLs', new_max_value=pages_count)
        for i in range(int(pages_count)):
            if not self.progress_window.update_and_continue(value=i, text=f'Gathering URL ({i + 1}/{pages_count})'):
                return -1
            start = self.start + (i * self.assets_per_page)
            url = self.core.egs.get_scrap_url(start, self.assets_per_page, self.sort_by, self.sort_order)
            self._urls.append(url)
        if self._urls:
            self._log(f'It took {(time.time() - start_time):.3f} seconds to gather {len(self._urls)} urls')
        else:
            self._log('No url has been gathered', 'warning')
        if save_result:
            self.save_to_file(filename=self._urls_list_filename, data=self._urls, is_json=False, is_owned=False)
        return assets_to_scrap

    def get_data_from_url(self, url='') -> GetDataResult:
        """
        Grab the data from the given url and stores it in the scraped_data property.
        :param url: url to grab the data from. If not given, uses the url property of the class.
        :return: GetDataResult value depending on the result
        """
        thread_state = ' RUNNING...'
        self._files_count = 0
        # HERE WE CAN'T UPDATE the progress window because it's not in the main thread
        # the next lines raise a  RuntimeError('main thread is not in main loop')
        # if not self.progress_window.update_and_continue(increment=1, text=f'Getting data from {url}):
        # self.progress_window.update()
        if not self.progress_window.continue_execution:
            thread_state = ' CANCELLING...'
            self._log(f'{url} has been cancelled. Waiting all others to be terminated {thread_state}.', 'info')
            # self.progress_window.close_window()  # must be done here because we will never return to the caller
            self._stop_executor()
            return GetDataResult.CANCELLED
        if not url:
            self._log('No url given to get_data_from_url()', 'error')
            return GetDataResult.NO_URL
        if self.offline_mode:
            self._log('The offline mode is active. No online data could be retreived')
            return GetDataResult.BAD_CONTEXT
        thread_data = ''
        no_error = False
        json_data_from_egs_url = {}
        try:
            if self._threads_count > 1:
                # add a delay when multiple threads are used
                time.sleep(random.uniform(0.5, 1.5))
                thread = current_thread()
                thread_data = f' ==> By Thread name={thread.name}'
            message = f'--- START scraping data from {url}{thread_data}{thread_state}'
            self._log(message)
            if self.core.scrap_asset_logger:
                self.core.scrap_asset_logger.info('\n' + message)

            try:
                # noinspection GrazieInspection
                """
                debug_value = 0  # other than 0 for debug purpose, changing the value during debug will change the test case
                if debug_value == 1:
                    # test for a 'common.server_error' error (http 431)
                    json_data_from_egs_url = self.core.egs.get_json_data_from_url( 'https://www.unrealengine.com/marketplace/api/assets?start=0&count=90&sortBy=effectiveDate&sortDir=DESC', override_timeout=gui_g.s.timeout_for_scraping)
                elif debug_value == 2:
                    # test for a timeout error
                    rand_start = random.randint(10, 350) * 100  # create a new url at each test to avoid server caching
                    json_data_from_egs_url = self.core.egs.get_json_data_from_url( f'https://www.unrealengine.com/marketplace/api/assets?start={rand_start}&count=50&sortBy=effectiveDate&sortDir=DESC', override_timeout=1 )
                else:
                    # normal case
                    json_data_from_egs_url = self.core.egs.get_json_data_from_url(url, override_timeout=gui_g.s.timeout_for_scraping)
                """
                json_data_from_egs_url = self.core.egs.get_json_data_from_url(url, override_timeout=gui_g.s.timeout_for_scraping)
                error_code = json_data_from_egs_url.get('errorCode', '')  # value returned by self.session.get() call inside get_json_data_from_url()
                no_error = (error_code == '')
            except (ReadTimeout, ):
                error_code = GetDataResult.TIMEOUT
            except (Exception, ):
                message = f'An Error occurs when decoding json data from url {url}. Trying to reload the page...'
                self._log(message, 'warning')
                if self.core.scrap_asset_logger:
                    self.core.scrap_asset_logger.warning(message)
                # try again
                try:
                    json_data_from_egs_url = self.core.egs.get_json_data_from_url(url, override_timeout=gui_g.s.timeout_for_scraping)
                    error_code = json_data_from_egs_url.get(
                        'errorCode', ''
                    )  # value returned by self.session.get() call inside get_json_data_from_url()
                    no_error = (error_code == '')
                except (Exception, ):
                    no_error = False
                    error_code = GetDataResult.JSON_DECODE
            if not no_error:
                if error_code == GetDataResult.TIMEOUT:
                    # mainly occurs because the timeout is too short for the number of asset to scrap
                    # the caller will try a bigger timeout
                    return error_code
                elif 'common.server_error' in error_code:
                    # mainly occurs because the number of asset to scrap is too big
                    # the caller will try a smaller number
                    return GetDataResult.ERROR_431
                elif error_code == GetDataResult.JSON_DECODE:
                    message = f'Json data can not be read from from url {url}'
                    self._log(message, 'error')
                    if self.core.scrap_asset_logger:
                        self.core.scrap_asset_logger.warning(message)
                else:
                    # other error
                    # the caller WON'T DO another try
                    message = f'Error getting data from url {url}: {error_code}'
                    self._log(message, 'error')
                    if self.core.scrap_asset_logger:
                        self.core.scrap_asset_logger.warning(message)
                return GetDataResult.ERROR
            try:
                # when multiple assets are returned, the data is in the 'elements' key
                count = len(json_data_from_egs_url['data']['elements'])
                self._log(f'==> parsed url {url}: got a list of {count} assets')
            except KeyError:
                # when only one asset is returned, the data is in the 'data' key
                self._log(f'==> parsed url {url} for one asset')
                json_data_from_egs_url['data']['elements'] = [json_data_from_egs_url['data']['data']]
            if json_data_from_egs_url:
                if self.keep_intermediate_files:
                    # store the GLOBAL result file in the raw format
                    try:
                        url_vars = gui_fn.extract_variables_from_url(url)
                        start = int(url_vars['start'])
                        count = int(url_vars['count'])
                        suffix = f'{start}-{start + count - 1}'
                    except (Exception, ):
                        suffix = datetime.now().strftime(DateFormat.file_suffix)
                    filename = f'assets_{suffix}.json'
                    self.save_to_file(filename=filename, data=json_data_from_egs_url, is_global=True)

                if self.save_parsed_to_files:
                    # store the RAW DATA of each asset in a file
                    for index, asset_data in enumerate(json_data_from_egs_url['data']['elements']):
                        filename, app_name = self.core.uevmlfs.get_filename_from_asset_data(asset_data)
                        if app_name in self._ignored_asset_names:
                            # already done in _parse_data()
                            # if self.core.ignored_logger
                            #     self.core.ignored_logger.info(app_name)
                            continue
                        asset_data['app_name'] = app_name
                        self.save_to_file(filename=filename, data=asset_data, is_owned=False)
                        self._files_count += 1
                try:
                    parsed_assets_data = self._parse_data(json_data_from_egs_url)  # could return a dict or a list of dict
                except (Exception, ) as error:
                    message = f'An Error occurs when saving data url {url}: {error!r}'
                    self._log(message, 'error')
                    if self.core.scrap_asset_logger:
                        self.core.scrap_asset_logger.warning(message)
                    return GetDataResult.ERROR
                if isinstance(parsed_assets_data, list):
                    self._scraped_data.append(parsed_assets_data)
                else:
                    self._scraped_data.append([parsed_assets_data])

                if self.core.scrap_asset_logger:
                    self.core.scrap_asset_logger.info(f'--- END scraping from {url}: {len(json_data_from_egs_url)} asset ADDED to scraped_data')
        except (Exception, ) as error:
            message = f'An Error occurs when getting data from url {url}: {error!r}'
            self._log(message, 'warning')
            if self.core.scrap_asset_logger:
                self.core.scrap_asset_logger.warning(message)
            return GetDataResult.ERROR
        return GetDataResult.OK

    def save_to_file(self, prefix='assets', filename=None, data=None, is_json=True, is_owned=False, is_global=False) -> bool:
        """
        Save JSON data to a file.
        :param data: dictionary containing the data to save. Defaults to None. If None, the data will be used.
        :param prefix: prefix to use for the file name. Defaults to 'assets'.
        :param filename: file name to use. Defaults to None. If None, a file name will be generated using the prefix and the start and count properties.
        :param is_json: boolean indicating whether the data is JSON or not. Defaults to True.
        :param is_owned: boolean indicating whether the data is owned assets or not. Defaults to False.
        :param is_global: boolean indicating whether if the data to save id the "global" result, as produced by the url scraping. Defaults to False.
        :return: boolean indicating whether the file was saved successfully.
        """
        if data is None:
            data = self._scraped_data
        if not data:
            self._log('No data to save', 'warning')
            return False

        folder = gui_g.s.owned_assets_data_folder if is_owned else gui_g.s.assets_global_folder if is_global else gui_g.s.assets_data_folder
        _, folder = gui_fn.check_and_get_folder(folder)
        if filename is None:
            filename = prefix
            if self.start > 0:
                filename += f'_{self.start}_{self.start + self.assets_per_page}'
            filename += '.json'
        filename = path_join(folder, filename)
        try:
            with open(filename, 'w', encoding='utf-8') as file:
                if is_json:
                    json.dump(data, file)
                else:
                    file.write('\n'.join(data))
            self._log(f'Data saved into {filename}', 'debug')
            return True
        except PermissionError as error:
            self._log(f'The following error occurred when saving data into {filename}: {error!r}', 'warning')
            return False

    def load_from_json_files(self, owned_assets_only=False) -> int:
        """
        Load all JSON data retrieved from the Unreal Engine Marketplace API to paginated files.
        :param owned_assets_only: whether to only the owned assets are scraped.
        :return: number of files loaded or -1 if the process has been interrupted.
        """
        start_time = time.time()
        text_saved = self.progress_window.get_text()
        self._files_count = 0
        self._scraped_ids = []
        self._scraped_data = []
        folder = gui_g.s.owned_assets_data_folder if owned_assets_only else gui_g.s.assets_data_folder
        files = os.listdir(folder)
        files_count = len(files)
        # Note: this data have the same structure as the table last_run inside the method UEAsset.create_tables()
        self._log(f'Loading {files_count} files from {folder}')
        self.progress_window.reset(new_value=0, new_text='Loading asset data from json files', new_max_value=files_count)
        for filename in files:
            if filename.endswith('.json') and filename != self._last_run_filename:
                # self._log(f'Loading {filename}','debug')
                with open(path_join(folder, filename), 'r', encoding='utf-8') as file:
                    try:
                        json_data_from_egs_file = json.load(file)
                    except json.decoder.JSONDecodeError as error:
                        self._log(f'The following error occured when loading data from {filename}:{error!r}', 'warning')
                        continue
                    parsed_assets_data = self._parse_data(json_data_from_egs_file)  # could return a dict or a list of dict
                    if isinstance(parsed_assets_data, list):
                        for parsed_asset_data in parsed_assets_data:
                            self._scraped_data.append(parsed_asset_data)
                    else:
                        self._scraped_data.append(parsed_assets_data)
                self._files_count += 1
                if not self.progress_window.update_and_continue(increment=1):
                    return -1
                if gui_g.s.testing_switch == 1 and self._files_count >= max(int(gui_g.s.testing_assets_limit / 10), 1000):
                    break
                # if self.progress_window.is_fake:
                #    self._log(f'{self._files_count}/{files_count} files loaded', 'info')  # could flood the console

        message = f'It took {(time.time() - start_time):.3f} seconds to load the data from {self._files_count} files'
        self._log(message)

        # debug an instance of asset (here the last one). MUST BE RUN OUTSIDE THE LOOP ON ALL ASSETS
        if (self.core.verbose_mode or gui_g.s.debug_mode) and self._scraped_data:
            debug_parsed_data(self._scraped_data[-1], DataSourceType.DATABASE)

        # save results in the last_run file
        content = {
            'date': str(datetime.now()),
            'mode': 'load_owned' if owned_assets_only else 'load',
            'files_count': self._files_count,
            'items_count': len(self._scraped_data),
            'scraped_ids': self._scraped_ids if self.store_ids else ''
        }
        filename = path_join(folder, self._last_run_filename)
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(content, file)

        self.progress_window.reset(new_value=0, new_text=text_saved, new_max_value=0)
        # self._save_in_db(last_run_content=content) # duplicate with a caller
        return self._files_count

    def save(self, owned_assets_only=False, save_last_run_file=True, save_to_format: str = 'csv') -> bool:
        """
        Save all JSON data retrieved from the Unreal Engine Marketplace API to paginated files.
        :param owned_assets_only: whether to only the owned assets are scraped.
        :param save_last_run_file: whether the last_run file is saved.
        :param save_to_format: format of the file to save the data. Sould be 'csv','tcsv' or 'json'. Used only when use_database is False.
        :return: True if OK, False if no.

        Notes:
            Execute the scraper. Load from files or downloads the items from the URLs and stores them in the scraped_data property.
            The execution is done in parallel using threads.
            If self.urls is None or empty, gather_urls() will be called first.
        """
        asset_loaded = 0
        if self.load_from_files:
            asset_loaded = self.load_from_json_files()
            if asset_loaded == -1:
                # stop has been pressed
                return False

        if self.use_database:
            tags_count_saved = self.asset_db_handler.get_rows_count('tags')
            rating_count_saved = self.asset_db_handler.get_rows_count('ratings')
        else:
            tags_count_saved, rating_count_saved = 0, 0

        if asset_loaded <= 0:
            # no data, ie no files loaded, so we have to save them
            self.load_from_files = False
            self.save_parsed_to_files = True
            start_time = time.time()
            if not self._urls:
                result_count = self.gather_all_assets_urls()  # return -1 if interrupted or error
                if result_count == -1:
                    self._log(f'An error has occured when retriving the urls list for assets to scrap.', 'error')
                    return False
                if result_count == 0:
                    self._log(f'No result has been returned when retriving the urls list for assets to scrap.', 'warning')
                    return False
            # test the first url to see if the data is available
            tries = 0
            max_tries = 3
            check = self.get_data_from_url(self._urls[0])
            while check != GetDataResult.OK and tries < max_tries:
                tries += 1
                if check == GetDataResult.ERROR_431:
                    self._log(
                        f'While testing the first url, we could not get data from url {self._urls[0]}.\nNew Try ({tries}/{max_tries}) with a lower number of scraped assets at once...',
                        'warning'
                    )
                    self.assets_per_page = int(self.assets_per_page * 0.7)  # 30% less
                    self._log(
                        f'The value of assets_per_page class has been adjusted to {self.assets_per_page}\nIf this message is repeated, you should change the value of assets_per_page in the GUISettings class',
                        'info'
                    )
                elif check == GetDataResult.TIMEOUT:
                    self._log(
                        f'While testing the first url, we could not get data from url {self._urls[0]}.\nNew Try ({tries}/{max_tries}) with a higher timeout value...',
                        'warning'
                    )
                    gui_g.s.timeout_for_scraping = int(gui_g.s.timeout_for_scraping * 1.5)  # 50% more
                check = self.get_data_from_url(self._urls[0])

            if check != GetDataResult.OK:
                return False

            result_count = self.gather_all_assets_urls()  # return -1 if interrupted or error
            if result_count == -1:
                return False

            url_count = len(self._urls)

            # allow the main windows to update the progress window and unfreeze its buttons while threads are running
            if gui_g.WindowsRef.uevm_gui is not None:
                gui_g.WindowsRef.uevm_gui.progress_window = self.progress_window

            self.progress_window.reset(new_value=0, new_text='Scraping data from URLs and saving to json files', new_max_value=url_count)
            # fake_root = FakeUEVMGuiClass()
            # self.progress_window.close_window()
            # pw = ProgressWindow(parent=fake_root, title='Scraping in progress...', width=300, show_btn_stop=True, show_progress=True,
            #                     quit_on_close=False)
            # pw.set_activation(False)
            self.has_been_cancelled = False
            if self.max_threads > 0 and url_count > 0:
                self._threads_count = min(self.max_threads, url_count)
                # threading processing COULD be stopped by the progress window
                self.progress_window.show_btn_stop()
                self._thread_executor = concurrent.futures.ThreadPoolExecutor(max_workers=self._threads_count, thread_name_prefix='Asset_Scaper')
                tasks = [
                    ScrapTask(caller=self, log_func=self._log_for_task, task_name=f'ScrapTask #{i}', url=url, owned_assets_only=False)
                    for i, url in enumerate(self._urls)
                ]
                with concurrent.futures.ThreadPoolExecutor():
                    self.progress_window.reset(new_value=0, new_text='Scraping data from URLs', new_max_value=url_count)
                    for task, future in [(_task, self._thread_executor.submit(_task)) for _task in tasks]:
                        if not self.progress_window.update_and_continue(increment=1, text=f'Scraping {gui_fn.shorten_text(task.url, limit=60)}'):
                            self.progress_window.stop_execution()
                            self._stop_executor()
                            self.has_been_cancelled = True
                            break
                        try:
                            future.result(timeout=gui_g.s.timeout_for_scraping)
                        except concurrent.futures.TimeoutError:
                            message = f'A Timeout error occured with task {task.name} and url {task.url}'
                            self._log(message, 'warning')
                            if self.core.scrap_asset_logger:
                                self.core.scrap_asset_logger.warning(message)
                            task.interrupt(message='Timeout error')
                        except concurrent.futures.CancelledError:
                            message = f'Task {task.name} and url {task.url} has been cancelled'
                            self._log(message, 'warning')
                            if self.core.scrap_asset_logger:
                                self.core.scrap_asset_logger.warning(message)
            else:
                for url in self._urls:
                    self.get_data_from_url(
                        url
                    )  # Note: If a captcha is present, this call will be made as a not connected user, so we can't get the "owned" flag value anymore
            if self.save_parsed_to_files:
                message = f'It took {(time.time() - start_time):.3f} seconds to download {len(self._urls)} urls and store the data in {self._files_count} files'
            else:
                message = f'It took {(time.time() - start_time):.3f} seconds to download {len(self._urls)} urls'
            self._log(message)
            # format the list to be 1 long list rather than multiple lists nested in a list - [['1'], ['2'], ...] -> ['1','2', ...]
            self._scraped_data = list(chain.from_iterable(self._scraped_data))

            # debug an instance of asset (here the last one). MUST BE RUN OUTSIDE THE LOOP ON ALL ASSETS
            if (self.core.verbose_mode or gui_g.s.debug_mode) and self._scraped_data:
                debug_parsed_data(self._scraped_data[-1], DataSourceType.DATABASE)

        if self.use_database:
            tags_count = self.asset_db_handler.get_rows_count('tags')
            rating_count = self.asset_db_handler.get_rows_count('ratings')
            self._log(f'{tags_count - tags_count_saved} tags and {rating_count - rating_count_saved} ratings have been added to the database.')

        if self.has_been_cancelled or not self.progress_window.continue_execution:
            self._log('PROCESS CANCELLED BY USER', 'warning')
            return False
        # Note: this data have the same structure as the table last_run inside the method UEAsset.create_tables()
        content = {
            'date': str(datetime.now()),
            'mode': 'save_owned' if owned_assets_only else 'save',
            'files_count': self._files_count,
            'items_count': len(self._scraped_data),
            'scraped_ids': self._scraped_ids if self.store_ids else ''
        }
        # self.progress_window.reset(new_value=0, new_text='Saving assets into files', new_max_value=len(self._scraped_data))
        # self._files_count = 0
        # for asset_data in self._scraped_data:
        #     # store the data in file AFTER parsing it
        #     filename, _ = self.core.uevmlfs.get_filename_from_asset_data(asset_data, use_sql_fields=True)
        #     self.save_to_file(filename=filename, data=asset_data, is_owned=owned_assets_only)
        #     self._files_count += 1
        #     if not self.progress_window.update_and_continue(increment=1, text=f'Saving asset to {filename}):
        #         return False

        if save_last_run_file:
            folder = gui_g.s.owned_assets_data_folder if owned_assets_only else gui_g.s.assets_data_folder
            filename = path_join(folder, self._last_run_filename)
            with open(filename, 'w', encoding='utf-8') as file:
                json.dump(content, file)

        start_time = time.time()
        if self.use_database:
            self.progress_window.reset(new_value=0, new_text='Saving into database. It could take some time...', new_max_value=None)
            is_ok = self._save_final_in_db(last_run_content=content)
        else:
            self.progress_window.reset(new_value=0, new_text='Saving into file. It could take some time...', new_max_value=None)
            is_ok = self._save_final_in_file(self.data_source_filename, save_to_format)
        message = f'It took {(time.time() - start_time):.3f} seconds to save the data in {self.data_source_filename}'
        self._log(message)
        return is_ok

    def pop_last_scraped_data(self) -> []:
        """
        Pop the last scraped data from the scraped_data property.
        :return: last scraped data.
        """
        result = []
        if len(self._scraped_data) > 0:
            result = self._scraped_data.pop()
        return result

    def clear_ignored_asset_names(self) -> None:
        """
        Clear the list of ignored asset names.
        """
        self._ignored_asset_names = []


if __name__ == '__main__':
    # the following code is just for class testing purposes
    st = UEAS_Settings()
    scraper = UEAssetScraper(
        datasource_filename=st.datasource_filename,
        use_database=True,
        start=st.start_row,
        stop=st.stop_row,
        assets_per_page=st.ue_asset_per_page,
        max_threads=st.threads,
        load_from_files=st.load_data_from_files,
        save_parsed_to_files=not st.load_data_from_files,
        store_ids=False,
        clean_database=st.clean_db
    )
    scraper.save()
