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
from UEVaultManager.api.egs import EPCAPI, GrabResult
from UEVaultManager.core import default_datetime_format
from UEVaultManager.models.UEAssetClass import UEAsset, UEAssetDbHandler
from UEVaultManager.tkgui.modules.functions_no_deps import check_and_get_folder


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
        clean_database=False
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

        self.last_run_filename = 'last_run.json'
        self.urls_list_filename = 'urls_list.txt'
        self.data_folder = os.path.join(gui_g.s.scraping_folder, 'assets', 'marketplace')
        self.db_name = os.path.join(gui_g.s.scraping_folder, 'assets.db')
        self.max_threads = max_threads
        self.threads_count = 0

        self.files_count = 0
        self.scraped_data = []  # the scraper scraped_data. Increased on each call to get_data_from_url(). Could be huge !!
        self.scraped_ids = []  # store IDs of all items
        self.existing_data = {
        }  # dictionary {ids, rows} : the data in database before scraping. Contains only minimal information (user fields, id, price)

        self.urls = []  # list of all urls to scrap

        self.egs = EPCAPI(timeout=timeout)
        self.logger = logging.getLogger(__name__)
        self.asset_db_handler = UEAssetDbHandler(self.db_name)

        # self.logger.setLevel(logging.DEBUG)
        if self.load_from_files:
            self.store_in_files = False
            self.store_in_db = True
        message = f'UEAssetScraper initialized with max_threads= {max_threads}, start= {start}, stop= {stop}, assets_per_page= {assets_per_page}, sort_by= {sort_by}, sort_order= {sort_order}'
        message += f'\nData will be load from files in {self.data_folder}' if self.load_from_files else ''
        message += f'\nData will be saved in files in {self.data_folder}' if self.store_in_files else ''
        message += f'\nData will be saved in database in {self.db_name}' if self.store_in_db else ''
        message += f'\nAsset Ids will be saved in {self.last_run_filename} or in database' if self.store_ids else ''
        self.logger.info(message)

    def _parse_data(self, json_data: dict = None) -> []:
        """
        Parses on or more asset data from the response of an url query.
        :param json_data: A dictionary containing the data to parse.
        :return: A list containing the parsed data.
        """
        content = []
        no_text_data = ''

        if json_data is None:
            return content
        for asset_data in json_data['data']['elements']:
            # make some calculation to the "raw" data
            release_info = asset_data.get('releaseInfo', {})
            id = asset_data['id']
            existing_data = self.existing_data.get(id, None)
            price = 0
            discount_price = 0
            discount_percentage = 0
            average_rating = 0
            rating_total = 0
            # category_slug = ''
            if asset_data['priceValue'] > 0:
                # tbh the logic here is flawed as hell lol. discount should only be set if there's a discount Epic wtf
                price = asset_data['priceValue'] if asset_data['priceValue'] == asset_data['discountPriceValue'] else asset_data['discountPriceValue']
                price /= 100  # price is in cents
                discount_percentage = asset_data['discountPercentage']
                discount_price = asset_data['discountPriceValue']
            if discount_price == 0:
                discount_price = price
            current_price_discounted = price != discount_price
            try:
                average_rating = asset_data['rating']['averageRating']
                rating_total = asset_data['rating']['total']
            except KeyError:
                self.logger.debug(f'No rating for {asset_data["title"]}')
            asset_data['price'] = price
            asset_data['discount_price'] = discount_price
            asset_data['discount_percentage'] = discount_percentage
            asset_data['current_price_discounted'] = current_price_discounted
            asset_data['average_rating'] = average_rating
            asset_data['rating_total'] = rating_total
            asset_data['category'] = asset_data['categories'][0]['name']
            asset_data['author'] = asset_data['seller']['name']
            asset_data['asset_url'] = self.egs.get_asset_url(asset_data['urlSlug'])
            try:
                asset_data['asset_id'] = release_info[0]['appId']  # latest release
            except KeyError:
                asset_data['asset_id'] = id
            """
            CSV fields to add for comptility with UEVaultManager scrapper
            'Grab result': to set regarding scraping result
            OK 'Page title': extras_data['page_title']
            OK 'App name': same as asset_id
            OK 'Developer': asset_data['author'] 
            OK 'Supported versions': from Compatible versions
            OK 'Obsolete': calculated from "Supported versions" in cli.create_asset_from_data()
            OK 'Old price': calculated from "Price" in cli.create_asset_from_data()
            OK 'Url': extras_data['asset_url']
            OK 'Date added': calculated in cli.create_asset_from_data()  
            OK 'Update date': metadata['lastModifiedDate']  
            EMPTIED 'Compatible versions' 
            EMPTIED 'Creation date': metadata['creationDate']  
            EMPTIED 'UE version': item.app_version('Windows')  
            EMPTIED 'Uid': ?
            
            CSV output exemple
            {
            'Asset_id': 'ZombieAnc4dbb87c3f71V1',
            'App name': 'ZombieAnc4dbb87c3f71V1',
            'App title': 'Zombie Movement and Modular Interaction Animations',
            'Category': 'assets',
            'Review': 4.72,
            'Developer': 'ByteSumPi LTD',
            'Description': 'Zombie Animations and Modular Interactions',
            'Status': 'ACTIVE',
            'Discount price': 19.99,
            'Discount percentage': 0,
            'Discounted': False,
            'Owned': False,
            'Obsolete': False,
            'Supported versions': '',
            'Grab result': 'NO_ERROR',
            'Price': 19.99,
            'Old price': 0.0,
            'Comment': '',
            'Stars': 0.0, 
            'Must buy': False, 
            'Test result': '',
            'Installed folder': '',
            'Alternative': '',
            'Origin': 'Marketplace',
            'Page title': '',
            'Image': 'https://cdn1.epicgames.com/ue/product/Screenshot/Gallery31080x1920.PNG-1920x1080-aa1b1cb6f6e48ee03609d838c5b97cc1.jpg',
            'Url': 'https://www.unrealengine.com/marketplace/en-US/product/zombie-animations-and-modular-interactions',
            'Compatible versions': 'UE_4.26,UE_4.27,UE_5.0,UE_5.1,UE_5.2',
            'Date added': '2023-06-12 18:03:10',
            'Creation date': '2021-04-29T16:26:33.246Z',
            'Update date': '2023-05-12T23:18:26.721Z',
            'UE version': '4.23.0-17260714+++depot+UE4-UserContent-Windows',
            'Uid': 'c4dbb87c3f7146328957da3861ae63dd'
            }            
            """

            asset_data['page_title'] = asset_data['title']
            separator = ','
            try:
                tmp_list = [separator.join(item.get('compatibleApps')) for item in release_info]
                supported_versions = separator.join(tmp_list)
            except TypeError as error:
                self.logger.warning(f'Error getting compatibleApps for asset #{id} : {error!r}')
                supported_versions = no_text_data
            asset_data['supported_versions'] = supported_versions
            asset_data['origin'] = 'Marketplace'  # by default when scrapped from marketplace
            asset_data['obsolete'] = 0  # TODO: check if asset is obsolete see in cli.create_asset_from_data()
            asset_data['old_price'] = existing_data.get('old_price', 0) if existing_data else 0
            asset_data['creation_date'] = release_info[0].get('dateAdded', no_text_data) if release_info else no_text_data
            asset_data['update_date'] = datetime.now().strftime(default_datetime_format)
            asset_data['grab_result'] = GrabResult.NO_ERROR.name

            # not pertinent, kept for compatibility with CSV format. Could be removed later after checking usage
            # asset_data['app_name'] = asset_data['asset_id']
            # asset_data['developer'] = asset_data['author']
            # asset_data['compatible_versions'] = no_text_data
            # asset_data['creation_date'] = no_text_data
            # asset_data['ue_version'] = no_text_data
            # asset_data['uid'] = no_text_data

            ue_asset = UEAsset()
            ue_asset.init_from_dict(asset_data)
            content.append(ue_asset.data)
            self.scraped_ids.append(asset_data['id'])
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
            self.asset_db_handler.set_assets(self.scraped_data, update_user_fields=True)
        else:
            self.asset_db_handler.set_assets(self.scraped_data, update_user_fields=False)
        self.asset_db_handler.save_last_run(last_run_content)

    def gather_urls(self, empty_list_before=False, save_result=True) -> None:
        """
        Gathers all the URLs (with pagination) to be parsed and stores them in a list for further use.
        """
        if empty_list_before:
            self.urls = []
        start_time = time.time()
        if self.stop <= 0:
            self.stop = self.egs.get_scrapped_asset_count()
        assets_count = self.stop - self.start
        pages_count = int(assets_count / self.assets_per_page)
        if (assets_count % self.assets_per_page) > 0:
            pages_count += 1
        for i in range(int(pages_count)):
            start = self.start + (i * self.assets_per_page)
            url = self.egs.get_scrap_url(start, self.assets_per_page, self.sort_by, self.sort_order)
            self.urls.append(url)
        self.logger.info(f'It took {(time.time() - start_time):.3f} seconds to gather {len(self.urls)} urls')
        if save_result:
            self.save_to_file(filename=self.urls_list_filename, data=self.urls, is_json=False)

    def get_data_from_url(self, url='') -> None:
        """
        Grabs the data from the given url and stores it in the scraped_data property.
        :param url: The url to grab the data from. If not given, uses the url property of the class.
        """
        if not url:
            url = self.egs.get_scrap_url(self.start, self.assets_per_page, self.sort_by, self.sort_order)
        self.logger.info(f'Parsing url {url}')
        json_data = self.egs.get_scrapped_assets(url)
        if json_data:
            if self.store_in_files and self.use_raw_format:
                for asset_data in json_data['data']['elements']:
                    # store the data in a BEFORE parsing it
                    try:
                        app_id = asset_data['releaseInfo'][0]['appId']
                        filename = f'{app_id}.json'
                    except KeyError:
                        data_id = asset_data['id']
                        filename = f'_no_appId_asset_{data_id}.json'
                    self.save_to_file(filename=filename, data=asset_data)
                    self.files_count += 1
            content = self._parse_data(json_data)
            self.scraped_data.append(content)
        if self.threads_count > 1:
            # add a delay when multiple threads are used
            time.sleep(random.uniform(1.0, 3.0))

    def get_scraped_data(self) -> None:
        """
        Loads from files or downloads the items from the URLs and stores them in the scraped_data property.
        The execution is done in parallel using threads.
        Note: if self.urls is None or empty, gather_urls() will be called first.
        """
        # store exiting data in the existing_data property
        self.existing_data = self.asset_db_handler.get_assets_data(fields=self.asset_db_handler.user_fields)

        if self.load_from_files:
            self.load_from_json_files()
        else:
            start_time = time.time()
            if self.urls is None or len(self.urls) == 0:
                self.gather_urls()
            if self.max_threads > 0:
                self.threads_count = min(self.max_threads, len(self.urls))
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.threads_count) as executor:
                    executor.map(self.get_data_from_url, self.urls)
            else:
                for url in self.urls:
                    self.get_data_from_url(url)
            if self.store_in_files and self.use_raw_format:
                message = f'It took {(time.time() - start_time):.3f} seconds to download {len(self.urls)} urls and store the data in {self.files_count} files'
            else:
                message = f'It took {(time.time() - start_time):.3f} seconds to download {len(self.urls)} urls'
            self.logger.info(message)
            # format the list to be 1 long list rather than multiple lists nested in a list - [['1'], ['2'], ...] -> ['1','2', ...]
            self.scraped_data = list(chain.from_iterable(self.scraped_data))

    def save_to_file(self, prefix='assets', filename=None, data=None, is_json=True) -> bool:
        """
        Saves JSON data to a file.
        :param data: A dictionary containing the data to save. Defaults to None. If None, the data will be used.
        :param prefix: A string representing the prefix to use for the file name. Defaults to 'assets'.
        :param filename: A string representing the file name to use. Defaults to None. If None, a file name will be generated using the prefix and the start and count properties.
        :param is_json: A boolean indicating whether the data is JSON or not. Defaults to True.
        :return: A boolean indicating whether the file was saved successfully.
        """
        if data is None:
            data = self.scraped_data

        if data is None or len(data) == 0:
            self.logger.warning('No data to save')
            return False

        _, self.data_folder = check_and_get_folder(self.data_folder)
        if filename is None:
            filename = prefix
            if self.start > 0:
                filename += '_' + str(self.start)
                filename += '_' + str(self.start + self.assets_per_page)
            filename += '.json'
        filename = os.path.join(self.data_folder, filename)
        try:
            with open(filename, 'w') as fh:
                if is_json:
                    json.dump(data, fh)
                else:
                    # write data as a list in the file
                    fh.write('\n'.join(data))
            self.logger.debug(f'Data saved into {filename}')
            return True
        except PermissionError as error:
            self.logger.warning(f'The following error occured when saving data into {filename}:{error!r}')
            return False

    def load_from_json_files(self) -> None:
        """
        Load all JSON data retrieved from the Unreal Engine Marketplace API to paginated files.
        """
        start_time = time.time()
        self.files_count = 0
        self.scraped_ids = []
        self.scraped_data = []

        files = os.listdir(self.data_folder)
        files_count = len(files)
        # note: this data have the same structure as the table last_run inside the method UEAsset.create_tables()
        self.logger.info(f'Loading {files_count} files from {self.data_folder}')
        for filename in files:
            if filename.endswith('.json'):
                # self.logger.debug(f'Loading {filename}')
                with open(os.path.join(self.data_folder, filename), 'r') as fh:
                    json_data = json.load(fh)
                    asset_data = self._parse_data(json_data)
                    self.scraped_data.append(asset_data)
                    if self.store_ids:
                        self.scraped_ids.append(asset_data['id'])
                self.files_count += 1
        message = f'It took {(time.time() - start_time):.3f} seconds to load the data from {self.files_count} files'
        self.logger.info(message)

        # save results in the last_run file
        content = {
            'date': str(datetime.now()),
            'mode': 'load',
            'files_count': self.files_count,
            'items_count': len(self.scraped_data),
            'scrapped_ids': self.scraped_ids if self.store_ids else ''
        }

        filename = os.path.join(self.data_folder, self.last_run_filename)
        with open(filename, 'w') as fh:
            json.dump(content, fh)

        self._save_in_db(last_run_content=content)

    def save(self) -> None:
        """
        Saves all JSON data retrieved from the Unreal Engine Marketplace API to paginated files.
        """
        self.get_scraped_data()

        start_time = time.time()

        # note: this data have the same structure as the table last_run inside the method UEAsset.create_tables()
        content = {'date': str(datetime.now()), 'mode': 'save', 'files_count': 0, 'items_count': len(self.scraped_data), 'scrapped_ids': ''}

        if self.store_in_files and not self.use_raw_format:
            # store the data in a AFTER parsing it
            self.files_count = 0
            for asset in self.scraped_data:
                app_id = asset['releaseInfo']['appId']
                self.save_to_file(filename=f'{app_id}.json', data=asset)
                self.files_count += 1
            message = f'It took {(time.time() - start_time):.3f} seconds to save the data in {self.files_count} files'
            self.logger.info(message)

        # save results in the last_run file
        content['files_count'] = self.files_count
        content['scrapped_ids'] = self.scraped_ids if self.store_ids else ''

        filename = os.path.join(self.data_folder, self.last_run_filename)
        with open(filename, 'w') as fh:
            json.dump(content, fh)

        self._save_in_db(last_run_content=content)


if __name__ == '__main__':
    # the following code is just for class testing purposes

    # set the number of rows to retrieve per page
    # As the asset are saved individually by default, this value is only use for pagination in the files that store the url
    # it speeds up the process of requesting the asset list
    rows_per_page = 100

    testing = True
    # disable threading is used for debugging (fewer exceptions are raised if threads are used)

    if testing:
        # shorter and faster list for testing only
        threads = 0  # set to 0 to disable threading
        start_row = 15000
        stop_row = 15000 + rows_per_page
        clean_db = True
    else:
        threads = 160  # set to 0 to disable threading
        start_row = 0
        stop_row = 0  # 0 means no limit
        clean_db = False

    scraper = UEAssetScraper(
        start=start_row,
        stop=stop_row,
        assets_per_page=rows_per_page,
        max_threads=threads,
        store_in_db=True,
        store_in_files=True,
        store_ids=True,
        clean_database=clean_db
    )
    scraper.save()
