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

import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.api.egs import EPCAPI, GrabResult, is_asset_obsolete
from UEVaultManager.core import default_datetime_format
from UEVaultManager.models.UEAssetClass import UEAsset
from UEVaultManager.models.UEAssetDbHandlerClass import UEAssetDbHandler
from UEVaultManager.tkgui.modules.functions_no_deps import check_and_get_folder

test_only_mode = False  # create some limitations to speed up the dev process - Set to True for debug Only


def get_filename_from_asset_data(asset_data) -> str:
    """
    Returns the filename to use to save the asset data
    :param asset_data: the asset data
    :return:  the filename to use to save the asset data
    """
    try:
        app_id = asset_data['releaseInfo'][0]['appId']
        filename = f'{app_id}.json'
    except KeyError:
        uid = asset_data['id']
        filename = f'_no_appId_asset_{uid}.json'
    return filename


class UEAssetScraper:
    """
    A class that handles scraping data from the Unreal Engine Marketplace.
    It saves the data in json files and/or in a sqlite database
    :param start: An int representing the starting index for the data to retrieve. Defaults to 0.
    :param start: An int representing the ending index for the data to retrieve. Defaults to 0.
    :param assets_per_page: An int representing the number of items to retrieve per request. Defaults to 100.
    :param sort_by: A string representing the field to sort by. Defaults to 'effectiveDate'.
    :param sort_order: A string representing the sort order. Defaults to 'ASC'.
    :param timeout: A float representing the timeout for the requests. Defaults to 10.0.
    :param max_threads: An int representing the maximum number of threads to use. Defaults to 8. Set to 0 to disable multithreading.
    :param load_from_files: A boolean indicating whether to load the data from files instead of scraping it. Defaults to False. If set to True, store_in_files will be set to False and store_in_db will be set to True.
    :param store_in_files: A boolean indicating whether to store the data in csv files. Defaults to True. Could create lots of files (1 file per asset)
    :param store_in_db: A boolean indicating whether to store the data in a sqlite database. Defaults to True.
    :param store_ids: A boolean indicating whether to store and save the IDs of the assets. Defaults to False. Could be memory consuming.
    :param use_raw_format: A boolean indicating whether to store the data in a raw format (as returned by the API) or after data have been parsed. Defaults to True.
    :param clean_database: A boolean indicating whether to clean the database before saving the data. Defaults to False.
    :param engine_version_for_obsolete_assets: A string representing the engine version to use to check if an asset is obsolete.
    :param egs: An EPCAPI object (session handler). Defaults to None. If None, a new EPCAPI object will be created and the session used WON'T BE LOGGED.
    """

    def __init__(
        self,
        start=0,
        stop=0,
        assets_per_page=100,
        sort_by='effectiveDate',  # other values: 'title','currentPrice','discountPercentage'
        sort_order='DESC',  # other values: 'ASC'
        timeout=10.0,
        max_threads=8,
        store_in_files=True,
        store_in_db=True,
        store_ids=False,
        use_raw_format=True,
        load_from_files=False,
        clean_database=False,
        engine_version_for_obsolete_assets=None,
        egs: EPCAPI = None,
    ) -> None:
        self.start = start
        self.stop = stop
        self.assets_per_page = assets_per_page
        self.sort_by = sort_by
        self.sort_order = sort_order
        self.load_from_files = load_from_files
        self.store_in_files = store_in_files
        self.store_in_db = store_in_db
        self.store_ids = store_ids
        self.use_raw_format = use_raw_format
        self.clean_database = clean_database
        # test several ways to get the following value depending on the context
        # noinspection PyBroadException
        try:
            self.engine_version_for_obsolete_assets = (
                engine_version_for_obsolete_assets or gui_g.UEVM_cli_ref.core.engine_version_for_obsolete_assets or
                gui_g.s.engine_version_for_obsolete_assets
            )
        except Exception:
            self.engine_version_for_obsolete_assets = None

        self.last_run_filename = 'last_run.json'
        self.urls_list_filename = 'urls_list.txt'
        self.assets_data_folder = os.path.join(gui_g.s.scraping_folder, 'assets', 'marketplace')
        self.owned_assets_data_folder = os.path.join(gui_g.s.scraping_folder, 'assets', 'owned')
        self.db_name = os.path.join(gui_g.s.scraping_folder, 'assets.db')
        self.max_threads = max_threads
        self.threads_count = 0

        self.files_count = 0
        self.scraped_data = []  # the scraper scraped_data. Increased on each call to get_data_from_url(). Could be huge !!
        self.scraped_ids = []  # store IDs of all items
        self.owned_asset_ids = []  # store IDs of all owned items
        self.existing_data = {
        }  # dictionary {ids, rows} : the data in database before scraping. Contains only minimal information (user fields, id, price)

        self.urls = []  # list of all urls to scrap

        self.egs = EPCAPI(timeout=timeout) if egs is None else egs
        self.logger = logging.getLogger(__name__)
        self.asset_db_handler = UEAssetDbHandler(self.db_name)

        # self.logger.setLevel(logging.DEBUG)
        if self.load_from_files:
            self.store_in_files = False
            self.store_in_db = True

        if (assets_per_page > 100) or (assets_per_page < 1):
            self.assets_per_page = 100
            self.logger.error(f'assets_per_page must be between 1 and 100. Set to 100')

        message = f'UEAssetScraper initialized with max_threads= {max_threads}, start= {start}, stop= {stop}, assets_per_page= {assets_per_page}, sort_by= {sort_by}, sort_order= {sort_order}'
        message += f'\nData will be load from files in {self.assets_data_folder}' if self.load_from_files else ''
        message += f'\nAsset Data will be saved in files in {self.assets_data_folder}' if self.store_in_files else ''
        message += f'\nOwned Asset Data will be saved in files in {self.owned_assets_data_folder}' if self.store_in_files else ''
        message += f'\nData will be saved in database in {self.db_name}' if self.store_in_db else ''
        message += f'\nAsset Ids will be saved in {self.last_run_filename} or in database' if self.store_ids else ''
        self._log_info(message)

    def _log_debug(self, message):
        """ a simple wrapper to use when cli is not initialized"""
        if gui_g.UEVM_cli_ref is None:
            print(message)
        else:
            self.logger.debug(message)

    def _log_info(self, message):
        """ a simple wrapper to use when cli is not initialized"""
        if gui_g.UEVM_cli_ref is None:
            print(message)
        else:
            self.logger.info(message)

    def _log_warning(self, message):
        """ a simple wrapper to use when cli is not initialized"""
        if gui_g.UEVM_cli_ref is None:
            print(message)
        else:
            self.logger.warning(message)

    def _log_error(self, message):
        """ a simple wrapper to use when cli is not initialized"""
        if gui_g.UEVM_cli_ref is None:
            print(message)
        else:
            self.logger.error(message)

    def _parse_data(self, json_data: dict = None, owned_assets_only=False) -> []:
        """
        Parses on or more asset data from the response of an url query.
        :param json_data: A dictionary containing the data to parse.
        :param owned_assets_only: if True, only the owned assets are scrapped
        :return: A list containing the parsed data.
        """
        content = []
        no_text_data = ''

        if json_data is None:
            return content

        try:
            # get the list of assets after a "scrapping" of the json data using URL
            assets_data_list = json_data['data']['elements']
        except KeyError:
            self._log_debug('data is not in a "scrapped" format')
            # create a list of one asset when data come from a json file
            assets_data_list = [json_data]

        for asset_data in assets_data_list:
            uid = asset_data.get('id', None)
            if uid is None:
                # this should never occur
                self._log_warning(f'No id found for asset {asset_data}. Passing to next asset')
                continue
            categories = asset_data.get('categories', None)
            release_info = asset_data.get('releaseInfo', {})
            asset_existing_data = self.existing_data.get(uid, None)
            price = 0
            discount_price = 0
            discount_percentage = 0
            average_rating = 0
            rating_total = 0
            supported_versions = no_text_data
            origin = 'Marketplace'  # by default when scrapped from marketplace
            date_now = datetime.now().strftime(default_datetime_format)
            grab_result = GrabResult.NO_ERROR.name

            # make some calculation with the "raw" data
            # ------------
            # set simple fields
            asset_data['thumbnail_url'] = asset_data['thumbnail']
            asset_data['category'] = categories[0]['name'] if categories else ''
            asset_data['author'] = asset_data['seller']['name']
            asset_data['asset_url'] = self.egs.get_asset_url(asset_data.get('urlSlug', None))
            try:
                asset_data['asset_id'] = release_info[0]['appId']  # latest release
            except (KeyError, AttributeError):
                grab_result = GrabResult.NO_APPID.name
                asset_data['asset_id'] = uid

            # set url and (re) update data if needed
            existing_url = asset_existing_data['asset_url'] if asset_existing_data else ''
            try:
                if existing_url and asset_existing_data and asset_data['asset_url'] != existing_url and asset_existing_data.get(
                    'grab_result', GrabResult.NO_ERROR.name
                ) != GrabResult.NO_ERROR.name:
                    self._log_warning(f'URL have changed in database and asset for asset #{uid}. Parsing data from {existing_url}')
                    # we use existing_url and not asset_data['asset_url'] because it could have been corrected by the user
                    # TODO: parse data from existing_url
            except (KeyError, TypeError) as error:
                self._log_debug(f'Error checking asset_url for asset #{uid}: {error!r}')

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
            asset_data['review'] = average_rating
            asset_data['review_count'] = rating_total

            # custom attributes
            asset_data['custom_attributes'] = ''
            try:
                custom_attributes = asset_data['customAttributes']
                if custom_attributes != {}:
                    self._log_info(f'asset {uid}:custom_attributes= {custom_attributes}')
                    # has an external link
                    custom_attributes = 'external_link:' + custom_attributes['BuyLink']['value'] if custom_attributes.get('BuyLink', '') else ''
                    asset_data['custom_attributes'] = custom_attributes
            except (KeyError, AttributeError):
                asset_data['custom_attributes'] = ''

            # set origin
            asset_data['page_title'] = asset_data['title']
            try:
                tmp_list = [','.join(item.get('compatibleApps')) for item in release_info]
                supported_versions = ','.join(tmp_list)
            except TypeError as error:
                self._log_debug(f'Error getting compatibleApps for asset #{uid}: {error!r}')
            asset_data['supported_versions'] = supported_versions
            asset_data['origin'] = origin
            asset_data['obsolete'] = is_asset_obsolete(supported_versions, self.engine_version_for_obsolete_assets)
            old_price = asset_existing_data.get('price', None) if asset_existing_data else 0
            older_price = asset_existing_data.get('old_price', None) if asset_existing_data else 0
            asset_data['old_price'] = old_price if old_price else older_price
            asset_data['creation_date'] = release_info[0].get('dateAdded', no_text_data) if release_info else no_text_data
            asset_data['update_date'] = date_now
            asset_data['date_added_in_db'] = asset_existing_data.get('date_added_in_db', None) if asset_existing_data else date_now
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

            # we use an UEAsset object to store the data and create a valid dict from it
            ue_asset = UEAsset()

            # we use copy data for user_fields to preserve user data
            if asset_existing_data:
                for field in self.asset_db_handler.user_fields:
                    old_value = asset_existing_data.get(field, None)
                    if old_value:
                        asset_data[field] = old_value

            ue_asset.init_from_dict(asset_data)
            content.append(ue_asset.data)
            message = f'Asset #{uid} added to content ue_asset.data: owned={ue_asset.data["owned"]} date_added_in_db={ue_asset.data["date_added_in_db"]} discount_percentage={ue_asset.data["discount_percentage"]}'
            self._log_debug(message)
            # print(message) # only if run from main
            if self.store_ids:
                try:
                    self.scraped_ids.append(uid)
                except (AttributeError, TypeError):
                    self._log_debug(f'Error adding {uid} to self.scraped_ids')
        # end for asset_data in json_data['data']['elements']:
        return content

    def _save_in_db(self, last_run_content: dict) -> None:
        """
        Stores the asset data in the database.
        """
        if not self.store_in_db:
            return
        # convert the list of ids to a string for the database only
        last_run_content['scrapped_ids'] = ','.join(self.scraped_ids) if self.store_ids else ''

        if self.clean_database:
            # next line will delete all assets in the database
            self.asset_db_handler.delete_all_assets()
            self.asset_db_handler.set_assets(self.scraped_data)
        else:
            self.asset_db_handler.set_assets(self.scraped_data)
        self.asset_db_handler.save_last_run(last_run_content)

    def gather_all_assets_urls(self, empty_list_before=False, save_result=True, owned_assets_only=False) -> None:
        """
        Gathers all the URLs (with pagination) to be parsed and stores them in a list for further use.
        :param empty_list_before: if True, the list of URLs is emptied before adding the new ones
        :param save_result: if True, the list of URLs is saved in the database
        :param owned_assets_only: if True, only the owned assets are scrapped
        """
        if empty_list_before:
            self.urls = []
        start_time = time.time()
        if self.stop <= 0:
            self.stop = self.egs.get_scrapped_asset_count(owned_assets_only=owned_assets_only)
        assets_count = self.stop - self.start
        pages_count = int(assets_count / self.assets_per_page)
        if (assets_count % self.assets_per_page) > 0:
            pages_count += 1
        for i in range(int(pages_count)):
            start = self.start + (i * self.assets_per_page)
            if owned_assets_only:
                url = self.egs.get_owned_scrap_url(start, self.assets_per_page)
            else:
                url = self.egs.get_scrap_url(start, self.assets_per_page, self.sort_by, self.sort_order)
            self.urls.append(url)
        self._log_info(f'It took {(time.time() - start_time):.3f} seconds to gather {len(self.urls)} urls')
        if save_result:
            self.save_to_file(filename=self.urls_list_filename, data=self.urls, is_json=False, is_owned=owned_assets_only)

    def get_data_from_url(self, url='', owned_assets_only=False) -> None:
        """
        Grabs the data from the given url and stores it in the scraped_data property.
        :param url: The url to grab the data from. If not given, uses the url property of the class.
        :param owned_assets_only: if True, only the owned assets are scrapped
        """
        if not url:
            self._log_error('No url given to get_data_from_url()')
            return
        self._log_info(f'Opening url {url}')
        json_data = self.egs.get_scrapped_assets(url)
        if json_data.get('errorCode', '') != '':
            self._log_error(f'Error getting data from url {url}: {json_data["errorCode"]}')
            return
        try:
            number = len(json_data['data']['elements'])
        except KeyError:
            number = 0
        self._log_info(f'==> parsed url {url}: got {number} assets')

        if json_data:
            if self.store_in_files and self.use_raw_format:
                for asset_data in json_data['data']['elements']:
                    filename = get_filename_from_asset_data(asset_data)
                    self.save_to_file(filename=filename, data=asset_data, is_owned=owned_assets_only)
                    self.files_count += 1
            content = self._parse_data(json_data)
            self.scraped_data.append(content)
        if self.threads_count > 1:
            # add a delay when multiple threads are used
            time.sleep(random.uniform(1.0, 3.0))

    def get_scraped_data(self, owned_assets_only=False) -> None:
        """
        Loads from files or downloads the items from the URLs and stores them in the scraped_data property.
        The execution is done in parallel using threads.
        :param owned_assets_only: if True, only the owned assets are scrapped

        Note: if self.urls is None or empty, gather_urls() will be called first.
        """
        # store previous data in the existing_data property
        self.existing_data = self.asset_db_handler.get_assets_data(fields=self.asset_db_handler.existing_data_fields)

        if self.load_from_files:
            self.load_from_json_files()
        else:
            # start_time = time.time()
            # self.get_owned_asset_ids()
            # message = f'It took {(time.time() - start_time):.3f} seconds to get {len(self.owned_asset_ids)} owned asset ids'
            # self._log_info(message)

            start_time = time.time()
            if self.urls is None or len(self.urls) == 0:
                self.gather_all_assets_urls(owned_assets_only=owned_assets_only)
            if self.max_threads > 0:
                self.threads_count = min(self.max_threads, len(self.urls))
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.threads_count) as executor:
                    # executor.map(self.get_data_from_url, self.urls)
                    executor.map(lambda url_param: self.get_data_from_url(url_param, owned_assets_only), self.urls)

            else:
                for url in self.urls:
                    self.get_data_from_url(url, owned_assets_only)
            if self.store_in_files and self.use_raw_format:
                message = f'It took {(time.time() - start_time):.3f} seconds to download {len(self.urls)} urls and store the data in {self.files_count} files'
            else:
                message = f'It took {(time.time() - start_time):.3f} seconds to download {len(self.urls)} urls'
            self._log_info(message)
            # format the list to be 1 long list rather than multiple lists nested in a list - [['1'], ['2'], ...] -> ['1','2', ...]
            self.scraped_data = list(chain.from_iterable(self.scraped_data))

    def save_to_file(self, prefix='assets', filename=None, data=None, is_json=True, is_owned=False) -> bool:
        """
        Saves JSON data to a file.
        :param data: A dictionary containing the data to save. Defaults to None. If None, the data will be used.
        :param prefix: A string representing the prefix to use for the file name. Defaults to 'assets'.
        :param filename: A string representing the file name to use. Defaults to None. If None, a file name will be generated using the prefix and the start and count properties.
        :param is_json: A boolean indicating whether the data is JSON or not. Defaults to True.
        :param is_owned: A boolean indicating whether the data is owned assets or not. Defaults to False.
        :return: A boolean indicating whether the file was saved successfully.
        """
        if data is None:
            data = self.scraped_data

        if data is None or len(data) == 0:
            self._log_warning('No data to save')
            return False

        folder = self.owned_assets_data_folder if is_owned else self.assets_data_folder

        _, folder = check_and_get_folder(folder)
        if filename is None:
            filename = prefix
            if self.start > 0:
                filename += '_' + str(self.start)
                filename += '_' + str(self.start + self.assets_per_page)
            filename += '.json'
        filename = os.path.join(folder, filename)
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

    def load_from_json_files(self, owned_assets_only=False) -> None:
        """
        Load all JSON data retrieved from the Unreal Engine Marketplace API to paginated files.
        :param owned_assets_only: if True, only the owned assets are scrapped
        """
        start_time = time.time()
        self.files_count = 0
        self.scraped_ids = []
        self.scraped_data = []
        folder = self.owned_assets_data_folder if owned_assets_only else self.assets_data_folder

        files = os.listdir(folder)
        files_count = len(files)
        # Note: this data have the same structure as the table last_run inside the method UEAsset.create_tables()
        self._log_info(f'Loading {files_count} files from {folder}')
        for filename in files:
            if filename.endswith('.json') and filename != self.last_run_filename:
                # self._log_debug(f'Loading {filename}')
                with open(os.path.join(folder, filename), 'r') as fh:
                    json_data = json.load(fh)
                    assets_data = self._parse_data(json_data)  # self._parse_data returns a list of assets
                    for asset_data in assets_data:
                        self.scraped_data.append(asset_data)
                self.files_count += 1
        message = f'It took {(time.time() - start_time):.3f} seconds to load the data from {self.files_count} files'
        self._log_info(message)

        # save results in the last_run file
        content = {
            'date': str(datetime.now()),
            'mode': 'load_owned' if owned_assets_only else 'load',
            'files_count': self.files_count,
            'items_count': len(self.scraped_data),
            'scrapped_ids': self.scraped_ids if self.store_ids else ''
        }
        filename = os.path.join(folder, self.last_run_filename)
        with open(filename, 'w') as fh:
            json.dump(content, fh)

        self._save_in_db(last_run_content=content)

    def save(self, owned_assets_only=False) -> None:
        """
        Saves all JSON data retrieved from the Unreal Engine Marketplace API to paginated files.
        :param owned_assets_only: if True, only the owned assets are scrapped
        """
        if owned_assets_only:
            self._log_info('Only Owned Assets will be scrapped')

        self.get_scraped_data(owned_assets_only=owned_assets_only)

        # Note: this data have the same structure as the table last_run inside the method UEAsset.create_tables()
        content = {
            'date': str(datetime.now()),
            'mode': 'save_owned' if owned_assets_only else 'save',
            'files_count': 0,
            'items_count': len(self.scraped_data),
            'scrapped_ids': ''
        }

        start_time = time.time()
        if self.store_in_files and not self.use_raw_format:
            # store the data in a AFTER parsing it
            self.files_count = 0
            for asset_data in self.scraped_data:
                filename = get_filename_from_asset_data(asset_data)
                self.save_to_file(filename=filename, data=asset_data, is_owned=owned_assets_only)
                self.files_count += 1
            message = f'It took {(time.time() - start_time):.3f} seconds to save the data in {self.files_count} files'
            self._log_info(message)

        # save results in the last_run file
        content['files_count'] = self.files_count
        content['scrapped_ids'] = self.scraped_ids if self.store_ids else ''
        folder = self.owned_assets_data_folder if owned_assets_only else self.assets_data_folder
        filename = os.path.join(folder, self.last_run_filename)
        with open(filename, 'w') as fh:
            json.dump(content, fh)

        self._save_in_db(last_run_content=content)
        self._log_info('data saved')


if __name__ == '__main__':
    # the following code is just for class testing purposes

    # set the number of rows to retrieve per page
    # As the asset are saved individually by default, this value is only use for pagination in the files that store the url
    # it speeds up the process of requesting the asset list
    rows_per_page = 36

    if test_only_mode:
        # shorter and faster list for testing only
        # disabling threading is used for debugging (fewer exceptions are raised if threads are used)
        threads = 0  # set to 0 to disable threading
        start_row = 15000
        stop_row = 15000 + rows_per_page
        clean_db = False
        load_data_from_files = False
    else:
        threads = 16
        start_row = 0
        stop_row = 0  # 0 means no limit
        clean_db = True
        load_data_from_files = False  # by default the scrapper will rebuild the database from scratch

    scraper = UEAssetScraper(
        start=start_row,
        stop=stop_row,
        assets_per_page=rows_per_page,
        max_threads=threads,
        store_in_db=True,
        store_in_files=not load_data_from_files,
        store_ids=False,
        load_from_files=load_data_from_files,
        clean_database=clean_db
    )
    scraper.save()
