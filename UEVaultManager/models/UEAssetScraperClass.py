# coding=utf-8
"""
Implementation for:
- UEAssetScraper: a class that handles scraping data from the Unreal Engine Marketplace.
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

import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.api.egs import GrabResult, is_asset_obsolete
from UEVaultManager.core import AppCore, default_datetime_format
from UEVaultManager.lfs.utils import path_join
from UEVaultManager.models.csv_sql_fields import convert_data_to_csv, csv_sql_fields, debug_parsed_data, get_csv_field_name_list, is_on_state, \
    is_preserved
from UEVaultManager.models.types import CSVFieldState, DateFormat
from UEVaultManager.models.UEAssetClass import UEAsset
from UEVaultManager.models.UEAssetDbHandlerClass import UEAssetDbHandler
from UEVaultManager.tkgui.modules.cls.FakeProgressWindowClass import FakeProgressWindow
from UEVaultManager.tkgui.modules.functions import box_message, box_yesno, check_and_convert_list_to_str, update_loggers_level
from UEVaultManager.tkgui.modules.types import DataSourceType
from UEVaultManager.utils.cli import str_is_bool, str_to_bool


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


class UEAssetScraper:
    """
    A class that handles scraping data from the Unreal Engine Marketplace.
    It saves the data in json files and/or in a sqlite database.
    :param datasource_filename: the name of the database or file to save the data to.
    :param use_database: a boolean indicating whether to use a database for reading missing data (ex tags names) and save data in a sqlite database. Defaults to True.
    :param start: an int representing the starting index for the data to retrieve. Defaults to 0.
    :param stop: an int representing the ending index for the data to retrieve. Defaults to 0.
    :param assets_per_page: an int representing the number of items to retrieve per request. Defaults to 100.
    :param sort_by: a string representing the field to sort by. Defaults to 'effectiveDate'.
    :param sort_order: a string representing the sort order. Defaults to 'ASC'.
    :param max_threads: an int representing the maximum number of threads to use. Defaults to 8. Set to 0 to disable multithreading.
    :param save_to_files: a boolean indicating whether to store the data in csv files. Defaults to True. Could create lots of files (1 file per asset).
    :param load_from_files: a boolean indicating whether to load the data from files instead of scraping it. Defaults to False. If set to True, save_to_files will be set to False and use_database will be set to True.
    :param store_ids: a boolean indicating whether to store and save the IDs of the assets. Defaults to False. Could be memory consuming.
    :param clean_database: a boolean indicating whether to clean the database before saving the data. Defaults to False.
    :param debug_mode: True to enable debug mode. Defaults to False.
    :param offline_mode: True to enable offline mode. Defaults to False.
    :param progress_window: a ProgressWindow object. Defaults to None. If None, a new ProgressWindow object will be created.
    :param core: an AppCore object. Defaults to None. If None, a new AppCore object will be created.
    :param timeout: timeout for the request. Could be a float or a tuple of float (connect timeout, read timeout).
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
        save_to_files: bool = True,
        load_from_files: bool = False,
        store_ids: bool = False,
        clean_database: bool = False,
        debug_mode=False,
        offline_mode=False,
        progress_window=None,  # don't use a typed annotation here to avoid import
        core: AppCore = None,
        timeout: float = (7, 7),
    ) -> None:
        self._last_run_filename: str = 'last_run.json'
        self._urls_list_filename: str = 'urls_list.txt'
        self._threads_count: int = 0
        self._files_count: int = 0
        self._thread_executor = None
        self._scraped_data = []  # the scraper scraped_data. Increased on each call to get_data_from_url(). Could be huge !!

        self._datasource_filename: str = datasource_filename
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
        self.load_from_files: bool = load_from_files
        self.save_to_files: bool = save_to_files
        self.store_ids = store_ids
        self.clean_database: bool = clean_database
        self.debug_mode = debug_mode
        self.offline_mode = offline_mode
        self.asset_db_handler = None
        if not datasource_filename:
            message = 'Database mode is used but no database filename has been provided' if use_database else 'File mode is used but no filename has been provided'
            self._log(message, 'error')
            return
        self.core = AppCore(timeout=timeout) if core is None else core

        if progress_window is None:
            progress_window = FakeProgressWindow()
        self.progress_window = progress_window

        if self.load_from_files:
            self.save_to_files = False  # no need to save if the source are the files , they won't be changes
            # self.use_database = True

        if (assets_per_page > 100) or (assets_per_page < 1):
            self.assets_per_page = 100
            self._log(f'assets_per_page must be between 1 and 100. Set to 100', 'error')

        message = f'UEAssetScraper initialized with max_threads= {max_threads}, start= {start}, stop= {stop}, assets_per_page= {assets_per_page}, sort_by= {sort_by}, sort_order= {sort_order}'
        message += f'\nData will be load from files in {gui_g.s.assets_data_folder}' if self.load_from_files else ''
        message += f'\nAsset Data will be saved in files in {gui_g.s.assets_data_folder}' if self.save_to_files else ''
        message += f'\nOwned Asset Data will be saved in files in {gui_g.s.owned_assets_data_folder}' if self.save_to_files else ''
        message += f'\nAsset Ids will be saved in {self._last_run_filename} or in database' if self.store_ids else ''
        if self.use_database:
            self.asset_db_handler = UEAssetDbHandler(self._datasource_filename)
            message += f'\nData will be saved in DATABASE in {self._datasource_filename}'
        else:
            message += f'\nData will be saved in FILE in {self._datasource_filename}'
        self._log(message)

    @property
    def data_source_filename(self):
        """ Get the name of the database to save the data to."""
        return self._datasource_filename

    @data_source_filename.setter
    def data_source_filename(self, value: str):
        """ Set the name of the data source to save the data to."""
        if not value or self._datasource_filename == value:
            return
        self._datasource_filename = value
        if self.use_database:
            if self.asset_db_handler:
                self.asset_db_handler.init_connection()
            else:
                self.asset_db_handler = UEAssetDbHandler(self._datasource_filename)

    @staticmethod
    def read_json_file(app_name: str, owned_assets_only=False) -> (dict, str):
        """
        Load JSON data from a file.
        :param app_name: the name of the asset to load the data from.
        :param owned_assets_only: whether only the owned assets are scraped.
        :return: a dictionary containing the loaded data.
        """
        folder = gui_g.s.owned_assets_data_folder if owned_assets_only else gui_g.s.assets_data_folder
        filename = app_name + '.json'
        json_data = {}
        message = ''
        with open(path_join(folder, filename), 'r', encoding='utf-8') as file:
            try:
                json_data = json.load(file)
            except json.decoder.JSONDecodeError as error:
                message = f'The following error occured when loading data from {filename}:{error!r}'
            # we need to add the appName  (i.e. assetId) to the data because it can't be found INSIDE the json data
            # it needed by the json_data_mapping() method
            json_data['appName'] = app_name
        return json_data, message

    @staticmethod
    def json_data_mapping(data_from_egs_format: dict) -> dict:
        """
        Convert json data from EGS format (NEW) to UEVM format (OLD, i.e. legendary
        :param data_from_egs_format: json data from EGS format (NEW)
        :return: json data in UEVM format (OLD)
        """
        app_name = data_from_egs_format['appName']
        category = data_from_egs_format['categories'][0]['path']

        if category == 'assets/codeplugins':
            category = 'plugins/engine'
        category_1 = category.split('/')[0]
        categorie = [{'path': category}, {'path': category_1}]
        data_to_uevm_format = {
            'app_name': app_name,
            'app_title': data_from_egs_format['title'],
            'asset_infos': {
                'Windows': {
                    'app_name': app_name,
                    # 'asset_id': data_from_egs_format['id'], # no common value between EGS and UEVM
                    # 'build_version': app_name,  # no common value between EGS and UEVM
                    'catalog_item_id': data_from_egs_format['catalogItemId'],
                    # 'label_name': 'Live-Windows',
                    'metadata': {},
                    'namespace': data_from_egs_format['namespace']
                }
            },
            'base_urls': [],
            'metadata': {
                'categories': categorie,
                # 'creationDate': data_from_egs_format['effectiveDate'], # use first release instead
                'description': data_from_egs_format['description'],
                'developer': data_from_egs_format['seller']['name'],
                'developerId': data_from_egs_format['seller']['id'],
                # 'endOfSupport': False,
                'entitlementName': data_from_egs_format['catalogItemId'],
                # 'entitlementType' : 'EXECUTABLE',
                # 'eulaIds': [],
                'id': data_from_egs_format['catalogItemId'],
                # 'itemType': 'DURABLE',
                'keyImages': data_from_egs_format['keyImages'],
                # 'lastModifiedDate': data_from_egs_format['effectiveDate'], # use last release instead
                'longDescription': data_from_egs_format['longDescription'],
                'namespace': data_from_egs_format['namespace'],
                'releaseInfo': data_from_egs_format['releaseInfo'],
                'status': data_from_egs_format['status'],
                'technicalDetails': data_from_egs_format['technicalDetails'],
                'title': data_from_egs_format['title'],
                # 'unsearchable': False
            }
        }
        return data_to_uevm_format

    def _log(self, message, level: str = 'info'):
        if level == 'debug':
            """ a simple wrapper to use when cli is not initialized"""
            if gui_g.UEVM_cli_ref is None and self.debug_mode:
                print(f'DEBUG {message}')
            else:
                if gui_g.s.testing_switch >= 1:
                    # force printing debug messages when testing
                    self.logger.info(message)
                else:
                    self.logger.debug(message)
        elif level == 'info':
            """ a simple wrapper to use when cli is not initialized"""
            if gui_g.UEVM_cli_ref is None:
                print(f'INFO {message}')
            else:
                self.logger.info(message)
        elif level == 'warning':
            """ a simple wrapper to use when cli is not initialized"""
            if gui_g.UEVM_cli_ref is None:
                print(f'WARNING {message}')
            else:
                self.logger.warning(message)
        elif level == 'error':
            """ a simple wrapper to use when cli is not initialized"""
            if gui_g.UEVM_cli_ref is None:
                print(f'ERROR {message}')
            else:
                self.logger.error(message)

    def _parse_data(self, json_data: dict = None) -> list:
        """
        Parse on or more asset data from the response of an url query.
        :param json_data: a dictionary containing the data to parse.
        :return: a list containing the parsed data.
        """

        all_assets = []
        if json_data is None:
            return all_assets
        try:
            # get the list of assets after a "scraping" of the json data using URL
            assets_data_list = json_data['data']['elements']
        except KeyError:
            # this exception is raised when data come from a json file. Not an issue
            # create a list of one asset when data come from a json file
            assets_data_list = [json_data.copy()]

        asset_db_handler = self.asset_db_handler
        use_database = self.use_database and asset_db_handler
        for asset_data in assets_data_list:
            uid = asset_data.get('id', '')
            if not uid:
                # this should never occur
                self._log(f'No id found for current asset. Passing to next asset', level='warning')
            else:
                asset_existing_data = {}  # when getting data the "OLD" method, no existing data , because the CSV will be compared after
                if use_database:
                    existing_data = asset_db_handler.get_assets_data(asset_db_handler.preserved_data_fields, uid)
                    asset_existing_data = existing_data.get(uid, None)
                categories = asset_data.get('categories', None)
                release_info = asset_data.get('releaseInfo', {})
                # convert release_info to a json string
                asset_data['release_info'] = json.dumps(release_info) if release_info else gui_g.no_text_data
                latest_release = release_info[-1] if release_info else {}
                first_release = release_info[0] if release_info else {}
                app_name = asset_data.get('app_name', '')
                origin = 'Marketplace'  # by default when scraped from marketplace
                date_now = datetime.now().strftime(default_datetime_format)
                grab_result = GrabResult.NO_ERROR.name

                # make some calculation with the "raw" data
                # ------------
                # simple fields
                seller = asset_data.get('seller', None)
                author = seller.get('name', '') if seller else asset_data.get('developer', '')
                asset_data['author'] = author
                asset_data['page_title'] = asset_data['title']
                asset_data['origin'] = origin
                asset_data['update_date'] = date_now
                asset_data['downloaded_size'] = self.core.uevmlfs.get_asset_size(
                    app_name, gui_g.no_text_data
                )  # '' because we want the cell to be empty if no size

                # thumbnail_url
                asset_data['thumbnail_url'] = asset_data.get('thumbnail', '')
                if not asset_data['thumbnail_url']:
                    try:
                        key_images = asset_data['keyImages']
                        # search for the image with the key 'Thumbnail'
                        for image in key_images:
                            if image['type'] == 'Thumbnail':
                                asset_data['thumbnail_url'] = image['url']
                                break
                    except IndexError:
                        self._log(f'asset {app_name} has no image', level='debug')
                if categories:
                    asset_data['category'] = categories[0].get('name', '') or categories[0].get('path', '') or ''

                # asset_id
                try:
                    asset_id = latest_release['appId']
                except (KeyError, AttributeError, IndexError):
                    grab_result = GrabResult.NO_APPID.name
                    asset_id = uid  # that's not the REAL asset_id, we use the uid instead
                asset_data['asset_id'] = asset_id

                # asset slug and asset url
                asset_slug = asset_data.get('urlSlug', gui_g.no_text_data) or asset_data.get('asset_slug', gui_g.no_text_data)
                if asset_slug == gui_g.no_text_data:
                    asset_url = gui_g.no_text_data
                    self._log(f'No asset_slug found for asset id={uid}. Its asset_url will be empty', level='warning')
                else:
                    asset_url = self.core.egs.get_marketplace_product_url(asset_slug)
                asset_data['asset_slug'] = asset_slug
                asset_data['asset_url'] = asset_url

                # prices and discount
                price = self.core.egs.extract_price(asset_data.get('price', gui_g.no_float_data))
                discount_price = self.core.egs.extract_price(asset_data.get('discount_price', gui_g.no_float_data))
                discount_percentage = int(asset_data.get('discount_percentage', gui_g.no_int_data))
                if asset_data.get('priceValue', 0) > 0:
                    # tbh the logic here is flawed as hell lol. discount should only be set if there's a discount Epic wtf
                    # price = asset_data['priceValue'] if asset_data['priceValue'] == asset_data['discountPriceValue'] else asset_data['discountPriceValue'] # here we keep the CURRENT price
                    price = float(asset_data['priceValue'])  # here we keep the NORMAL price
                    discount_price = float(asset_data['discountPriceValue'])
                    # price are in cents
                    price /= 100
                    discount_price /= 100
                    discount_percentage = 100 - int(asset_data['discountPercentage'])
                    # discount_percentage = 0.0 if (discount_price == 0.0 or price == 0.0 or discount_price == price) else int((price-discount_price) / price * 100.0)
                if discount_price == gui_g.no_int_data:
                    discount_price = price
                asset_data['price'] = price
                asset_data['discount_price'] = discount_price
                asset_data['discount_percentage'] = discount_percentage

                # old price
                old_price = asset_existing_data.get('price', gui_g.no_float_data) if asset_existing_data else gui_g.no_float_data
                older_price = asset_existing_data.get('old_price', gui_g.no_float_data) if asset_existing_data else gui_g.no_float_data
                asset_data['old_price'] = old_price if old_price else older_price

                # rating
                average_rating = asset_data.get('review', gui_g.no_int_data)
                rating_total = gui_g.no_int_data
                if asset_data.get('rating', ''):
                    try:
                        average_rating = asset_data['rating']['averageRating']
                        rating_total = asset_data['rating']['total']
                    except KeyError:
                        self._log('_debug', f'No rating for {asset_data["title"]}')
                        # check if self has asset_db_handler
                        if use_database:
                            average_rating, rating_total = asset_db_handler.get_rating_by_id(uid)
                asset_data['review'] = average_rating
                asset_data['review_count'] = rating_total

                # custom attributes
                asset_data['custom_attributes'] = ''
                try:
                    custom_attributes = asset_data.get('customAttributes', '')
                    if isinstance(custom_attributes, dict):
                        # check for "has an external link"
                        custom_attributes = 'external_link:' + custom_attributes['BuyLink']['value'] if custom_attributes.get('BuyLink', '') else ''
                        asset_data['custom_attributes'] = custom_attributes
                except (KeyError, AttributeError):
                    asset_data['custom_attributes'] = gui_g.no_text_data

                # supported_versions
                supported_versions = asset_data.get('supported_versions', gui_g.no_text_data)  # data can come from the extra_data
                try:
                    tmp_list = [check_and_convert_list_to_str(item.get('compatibleApps')) for item in release_info]
                    supported_versions = check_and_convert_list_to_str(tmp_list) or supported_versions
                except TypeError as error:
                    self._log(f'Error getting compatibleApps for asset with uid={uid}: {error!r}', level='debug')
                asset_data['supported_versions'] = supported_versions

                # dates
                # asset_data['creation_date'] = asset_data['creationDate']  # does not exist in when scrapping from marketplace
                # we use the first realase date instead as it exist in both cases
                tmp_date = first_release.get('dateAdded', gui_g.no_text_data) if first_release else gui_g.no_text_data
                tmp_date = gui_fn.convert_to_datetime(tmp_date, formats_to_use=[DateFormat.epic, DateFormat.csv])
                tmp_date = gui_fn.convert_to_str_datetime(tmp_date, DateFormat.csv)
                asset_data['creation_date'] = tmp_date
                asset_data['date_added'] = asset_existing_data.get('date_added', date_now) if asset_existing_data else date_now

                # obsolete
                try:
                    engine_version_for_obsolete_assets = (
                        gui_g.UEVM_cli_ref.core.engine_version_for_obsolete_assets or gui_g.s.engine_version_for_obsolete_assets
                    )
                except (Exception, ):
                    engine_version_for_obsolete_assets = None
                asset_data['obsolete'] = is_asset_obsolete(supported_versions, engine_version_for_obsolete_assets)

                # grab_result and old_grab_result
                # old_grab_result = asset_existing_data.get(
                #     'grab_result', GrabResult.NO_ERROR.name
                # ) if asset_existing_data else GrabResult.NO_ERROR.name
                # if owned_assets_only and old_grab_result == GrabResult.NO_ERROR.name:
                #     # if no error occurs and if we only parse owned assets, the parsed data ARE less complete than the "normal" one
                #     # so, we set the grab result to PARTIAL
                #     grab_result = GrabResult.PARTIAL.name
                asset_data['grab_result'] = grab_result

                # we use copy data for user_fields to preserve user data
                if asset_existing_data and use_database:
                    for field in asset_db_handler.user_fields:
                        old_value = asset_existing_data.get(field, None)
                        if old_value:
                            asset_data[field] = old_value

                # installed_folders and tags
                installed_folders_str = asset_data.get('installed_folders', '')
                asset_installed = self.core.uevmlfs.get_installed_asset(asset_id)  # from current existing install
                if asset_installed:
                    asset_installed_folders = asset_installed.installed_folders
                    installed_folders_str = gui_fn.merge_lists_or_strings(installed_folders_str, asset_installed_folders)
                tags = asset_data.get('tags', [])
                if use_database:
                    # get tag name from tag id and convert the list into a comma separated string
                    tags_str = asset_db_handler.convert_tag_list_to_string(tags)
                    # asset_data['installed_folders'] = installed_folders_str
                else:
                    # just convert the list of ids into a comma separated string
                    tags_str = check_and_convert_list_to_str(tags)
                    # we need to convert list to string if we are in FILE Mode because it's done when saving the asset in database in the "SQLITE" mode
                    installed_folders_str = check_and_convert_list_to_str(asset_data.get('installed_folders', []))
                asset_data['installed_folders'] = installed_folders_str
                asset_data['tags'] = tags_str

                # we use an UEAsset object to store the data and create a valid dict from it
                ue_asset = UEAsset()
                ue_asset.init_from_dict(asset_data)

                # -----
                # end similar part as in UEAssetScrappedClass._parse_data
                # -----

                all_assets.append(ue_asset.get_data())
                message = f'Asset with uid={uid} added to content: owned={ue_asset.get("owned")} creation_date={ue_asset.get("creation_date")}'
                self._log(message, 'debug')  # use debug here instead of info to avoid spamming the log file
                if self.store_ids:
                    try:
                        self._scraped_ids.append(uid)
                    except (AttributeError, TypeError) as error:
                        self._log(f'Error when adding uid to self.scraped_ids: {error!r}', 'debug')
            # end else if uid:
        # end for asset_data in json_data['data']['elements']:
        return all_assets

    def _get_filename_from_asset_data(self, asset_data) -> str:
        """
        Return the filename to use to save the asset data.
        :param asset_data: the asset data.
        :return: the filename to use to save the asset data.
        """
        try:
            app_id = asset_data['releaseInfo'][-1]['appId']  # latest release
            filename = f'{app_id}.json'
        except (KeyError, IndexError) as error:
            self._log(f'Error getting appId for asset with id {asset_data["id"]}: {error!r}', 'warning')
            app_id = asset_data.get('urlSlug', None)
            if app_id is None:
                app_id = asset_data.get('catalogItemId', gui_fn.create_uid())
            filename = f'_no_appId_{app_id}.json'
        return filename

    def get_scrapped_data(self) -> list:
        """ Return the scraped data. """
        return self._scraped_data

    def _save_in_db(self, last_run_content: dict) -> bool:
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
        csv_fields_count = len(get_csv_field_name_list())
        if _assets_in_file.get(_asset_id):
            item_in_file = _assets_in_file.get(_asset_id)
            keys_check = item_in_file.keys()
            if gui_g.s.index_copy_col_name in keys_check:
                csv_fields_count += 1
            if len(keys_check) != csv_fields_count:
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
                    if value in gui_g.s.cell_is_empty_list:
                        _csv_record[index] = ''
                        continue
                    value = str(value)
                    # Get the old price in the previous file
                    if _csv_field == 'Price':
                        price_index = index
                        _price = gui_fn.convert_to_float(_csv_record[price_index])
                        old_price = gui_fn.convert_to_float(
                            item_in_file[_csv_field]
                        )  # Note: the 'old price' is the 'price' saved in the file, not the 'old_price' in the file
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
            # end ELSE if len(item_in_file.keys()) != csv_fields_count
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
        :return:
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
                )  # Note: the 'old price' is the 'price' saved in the file, not the 'old_price' in the file
            except Exception as _error:
                self._log(f'Old price values can not be converted for asset {_asset_id}\nError:{_error!r}', level='warning')
            _json_record['Old price'] = old_price
        return _json_record

    # end def update_and_merge_json_record_data

    def _save_in_file(self, save_to_format: str = 'csv') -> bool:
        """
        Save the scraped data into a file.
        :param save_to_format: the format of the file to save the data. Sould be 'csv','tcsv' or 'json'. Used only when use_database is False
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
                with open(self._datasource_filename, 'r', encoding='utf-8') as output:
                    csv_file_content = csv.DictReader(output)
                    # get the data (it's a dict)
                    for csv_record in csv_file_content:
                        # noinspection PyTypeChecker
                        asset_id = csv_record['Asset_id']
                        assets_in_file[asset_id] = csv_record
                    output.close()
            except (FileExistsError, OSError, UnicodeDecodeError, StopIteration):
                self._log(f'Could not read CSV record from the file {self._datasource_filename}', level='warning')
            # reopen file for writing
            output = open(self._datasource_filename, 'w', encoding='utf-8')
            writer = csv.writer(output, dialect='excel-tab' if save_to_format == 'tcsv' else 'excel', lineterminator='\n')

            # get final the csv fields name list by
            # - using the columns_infos from the settings
            # - ordering the columns by their position
            # - adding the csv_field_name_list that are not in columns_infos
            csv_field_name_list = get_csv_field_name_list()
            columns_infos = gui_g.s.get_column_infos(DataSourceType.FILE)
            sorted_cols_by_pos = dict(sorted(columns_infos.items(), key=lambda item: item[1]['pos']))
            new_csv_field_name_list = list(sorted_cols_by_pos.keys())
            # add field in csv_field_name_list if it's not in the list
            for col_name in csv_field_name_list:
                if col_name not in new_csv_field_name_list:
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
                    ignore_in_csv = is_on_state(csv_field_name=key, states=[CSVFieldState.ASSET_ONLY, CSVFieldState.SQL_ONLY], default=False)
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
                with open(self._datasource_filename, 'r', encoding='utf-8') as output:
                    assets_in_file = json.load(output)
            except (FileExistsError, OSError, UnicodeDecodeError, StopIteration, json.decoder.JSONDecodeError):
                self._log(f'Could not read Json record from the file {self._datasource_filename}', level='warning')
            # reopen file for writing
            output = open(self._datasource_filename, 'w', encoding='utf-8')
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
                    message = f'Could not write Json record for {asset_id} into {self._datasource_filename}\nError:{error!r}'
                    self._log(message, level='error')
            json.dump(json_content, output, indent=2)

        # close the opened file
        if output is not None:
            output.close()
        self._log(f'\n======\n{asset_count} assets have been saved (without duplicates due to different UE versions)\nOperation Finished\n======\n')
        return True

    def gather_all_assets_urls(self, egs_available_assets_count: int = -1, empty_list_before=False, save_result=True, owned_assets_only=False) -> int:
        """
        Gather all the URLs (with pagination) to be parsed and stores them in a list for further use.
        :param egs_available_assets_count: the number of assets available on the marketplace. If not given, it will be retrieved from the EGS API.
        :param empty_list_before: whether the list of URLs is emptied before adding the new ones.
        :param save_result: whether the list of URLs is saved in the database.
        :param owned_assets_only: whether only the owned assets are scraped.
        :return: the number of assets to be scraped or -1 if the offline mode is active or if the process has been interrupted.
        """
        if self.offline_mode:
            self._log('The offline mode is active. No online data could be retreived')
            return -1
        start_time = time.time()
        if egs_available_assets_count <= 0:
            egs_available_assets_count = self.core.egs.get_available_assets_count(owned_assets_only)
        if empty_list_before:
            self._urls = []
        if self.stop <= 0:
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
            if owned_assets_only:
                url = self.core.egs.get_owned_scrap_url(start, self.assets_per_page)
            else:
                url = self.core.egs.get_scrap_url(start, self.assets_per_page, self.sort_by, self.sort_order)
            self._urls.append(url)
        self._log(f'It took {(time.time() - start_time):.3f} seconds to gather {len(self._urls)} urls')
        if save_result:
            self.save_to_file(filename=self._urls_list_filename, data=self._urls, is_json=False, is_owned=owned_assets_only)
        return assets_to_scrap

    def get_data_from_url(self, url='', owned_assets_only=False) -> None:
        """
        Grab the data from the given url and stores it in the scraped_data property.
        :param url: the url to grab the data from. If not given, uses the url property of the class.
        :param owned_assets_only: whether only the owned assets are scraped.
        """
        if not self.progress_window.continue_execution:
            return
        if not url:
            self._log('No url given to get_data_from_url()', 'error')
            return
        if self.offline_mode:
            self._log('The offline mode is active. No online data could be retreived')
            return
        thread_data = ''
        try:
            if self._threads_count > 1:
                # add a delay when multiple threads are used
                time.sleep(random.uniform(1.0, 3.0))
                thread = current_thread()
                thread_data = f' ==> By Thread name={thread.name}'
            self._log(f'--- START scraping data from {url}{thread_data}')
            json_data = self.core.egs.get_json_data_from_url(url)
            no_error = json_data.get('status', '') == 'OK'
            if not no_error:
                self._log(f'Error getting data from url {url}. Making another try....')
                json_data = self.core.egs.get_json_data_from_url(url)
                no_error = json_data.get('status', '') == 'OK'
                if not no_error:
                    self._log(f'Error getting data from url {url}: {json_data["errorCode"]}', 'error')
                    return
            try:
                # when multiple assets are returned, the data is in the 'elements' key
                count = len(json_data['data']['elements'])
                self._log(f'==> parsed url {url}: got a list of {count} assets')
            except KeyError:
                # when only one asset is returned, the data is in the 'data' key
                self._log(f'==> parsed url {url} for one asset')
                json_data['data']['elements'] = [json_data['data']['data']]

            if json_data:
                if self.save_to_files:
                    # store the result file in the raw format
                    # noinspection PyBroadException
                    try:
                        url_vars = gui_fn.extract_variables_from_url(url)
                        start = int(url_vars['start'])
                        count = int(url_vars['count'])
                        suffix = f'{start}-{start + count - 1}'
                    except Exception:
                        suffix = datetime.now().strftime('%y-%m-%d_%H-%M-%S')
                    filename = f'assets_{suffix}.json'
                    self.save_to_file(filename=filename, data=json_data, is_global=True)

                    # store the individial asset in file
                    saved_text = self.progress_window.get_text()
                    count = len(json_data['data']['elements'])
                    for index, asset_data in enumerate(json_data['data']['elements']):
                        self.progress_window.set_text(f'Saving data to json files ({index}/{count})')
                        filename = self._get_filename_from_asset_data(asset_data)
                        self.save_to_file(filename=filename, data=asset_data, is_owned=owned_assets_only)
                        self._files_count += 1
                    self.progress_window.set_text(saved_text)
                content = self._parse_data(json_data)
                self._scraped_data.append(content)
        except Exception as error:
            self._log(f'Error getting data from url {url}: {error!r}', 'warning')

    def _execute(self, owned_assets_only=False) -> bool:
        """
        Execute the scrapper. Load from files or downloads the items from the URLs and stores them in the scraped_data property.
        The execution is done in parallel using threads.
        :param owned_assets_only: whether only the owned assets are scraped
        :return: True if the execution is successful, False otherwise.

        Notes:
            If self.urls is None or empty, gather_urls() will be called first.
        """

        def stop_executor(tasks) -> None:
            """
            Cancel all outstanding tasks and shut down the executor.
            :param tasks: tasks to cancel.
            """
            for _, task in tasks.items():
                task.cancel()
            self._thread_executor.shutdown(wait=False)

        try:
            egs_available_assets_count = self.core.egs.get_available_assets_count(owned_assets_only)
        except (Exception, ):
            self._log('Can not get the asset count from marketplace.\nOffline mode is activated and data will be got from files.', 'warning')
            egs_available_assets_count = -1
            self.offline_mode = True
            self.load_from_files = True

        asset_loaded = 0
        if self.load_from_files:
            asset_loaded = self.load_from_json_files()
            if asset_loaded == -1:
                # stop has been pressed
                return False

        if asset_loaded <= 0:
            # no data, ie no files loaded, so we have to save them
            self.load_from_files = False
            self.save_to_files = True
            start_time = time.time()
            result_count = 0
            if not self._urls:
                result_count = self.gather_all_assets_urls(owned_assets_only=owned_assets_only)  # return -1 if interrupted or error
            if result_count == -1:
                return False
            self.progress_window.reset(new_value=0, new_text='Scraping data from URLs and saving to json files', new_max_value=len(self._urls))
            url_count = len(self._urls)
            if self.max_threads > 0 and url_count > 0:
                self._threads_count = min(self.max_threads, url_count)
                # threading processing COULD be stopped by the progress window
                self.progress_window.show_btn_stop()
                self._thread_executor = concurrent.futures.ThreadPoolExecutor(max_workers=self._threads_count, thread_name_prefix='Asset_Scaper')
                futures = {}
                # for url in self.urls:
                while len(self._urls) > 0:
                    url = self._urls.pop()
                    # Submit the task and add its Future to the dictionary
                    future = self._thread_executor.submit(lambda url_param: self.get_data_from_url(url_param, owned_assets_only), url)
                    futures[url] = future

                with concurrent.futures.ThreadPoolExecutor():
                    for future in concurrent.futures.as_completed(futures.values()):
                        if gui_g.s.testing_switch == 1 and len(self._scraped_data) >= gui_g.s.testing_assets_limit:
                            # stop the scraping after 3000 assets when testing
                            stop_executor(futures)
                            break
                        try:
                            _ = future.result()
                            # print("Result: ", result)
                        except Exception as error:
                            self._log(f'The following error occurs in threading: {error!r}', 'warning')
                        if not self.progress_window.update_and_continue(increment=1):
                            # self._log(f'User stop has been pressed. Stopping running threads....')   # will flood console
                            stop_executor(futures)
                self._thread_executor.shutdown(wait=False)
            else:
                for url in self._urls:
                    self.get_data_from_url(url, owned_assets_only)
            if self.save_to_files:
                message = f'It took {(time.time() - start_time):.3f} seconds to download {len(self._urls)} urls and store the data in {self._files_count} files'
            else:
                message = f'It took {(time.time() - start_time):.3f} seconds to download {len(self._urls)} urls'
            self._log(message)
            # format the list to be 1 long list rather than multiple lists nested in a list - [['1'], ['2'], ...] -> ['1','2', ...]
            self._scraped_data = list(chain.from_iterable(self._scraped_data))
            # debug an instance of asset (here the last one). MUST BE RUN OUTSIDE THE LOOP ON ALL ASSETS
            if (self.core.verbose_mode or gui_g.s.debug_mode) and self._scraped_data:
                debug_parsed_data(self._scraped_data[-1], DataSourceType.SQLITE)
        elif asset_loaded <= egs_available_assets_count:
            # some asset are missing in json files
            message = f'{asset_loaded} assets have been loaded from json files but {egs_available_assets_count} are available on the marketplace.\nYou should do a rebuild with the force_refresh option enabled to get the new ones.'
            if self.progress_window.is_fake:
                # use a box message only if the progress window is fake, ie whe are not in GUI mode
                box_message(message)
            else:
                self.progress_window.reset(new_value=0, new_text=message, new_max_value=None)
        return True

    def save_to_file(self, prefix='assets', filename=None, data=None, is_json=True, is_owned=False, is_global=False) -> bool:
        """
        Save JSON data to a file.
        :param data: a dictionary containing the data to save. Defaults to None. If None, the data will be used.
        :param prefix: a string representing the prefix to use for the file name. Defaults to 'assets'.
        :param filename: a string representing the file name to use. Defaults to None. If None, a file name will be generated using the prefix and the start and count properties.
        :param is_json: a boolean indicating whether the data is JSON or not. Defaults to True.
        :param is_owned: a boolean indicating whether the data is owned assets or not. Defaults to False.
        :param is_global: a boolean indicating whether if the data to save id the "global" result, as produced by the url scraping. Defaults to False.
        :return: a boolean indicating whether the file was saved successfully.
        """
        if data is None:
            data = self._scraped_data

        if not data:
            self._log('No data to save', 'warning')
            return False

        folder = gui_g.s.owned_assets_data_folder if is_owned else gui_g.s.assets_data_folder
        folder = gui_g.s.assets_global_folder if is_global else folder

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
        :return: the number of files loaded or -1 if the process has been interrupted.
        """
        start_time = time.time()
        self._files_count = 0
        self._scraped_ids = []
        self._scraped_data = []
        folder = gui_g.s.owned_assets_data_folder if owned_assets_only else gui_g.s.assets_data_folder
        old_text = self.progress_window.get_text()
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
                        json_data = json.load(file)
                    except json.decoder.JSONDecodeError as error:
                        self._log('_warning', f'The following error occured when loading data from {filename}:{error!r}')
                        continue
                    assets_data = self._parse_data(json_data)  # self._parse_data returns a list of assets
                    for asset_data in assets_data:
                        self._scraped_data.append(asset_data)
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
            debug_parsed_data(self._scraped_data[-1], DataSourceType.SQLITE)

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

        self.progress_window.reset(new_value=0, new_text=old_text, new_max_value=0)
        # self._save_in_db(last_run_content=content) # duplicate with a caller
        return self._files_count

    def save(self, owned_assets_only=False, save_last_run_file=True, save_to_format: str = 'csv') -> bool:
        """
        Save all JSON data retrieved from the Unreal Engine Marketplace API to paginated files.
        :param owned_assets_only: whether to only the owned assets are scraped.
        :param save_last_run_file: whether the last_run file is saved.
        :param save_to_format: the format of the file to save the data. Sould be 'csv','tcsv' or 'json'. Used only when use_database is False
        :return: True if OK, False if not
        """
        if owned_assets_only:
            self._log('Only Owned Assets will be scraped')

        is_ok = self._execute(owned_assets_only=owned_assets_only)  # will fill the self._scraped_data property
        if not is_ok or not self.progress_window.continue_execution:
            return False
        # Note: this data have the same structure as the table last_run inside the method UEAsset.create_tables()
        content = {
            'date': str(datetime.now()),
            'mode': 'save_owned' if owned_assets_only else 'save',
            'files_count': 0,
            'items_count': len(self._scraped_data),
            'scraped_ids': ''
        }
        start_time = time.time()
        if self.save_to_files:
            self.progress_window.reset(new_value=0, new_text='Saving into files', new_max_value=len(self._scraped_data))
            # store the data in a AFTER parsing it
            self._files_count = 0
            for asset_data in self._scraped_data:
                filename = self._get_filename_from_asset_data(asset_data)
                self.save_to_file(filename=filename, data=asset_data, is_owned=owned_assets_only)
                self._files_count += 1
                if not self.progress_window.update_and_continue(increment=1):
                    return False
            message = f'It took {(time.time() - start_time):.3f} seconds to save the data in {self._files_count} files'
            self._log(message)

        # save results in the last_run file
        content['files_count'] = self._files_count
        content['scraped_ids'] = self._scraped_ids if self.store_ids else ''
        if save_last_run_file:
            folder = gui_g.s.owned_assets_data_folder if owned_assets_only else gui_g.s.assets_data_folder
            filename = path_join(folder, self._last_run_filename)
            with open(filename, 'w', encoding='utf-8') as file:
                json.dump(content, file)

        if self.use_database:
            self.progress_window.reset(new_value=0, new_text='Saving into database', new_max_value=None)
            is_ok = self._save_in_db(last_run_content=content)
        else:
            self.progress_window.reset(new_value=0, new_text='Saving into file', new_max_value=None)
            is_ok = self._save_in_file(save_to_format)
        self._log('data saved')
        return is_ok

    def pop_last_scrapped_data(self) -> []:
        """
        Pop the last scraped data from the scraped_data property.
        :return: the last scraped data.
        """
        result = []
        if len(self._scraped_data) > 0:
            result = self._scraped_data.pop()
        return result


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
        save_to_files=not st.load_data_from_files,
        store_ids=False,
        clean_database=st.clean_db
    )
    scraper.save()
