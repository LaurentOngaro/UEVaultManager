# coding=utf-8
"""
Implementation for:
- UEAssetScraper: a class that handles scraping data from the Unreal Engine Marketplace.
"""
import concurrent.futures
import json
import logging
import os
import random
import time
from datetime import datetime
from itertools import chain
from threading import current_thread

import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.api.egs import GrabResult, is_asset_obsolete
from UEVaultManager.core import AppCore, default_datetime_format
from UEVaultManager.lfs.utils import path_join
from UEVaultManager.models.UEAssetClass import UEAsset
from UEVaultManager.models.UEAssetDbHandlerClass import UEAssetDbHandler
from UEVaultManager.tkgui.modules.cls.FakeProgressWindowClass import FakeProgressWindow
from UEVaultManager.tkgui.modules.functions import box_yesno, update_loggers_level
from UEVaultManager.tkgui.modules.functions_no_deps import check_and_get_folder, convert_to_datetime, convert_to_str_datetime, create_uid, \
    extract_variables_from_url


class UEAS_Settings:
    """
    Settings for the class when running as main.
    """
    # set the number of rows to retrieve per page
    # As the asset are saved individually by default, this value is only use for pagination in the files that store the url
    # it speeds up the process of requesting the asset list
    ue_asset_per_page = 100

    if gui_g.s.testing_switch == 1:
        # shorter and faster list for testing only
        # disabling threading is used for debugging (fewer exceptions are raised if threads are used)
        threads = 0  # set to 0 to disable threading
        start_row = 15000
        stop_row = 15000 + ue_asset_per_page
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
    :param start: an int representing the starting index for the data to retrieve. Defaults to 0.
    :param start: an int representing the ending index for the data to retrieve. Defaults to 0.
    :param assets_per_page: an int representing the number of items to retrieve per request. Defaults to 100.
    :param sort_by: a string representing the field to sort by. Defaults to 'effectiveDate'.
    :param sort_order: a string representing the sort order. Defaults to 'ASC'.
    :param timeout: a float representing the timeout for the requests. Defaults to 10.0.
    :param max_threads: an int representing the maximum number of threads to use. Defaults to 8. Set to 0 to disable multithreading.
    :param load_from_files: a boolean indicating whether to load the data from files instead of scraping it. Defaults to False. If set to True, store_in_files will be set to False and store_in_db will be set to True.
    :param store_in_files: a boolean indicating whether to store the data in csv files. Defaults to True. Could create lots of files (1 file per asset).
    :param store_in_db: a boolean indicating whether to store the data in a sqlite database. Defaults to True.
    :param store_ids: a boolean indicating whether to store and save the IDs of the assets. Defaults to False. Could be memory consuming.
    :param use_raw_format: a boolean indicating whether to store the data in a raw format (as returned by the API) or after data have been parsed. Defaults to True.
    :param clean_database: a boolean indicating whether to clean the database before saving the data. Defaults to False.
    :param engine_version_for_obsolete_assets: a string representing the engine version to use to check if an asset is obsolete.
    :param core: an AppCore object. Defaults to None. If None, a new AppCore object will be created.
    :param progress_window: a ProgressWindow object. Defaults to None. If None, a new ProgressWindow object will be created.
    :param cli_args: a CliArgs object. Defaults to None. If None, a new CliArgs object will be created.
    """

    logger = logging.getLogger(__name__.split('.')[-1])  # keep only the class name
    update_loggers_level(logger)

    def __init__(
        self,
        start: int = 0,
        stop: int = 0,
        assets_per_page: int = 100,
        sort_by: str = 'effectiveDate',  # other values: 'title','currentPrice','discountPercentage'
        sort_order: str = 'DESC',  # other values: 'ASC'
        timeout: float = 10.0,
        max_threads: int = 8,
        store_in_files: bool = True,
        store_in_db: bool = True,
        store_ids: bool = False,
        use_raw_format: bool = True,
        load_from_files: bool = False,
        clean_database: bool = False,
        engine_version_for_obsolete_assets=None,
        core: AppCore = None,
        progress_window=None,  # don't use a typed annotation here to avoid import
        cli_args=None,
    ) -> None:
        self._last_run_filename: str = 'last_run.json'
        self._urls_list_filename: str = 'urls_list.txt'
        self._threads_count: int = 0
        self._files_count: int = 0
        self._thread_executor = None
        self._scraped_data = []  # the scraper scraped_data. Increased on each call to get_data_from_url(). Could be huge !!
        self._db_name: str = path_join(gui_g.s.scraping_folder, gui_g.s.sqlite_filename)
        self._scraped_ids = []  # store IDs of all items
        self._owned_asset_ids = []  # store IDs of all owned items
        self._urls = []  # list of all urls to scrap
        self.start: int = start
        self.stop: int = stop
        self.assets_per_page: int = assets_per_page
        self.sort_by: str = sort_by
        self.sort_order: str = sort_order
        self.max_threads: int = max_threads if gui_g.s.use_threads else 0
        self.load_from_files: bool = load_from_files
        self.store_in_files: bool = store_in_files
        self.store_in_db: bool = store_in_db
        self.store_ids = store_ids
        self.use_raw_format: bool = use_raw_format
        self.clean_database: bool = clean_database
        self.cli_args = cli_args
        # test several ways to get the following value depending on the context
        # noinspection PyBroadException
        try:
            self.engine_version_for_obsolete_assets = (
                engine_version_for_obsolete_assets or gui_g.UEVM_cli_ref.core.engine_version_for_obsolete_assets or
                gui_g.s.engine_version_for_obsolete_assets
            )
        except Exception:
            self.engine_version_for_obsolete_assets = None

        self.core = AppCore(timeout=timeout) if core is None else core
        self.asset_db_handler = UEAssetDbHandler(self._db_name)

        if progress_window is None:
            progress_window = FakeProgressWindow()
        self.progress_window = progress_window

        if self.load_from_files:
            self.store_in_files = False
            self.store_in_db = True

        if (assets_per_page > 100) or (assets_per_page < 1):
            self.assets_per_page = 100
            self.logger.error(f'assets_per_page must be between 1 and 100. Set to 100')

        message = f'UEAssetScraper initialized with max_threads= {max_threads}, start= {start}, stop= {stop}, assets_per_page= {assets_per_page}, sort_by= {sort_by}, sort_order= {sort_order}'
        message += f'\nData will be load from files in {gui_g.s.assets_data_folder}' if self.load_from_files else ''
        message += f'\nAsset Data will be saved in files in {gui_g.s.assets_data_folder}' if self.store_in_files else ''
        message += f'\nOwned Asset Data will be saved in files in {gui_g.s.owned_assets_data_folder}' if self.store_in_files else ''
        message += f'\nData will be saved in database in {self._db_name}' if self.store_in_db else ''
        message += f'\nAsset Ids will be saved in {self._last_run_filename} or in database' if self.store_ids else ''
        self._log_info(message)

    @staticmethod
    def read_json_file(app_name: str, owned_assets_only=False) -> (dict, str):
        """
        Load JSON data from a file.
        :param app_name: the name of the app to load the data from.
        :param owned_assets_only: whether only the owned assets are scraped.
        :return: a dictionary containing the loaded data.
        """
        folder = gui_g.s.owned_assets_data_folder if owned_assets_only else gui_g.s.assets_data_folder
        filename = app_name + '.json'
        json_data = {}
        message = ''
        with open(path_join(folder, filename), 'r') as fh:
            try:
                json_data = json.load(fh)
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
                'creationDate': data_from_egs_format['effectiveDate'],
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
                'lastModifiedDate': data_from_egs_format['effectiveDate'],
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

    def _log_debug(self, message):
        """ a simple wrapper to use when cli is not initialized"""
        if gui_g.UEVM_cli_ref is None and self.cli_args.debug:
            print(f'DEBUG {message}')
        else:
            if gui_g.s.testing_switch >= 1:
                # force printing debug messages when testing
                self.logger.info(message)
            else:
                self.logger.debug(message)

    def _log_info(self, message):
        """ a simple wrapper to use when cli is not initialized"""
        if gui_g.UEVM_cli_ref is None:
            print(f'INFO {message}')
        else:
            self.logger.info(message)

    def _log_warning(self, message):
        """ a simple wrapper to use when cli is not initialized"""
        if gui_g.UEVM_cli_ref is None:
            print(f'WARNING {message}')
        else:
            self.logger.warning(message)

    def _log_error(self, message):
        """ a simple wrapper to use when cli is not initialized"""
        if gui_g.UEVM_cli_ref is None:
            print(f'ERROR {message}')
        else:
            self.logger.error(message)

    def _parse_data(self, json_data: dict = None, owned_assets_only=False) -> []:
        """
        Parse on or more asset data from the response of an url query.
        :param json_data: a dictionary containing the data to parse.
        :param owned_assets_only: whether only the owned assets are scraped.
        :return: a list containing the parsed data.
        """

        content = []
        no_text_data = ''
        if json_data is None:
            return content
        try:
            # get the list of assets after a "scraping" of the json data using URL
            assets_data_list = json_data['data']['elements']
        except KeyError:
            # this exception is raised when data come from a json file. Not an issue
            # create a list of one asset when data come from a json file
            assets_data_list = [json_data]

        for asset_data in assets_data_list:
            uid = asset_data.get('id', None)
            if uid is None:
                # this should never occur
                self._log_warning(f'No id found for asset {asset_data}. Passing to next asset')
                return ''
            existing_data = self.asset_db_handler.get_assets_data(fields=self.asset_db_handler.preserved_data_fields, uid=uid)
            asset_existing_data = existing_data.get(uid, None)
            asset_data['asset_url'] = self.core.egs.get_marketplace_product_url(asset_data.get('urlSlug', None))
            if not uid:
                continue
            # self._log_debug(f"uid='{uid}'")  # debug only ex:'c77526fd4365450c9810e198450d2b91'

            categories = asset_data.get('categories', None)
            release_info = asset_data.get('releaseInfo', {})
            latest_release = release_info[0] if release_info else {}
            price = 0
            discount_price = 0
            discount_percentage = 0
            supported_versions = no_text_data
            origin = 'Marketplace'  # by default when scraped from marketplace
            date_now = datetime.now().strftime(default_datetime_format)
            grab_result = GrabResult.NO_ERROR.name

            # make some calculation with the "raw" data
            # ------------
            # set simple fields
            asset_data['thumbnail_url'] = asset_data['thumbnail']
            asset_data['category'] = categories[0]['name'] if categories else ''
            asset_data['author'] = asset_data['seller']['name']
            try:
                asset_data['asset_id'] = latest_release['appId']  # latest release
            except (KeyError, AttributeError, IndexError):
                grab_result = GrabResult.NO_APPID.name
                asset_data['asset_id'] = uid  # that's not the REAL asset_id, we use the uid instead

            # set prices and discount
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

            if discount_price == 0:
                discount_price = price
            asset_data['price'] = price
            asset_data['discount_price'] = discount_price
            asset_data['discount_percentage'] = discount_percentage

            # set rating
            try:
                average_rating = asset_data['rating']['averageRating']
                rating_total = asset_data['rating']['total']
            except KeyError:
                self.logger.debug(f'No rating for {asset_data["title"]}')
                average_rating, rating_total = self.asset_db_handler.get_rating_by_id(uid)
            asset_data['review'] = average_rating if average_rating else 0
            asset_data['review_count'] = rating_total if rating_total else 0

            # custom attributes
            asset_data['custom_attributes'] = ''
            try:
                custom_attributes = asset_data['customAttributes']
                if custom_attributes != {}:
                    self._log_debug(f'asset {uid}:custom_attributes= {custom_attributes}')
                    # has an external link
                    custom_attributes = 'external_link:' + custom_attributes['BuyLink']['value'] if custom_attributes.get('BuyLink', '') else ''
                    asset_data['custom_attributes'] = custom_attributes
            except (KeyError, AttributeError):
                asset_data['custom_attributes'] = ''

            # set various fields
            asset_data['page_title'] = asset_data['title']
            try:
                tmp_list = [','.join(item.get('compatibleApps')) for item in release_info]
                supported_versions = ','.join(tmp_list)
            except TypeError as error:
                self._log_debug(f'Error getting compatibleApps for asset with uid={uid}: {error!r}')
            asset_data['supported_versions'] = supported_versions
            asset_data['origin'] = origin

            asset_data['update_date'] = date_now
            tmp_date = latest_release.get('dateAdded', no_text_data) if latest_release else no_text_data
            tmp_date = convert_to_datetime(tmp_date, formats_to_use=[gui_g.s.epic_datetime_format, gui_g.s.csv_datetime_format])
            tmp_date = convert_to_str_datetime(tmp_date, gui_g.s.csv_datetime_format)
            asset_data['creation_date'] = tmp_date
            tmp_date = asset_existing_data.get('date_added_in_db', None) if asset_existing_data else date_now
            asset_data['date_added_in_db'] = tmp_date

            asset_data['obsolete'] = is_asset_obsolete(supported_versions, self.engine_version_for_obsolete_assets)
            old_price = asset_existing_data.get('price', None) if asset_existing_data else 0
            older_price = asset_existing_data.get('old_price', None) if asset_existing_data else 0
            asset_data['old_price'] = old_price if old_price else older_price
            # note: asset_data['tags'] will be converted in ue_asset.init_from_dict(asset_data)

            # the current parsing process does not produce as many error as the previous one
            # mainly, there is no error during the process
            old_grab_result = asset_existing_data.get('grab_result', GrabResult.NO_ERROR.name) if asset_existing_data else GrabResult.NO_ERROR.name
            if owned_assets_only and old_grab_result == GrabResult.NO_ERROR.name:
                # if no error occurs and if we only parse owned assets, the parsed data ARE less complete than the "normal" one
                # so, we set the grab result to PARTIAL
                grab_result = GrabResult.PARTIAL.name
            asset_data['grab_result'] = grab_result
            # not pertinent, kept for compatibility with CSV format. Could be removed later after checking usage
            # asset_data['app_name'] = asset_data['asset_id']
            # asset_data['developer'] = asset_data['author']
            # asset_data['compatible_versions'] = no_text_data
            # asset_data['ue_version'] = no_text_data
            # asset_data['uid'] = no_text_data

            # we use copy data for user_fields to preserve user data
            if asset_existing_data:
                for field in self.asset_db_handler.user_fields:
                    old_value = asset_existing_data.get(field, None)
                    if old_value:
                        asset_data[field] = old_value
            # installed_folders
            installed_folders = asset_data.get('installed_folders', '')  # asset_existing_data
            app_installed = self.core.uevmlfs.get_installed_app(asset_data.get('asset_id', ''))
            if app_installed:
                app_installed_folders = app_installed.installed_folders
                # merge the 2 lists without duplicates
                installed_folders = list(set(installed_folders + app_installed_folders))
            asset_data['installed_folders'] = sorted(installed_folders)

            # we use an UEAsset object to store the data and create a valid dict from it
            ue_asset = UEAsset()
            ue_asset.init_from_dict(asset_data)
            tags = ue_asset.data.get('tags', [])
            tags_str = self.asset_db_handler.convert_tag_list_to_string(tags)
            ue_asset.data['tags'] = tags_str
            content.append(ue_asset.data)
            message = f'Asset with uid={uid} added to content ue_asset.data: owned={ue_asset.data["owned"]} creation_date={ue_asset.data["creation_date"]}'
            # message += f'\nTAGS:{tags_str}' # this line seems to create BUGS in threads (WTF !!!!)
            self._log_debug(message)
            if self.store_ids:
                try:
                    self._scraped_ids.append(uid)
                except (AttributeError, TypeError) as error:
                    self._log_debug(f'Error when adding uid to self.scraped_ids: {error!r}')
        # end for asset_data in json_data['data']['elements']:
        return content

    def _save_in_db(self, last_run_content: dict) -> None:
        """
        Stores the asset data in the database.
        """
        if not self.store_in_db:
            return
        # convert the list of ids to a string for the database only
        last_run_content['scraped_ids'] = ','.join(self._scraped_ids) if self.store_ids else ''

        if self.clean_database:
            # next line will delete all assets in the database
            if box_yesno(
                'Current settings and params are set to delete all existing data before rebuilding. All user fields values will be lost. Are you sure your want to do that ?'
            ):
                self.asset_db_handler.delete_all_assets(keep_added_manually=True)
        self.asset_db_handler.set_assets(self._scraped_data)
        self.asset_db_handler.save_last_run(last_run_content)

    def _get_filename_from_asset_data(self, asset_data) -> str:
        """
        Return the filename to use to save the asset data.
        :param asset_data: the asset data.
        :return:  the filename to use to save the asset data.
        """
        try:
            app_id = asset_data['releaseInfo'][0]['appId']
            filename = f'{app_id}.json'
        except (KeyError, IndexError) as error:
            self.logger.warning(f'Error getting appId for asset with id {asset_data["id"]}: {error!r}')
            slug = asset_data.get('urlSlug', None)
            if slug is None:
                slug = asset_data.get('catalogItemId', create_uid())
            filename = f'_no_appId_{slug}.json'
        return filename

    def gather_all_assets_urls(self, empty_list_before=False, save_result=True, owned_assets_only=False) -> None:
        """
        Gather all the URLs (with pagination) to be parsed and stores them in a list for further use.
        :param empty_list_before: whether the list of URLs is emptied before adding the new ones.
        :param save_result: whether the list of URLs is saved in the database.
        :param owned_assets_only: whether only the owned assets are scraped.
        """
        if empty_list_before:
            self._urls = []
        start_time = time.time()
        if self.stop <= 0:
            self.stop = self.core.egs.get_scraped_asset_count(owned_assets_only=owned_assets_only)
        assets_count = self.stop - self.start
        pages_count = int(assets_count / self.assets_per_page)
        if (assets_count % self.assets_per_page) > 0:
            pages_count += 1
        self.progress_window.reset(new_value=0, new_text='Gathering URLs', new_max_value=pages_count)
        for i in range(int(pages_count)):
            if not self.progress_window.update_and_continue(value=i, text=f'Gathering URL ({i + 1}/{pages_count})'):
                return
            start = self.start + (i * self.assets_per_page)
            if owned_assets_only:
                url = self.core.egs.get_owned_scrap_url(start, self.assets_per_page)
            else:
                url = self.core.egs.get_scrap_url(start, self.assets_per_page, self.sort_by, self.sort_order)
            self._urls.append(url)
        self._log_info(f'It took {(time.time() - start_time):.3f} seconds to gather {len(self._urls)} urls')
        if save_result:
            self.save_to_file(filename=self._urls_list_filename, data=self._urls, is_json=False, is_owned=owned_assets_only)

    def get_data_from_url(self, url='', owned_assets_only=False) -> None:
        """
        Grab the data from the given url and stores it in the scraped_data property.
        :param url: the url to grab the data from. If not given, uses the url property of the class.
        :param owned_assets_only: whether only the owned assets are scraped.
        """
        if gui_g.progress_window_ref is not None and not gui_g.progress_window_ref.continue_execution:
            return

        if not url:
            self._log_error('No url given to get_data_from_url()')
            return

        thread_data = ''
        try:
            if self._threads_count > 1:
                # add a delay when multiple threads are used
                time.sleep(random.uniform(1.0, 3.0))
                thread = current_thread()
                thread_data = f' ==> By Thread name={thread.name}'

            self._log_info(f'--- START scraping data from {url}{thread_data}')

            json_data = self.core.egs.get_json_data_from_url(url)
            if json_data.get('errorCode', '') != '':
                self._log_error(f'Error getting data from url {url}: {json_data["errorCode"]}')
                return
            try:
                # when multiple assets are returned, the data is in the 'elements' key
                count = len(json_data['data']['elements'])
                self._log_info(f'==> parsed url {url}: got a list of {count} assets')
            except KeyError:
                # when only one asset is returned, the data is in the 'data' key
                self._log_info(f'==> parsed url {url} for one asset')
                json_data['data']['elements'] = [json_data['data']['data']]

            if json_data:
                if self.store_in_files and self.use_raw_format:
                    # store the result file in the raw format
                    # noinspection PyBroadException
                    try:
                        url_vars = extract_variables_from_url(url)
                        start = int(url_vars['start'])
                        count = int(url_vars['count'])
                        suffix = f'{start}-{start + count - 1}'
                    except Exception:
                        suffix = datetime.now().strftime("%y-%m-%d_%H-%M-%S")
                    filename = f'assets_{suffix}.json'
                    self.save_to_file(filename=filename, data=json_data, is_global=True)

                    # store the individial asset in file
                    for asset_data in json_data['data']['elements']:
                        filename = self._get_filename_from_asset_data(asset_data)
                        self.save_to_file(filename=filename, data=asset_data, is_owned=owned_assets_only)
                        self._files_count += 1
                content = self._parse_data(json_data)
                self._scraped_data.append(content)
        except Exception as error:
            self._log_warning(f'Error getting data from url {url}: {error!r}')

    def get_scraped_data(self, owned_assets_only=False) -> None:
        """
        Load from files or downloads the items from the URLs and stores them in the scraped_data property.
        The execution is done in parallel using threads.
        :param owned_assets_only: whether only the owned assets are scraped

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

        has_data = False
        if self.load_from_files:
            has_data = self.load_from_json_files() > 0

        if not has_data:
            # start_time = time.time()
            # self.get_owned_asset_ids()
            # message = f'It took {(time.time() - start_time):.3f} seconds to get {len(self.owned_asset_ids)} owned asset ids'
            # self._log_info(message)

            start_time = time.time()
            if self._urls is None or len(self._urls) == 0:
                self.gather_all_assets_urls(owned_assets_only=owned_assets_only)
            self.progress_window.reset(new_value=0, new_text='Scraping data from URLs', new_max_value=len(self._urls))
            url_count = len(self._urls)
            if self.max_threads > 0 and url_count > 0:
                self._threads_count = min(self.max_threads, url_count)
                # threading processing COULD be stopped by the progress window
                self.progress_window.show_btn_stop()
                self._thread_executor = concurrent.futures.ThreadPoolExecutor(max_workers=self._threads_count, thread_name_prefix="Asset_Scaper")
                futures = {}
                # for url in self.urls:
                while len(self._urls) > 0:
                    url = self._urls.pop()
                    # Submit the task and add its Future to the dictionary
                    future = self._thread_executor.submit(lambda url_param: self.get_data_from_url(url_param, owned_assets_only), url)
                    futures[url] = future

                with concurrent.futures.ThreadPoolExecutor():
                    for future in concurrent.futures.as_completed(futures.values()):
                        try:
                            _ = future.result()
                            # print("Result: ", result)
                        except Exception as error:
                            self._log_warning(f'The following error occurs in threading: {error!r}')
                        if not self.progress_window.update_and_continue(increment=1):
                            # self._log_info(f'User stop has been pressed. Stopping running threads....')   # will flood console
                            stop_executor(futures)
                self._thread_executor.shutdown(wait=False)
            else:
                for url in self._urls:
                    self.get_data_from_url(url, owned_assets_only)
            if self.store_in_files and self.use_raw_format:
                message = f'It took {(time.time() - start_time):.3f} seconds to download {len(self._urls)} urls and store the data in {self._files_count} files'
            else:
                message = f'It took {(time.time() - start_time):.3f} seconds to download {len(self._urls)} urls'
            self._log_info(message)
            # format the list to be 1 long list rather than multiple lists nested in a list - [['1'], ['2'], ...] -> ['1','2', ...]
            self._scraped_data = list(chain.from_iterable(self._scraped_data))

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

        if data is None or len(data) == 0:
            self._log_warning('No data to save')
            return False

        folder = gui_g.s.owned_assets_data_folder if is_owned else gui_g.s.assets_data_folder
        folder = gui_g.s.assets_global_folder if is_global else folder

        _, folder = check_and_get_folder(folder)
        if filename is None:
            filename = prefix
            if self.start > 0:
                filename += '_' + str(self.start)
                filename += '_' + str(self.start + self.assets_per_page)
            filename += '.json'
        filename = path_join(folder, filename)
        try:
            with open(filename, 'w') as fh:
                if is_json:
                    json.dump(data, fh)
                else:
                    # write data as a list in the file
                    fh.write('\n'.join(data))
            self._log_debug(f'Data saved into {filename}')
            return True
        except PermissionError as error:
            self._log_warning(f'The following error occured when saving data into {filename}:{error!r}')
            return False

    def load_from_json_files(self, owned_assets_only=False) -> int:
        """
        Load all JSON data retrieved from the Unreal Engine Marketplace API to paginated files.
        :param owned_assets_only: whether to only the owned assets are scraped.
        :return: the number of files loaded.
        """
        start_time = time.time()
        self._files_count = 0
        self._scraped_ids = []
        self._scraped_data = []
        folder = gui_g.s.owned_assets_data_folder if owned_assets_only else gui_g.s.assets_data_folder

        files = os.listdir(folder)
        files_count = len(files)
        # Note: this data have the same structure as the table last_run inside the method UEAsset.create_tables()
        self._log_info(f'Loading {files_count} files from {folder}')
        self.progress_window.reset(new_value=0, new_text='Loading asset data from json files', new_max_value=files_count)
        for filename in files:
            if filename.endswith('.json') and filename != self._last_run_filename:
                # self._log_debug(f'Loading {filename}')
                with open(path_join(folder, filename), 'r') as fh:
                    try:
                        json_data = json.load(fh)
                    except json.decoder.JSONDecodeError as error:
                        self._log_warning(f'The following error occured when loading data from {filename}:{error!r}')
                        continue
                    assets_data = self._parse_data(json_data)  # self._parse_data returns a list of assets
                    for asset_data in assets_data:
                        self._scraped_data.append(asset_data)
                self._files_count += 1
                if not self.progress_window.update_and_continue(increment=1):
                    return self._files_count
                if gui_g.s.testing_switch == 1 and self._files_count >= 100:
                    break
        message = f'It took {(time.time() - start_time):.3f} seconds to load the data from {self._files_count} files'
        self._log_info(message)

        # save results in the last_run file
        content = {
            'date': str(datetime.now()),
            'mode': 'load_owned' if owned_assets_only else 'load',
            'files_count': self._files_count,
            'items_count': len(self._scraped_data),
            'scraped_ids': self._scraped_ids if self.store_ids else ''
        }
        filename = path_join(folder, self._last_run_filename)
        with open(filename, 'w') as fh:
            json.dump(content, fh)

        self.progress_window.reset(new_value=0, new_text='Saving into database', new_max_value=0)
        # self._save_in_db(last_run_content=content) # duplicate with a caller
        return self._files_count

    def save(self, owned_assets_only=False, save_last_run_file=True) -> None:
        """
        Save all JSON data retrieved from the Unreal Engine Marketplace API to paginated files.
        :param owned_assets_only: whether to only the owned assets are scraped.
        :param save_last_run_file: whether the last_run file is saved.
        """
        if owned_assets_only:
            self._log_info('Only Owned Assets will be scraped')

        self.get_scraped_data(owned_assets_only=owned_assets_only)
        if not self.progress_window.continue_execution:
            return

        # Note: this data have the same structure as the table last_run inside the method UEAsset.create_tables()
        content = {
            'date': str(datetime.now()),
            'mode': 'save_owned' if owned_assets_only else 'save',
            'files_count': 0,
            'items_count': len(self._scraped_data),
            'scraped_ids': ''
        }

        start_time = time.time()
        if self.store_in_files and not self.use_raw_format:
            self.progress_window.reset(new_value=0, new_text='Saving into files', new_max_value=len(self._scraped_data))
            # store the data in a AFTER parsing it
            self._files_count = 0
            for asset_data in self._scraped_data:
                filename = self._get_filename_from_asset_data(asset_data)
                self.save_to_file(filename=filename, data=asset_data, is_owned=owned_assets_only)
                self._files_count += 1
                if not self.progress_window.update_and_continue(increment=1):
                    return
            message = f'It took {(time.time() - start_time):.3f} seconds to save the data in {self._files_count} files'
            self._log_info(message)

        # save results in the last_run file
        content['files_count'] = self._files_count
        content['scraped_ids'] = self._scraped_ids if self.store_ids else ''
        if save_last_run_file:
            folder = gui_g.s.owned_assets_data_folder if owned_assets_only else gui_g.s.assets_data_folder
            filename = path_join(folder, self._last_run_filename)
            with open(filename, 'w') as fh:
                json.dump(content, fh)

        self.progress_window.reset(new_value=0, new_text='Saving into database', new_max_value=None)
        self._save_in_db(last_run_content=content)
        self._log_info('data saved')

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
        start=st.start_row,
        stop=st.stop_row,
        assets_per_page=st.ue_asset_per_page,
        max_threads=st.threads,
        store_in_db=True,
        store_in_files=not st.load_data_from_files,
        store_ids=False,
        load_from_files=st.load_data_from_files,
        clean_database=st.clean_db
    )
    scraper.save()
