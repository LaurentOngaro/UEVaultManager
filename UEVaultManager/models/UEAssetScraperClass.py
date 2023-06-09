# coding=utf-8
"""
Implementation for:
- UEAssetScraper: a class that handles scraping data from the Unreal Engine Marketplace.
"""
import concurrent.futures
import datetime
import json
import logging
import os
import random
import time
from itertools import chain

from UEVaultManager.api.egs import EPCAPI
from UEVaultManager.models.UEAssetClass import UEAsset, UEAssetDbHandler
from UEVaultManager.tkgui.modules.functions_no_deps import check_and_get_folder
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience


class UEAssetScraper:
    """
    A class that handles scraping data from the Unreal Engine Marketplace.
    It saves the data in csv files and/or in a sqlite database
    """

    def __init__(
        self,
        start=0,
        count=100,
        sort_by='effectiveDate',
        sort_order='DESC',
        timeout=10.0,
        max_threads=8,
        store_in_files=True,
        store_in_db=True,
        store_ids=False
    ) -> None:
        """
        Initializes an instance of the AssetsParser class.
        :param start: An int representing the starting index for the data to retrieve. Defaults to 0.
        :param count: An int representing the number of items to retrieve per request. Defaults to 100.
        :param sort_by: A string representing the field to sort by. Defaults to 'effectiveDate'.
        :param sort_order: A string representing the sort order. Defaults to 'ASC'.
        :param timeout: A float representing the timeout for the requests. Defaults to 10.0.
        :param max_threads: An int representing the maximum number of threads to use. Defaults to 8. Set to 0 to disable multithreading.
        :param store_in_files: A boolean indicating whether to store the data in csv files. Defaults to True. Could create lots of files (1 file per asset)
        :param store_in_db: A boolean indicating whether to store the data in a sqlite database. Defaults to True.
        :param store_ids: A boolean indicating whether to store and save the IDs of the assets. Defaults to False. Could be memory consuming.
        """
        self.start = start
        self.count = count
        self.sort_by = sort_by
        self.sort_order = sort_order
        self.store_in_files = store_in_files
        self.store_in_db = store_in_db
        self.store_ids = store_ids
        self.last_run_filename = 'last_run.json'
        self.urls_list_filename = 'urls_list.txt'
        self.data_folder = os.path.join(gui_g.s.scraping_folder, 'assets', 'marketplace')
        self.db_name = os.path.join(gui_g.s.scraping_folder, 'assets.db')
        self.max_threads = max_threads
        self.threads_count = 0

        self.files_count = 0
        self.assets_data = []  # the scraper assets_data. Increased on each call to get_data_from_url(). Could be huge !!
        self.assets_ids = []  # store IDs of all items
        self.urls = []  # list of all urls to scrap
        self.egs = EPCAPI(timeout=timeout)
        self.logger = logging.getLogger(__name__)
        # self.logger.setLevel(logging.DEBUG)
        message = f'UEAssetScraper initialized with max_threads= {max_threads}, start= {start}, count= {count}, sort_by= {sort_by}, sort_order= {sort_order}'
        message += f'\nData will be saved in files in {self.data_folder}' if store_in_files else ''
        message += f'\nData will be saved in database in {self.db_name}' if store_in_db else ''
        message += f'\nAsset Ids will be saved in {self.last_run_filename} or in database' if store_ids else ''
        self.logger.info(message)

    def _parse_data(self, json_data: dict = None) -> []:
        """
        Parses on or more asset data from the response of an url query.
        :param json_data: A dictionary containing the data to parse.
        :return: A list containing the parsed data.
        """
        content = []
        if json_data is None:
            return content
        for asset_data in json_data['data']['elements']:
            # make some calculation to the "raw" data
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
            # try:
            #     category_slug = asset_data["categories"][0]["path"].split('asset_datas/')[1]
            # except (KeyError,IndexError):
            #     self.logger.debug(f'No category_slug for {asset_data["title"]}')
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
            # asset_data['category_slug'] = category_slug

            ue_asset = UEAsset()
            ue_asset.init_from_dict(asset_data)
            content.append(ue_asset.data)
            self.assets_ids.append(asset_data['id'])
        return content

    def gather_urls(self, empty_list_before=False, save_result=True) -> None:
        """
        Gathers all the URLs (with pagination) to be parsed and stores them in a list for further use.
        """
        if empty_list_before:
            self.urls = []
        start_time = time.time()

        assets_count = self.egs.get_scrapped_asset_count() - self.start
        pages_count = int(assets_count / self.count)
        if (assets_count % self.count) > 0:
            pages_count += 1
        for i in range(int(pages_count)):
            start = self.start + (i * self.count)
            url = self.egs.get_scrap_url(start, self.count, self.sort_by, self.sort_order)
            self.urls.append(url)
        self.logger.info(f'It took {(time.time() - start_time):.3f} seconds to gather {len(self.urls)} urls')
        if save_result:
            self.save_to_file(filename=self.urls_list_filename, data=self.urls, is_json=False)

    def get_data_from_url(self, url='') -> None:
        """
        Grabs the data from the given url and stores it in the assets_data property.
        :param url: The url to grab the data from. If not given, uses the url property of the class.
        """
        if not url:
            url = self.egs.get_scrap_url(self.start, self.count, self.sort_by, self.sort_order)
        self.logger.info(f'Parsing url {url}')
        json_data = self.egs.get_scrapped_assets(url)
        if json_data:
            content = self._parse_data(json_data)
            self.assets_data.append(content)
        if self.threads_count > 1:
            # add a delay when multiple threads are used
            time.sleep(random.uniform(1.0, 3.0))

    def download_assets_data(self) -> None:
        """
        Downloads the items from the URLs gathered by gather_urls() and stores them in the assets_data property.
        The execution is done in parallel using threads.
        Note: if self.urls is None or empty, gather_urls() will be called first.
        """
        if self.urls is None or len(self.urls) == 0:
            self.gather_urls()
        if self.max_threads > 0:
            self.threads_count = min(self.max_threads, len(self.urls))
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.threads_count) as executor:
                executor.map(self.get_data_from_url, self.urls)
        else:
            for url in self.urls:
                self.get_data_from_url(url)

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
            data = self.assets_data

        if data is None or len(data) == 0:
            self.logger.warning('No data to save')
            return False

        _, self.data_folder = check_and_get_folder(self.data_folder)
        if filename is None:
            filename = prefix
            if self.start > 0:
                filename += '_' + str(self.start)
                filename += '_' + str(self.start + self.count)
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

    def save(self, save_ids=False, clean_database=False) -> None:
        """
        Saves all JSON data retrieved from the Unreal Engine Marketplace API to paginated files.
        :param save_ids: A boolean indicating whether to store the store IDs extracted from the data in the self.tems_ids. Defaults to False. Could be time and memory consuming.
        :param clean_database: A boolean indicating whether to clean the database before saving the data. Defaults to False.
        """
        start_time = time.time()
        self.download_assets_data()
        self.logger.info(f'It took {(time.time() - start_time):.3f} seconds to download assets for {len(self.urls)} urls')

        start_time = time.time()
        # format the list to be 1 long list rather than multiple lists nested in a list - [['1'], ['2'], ...] -> ['1','2', ...]
        assets_list = list(chain.from_iterable(self.assets_data))
        self.files_count = 0

        # note: this data have the same structure as the table last_run inside the method UEAsset.create_tables()
        content = {'date': str(datetime.datetime.now()), 'files_count': self.files_count, 'items_count': len(assets_list), 'items_ids': ''}

        if self.store_in_files:
            for asset in assets_list:
                asset_id = asset['id']
                self.save_to_file(filename=f'asset_{asset_id}.json', data=asset)
                self.files_count += 1
            self.logger.info(f'It took {(time.time() - start_time):.3f} seconds to save the data in files')
            # save results in the last_run file
            content['files_count'] = self.files_count
            content['items_ids'] = self.assets_ids if save_ids else ''

            filename = os.path.join(self.data_folder, self.last_run_filename)
            with open(filename, 'w') as fh:
                json.dump(content, fh)

        if self.store_in_db:
            content['items_ids'] = ','.join(self.assets_ids) if save_ids else ''
            asset_db_handler = UEAssetDbHandler(self.db_name)
            if clean_database:
                # next line will delete all assets in the database
                asset_db_handler.delete_all_assets()
                asset_db_handler.set_assets(assets_list, update_user_fields=True)
            else:
                asset_db_handler.set_assets(assets_list, update_user_fields=False)
            asset_db_handler.save_last_run(content)


if __name__ == '__main__':
    # the following code is just for class testing purposes
    row_per_page = 36
    testing = True

    if testing:
        # shorter and faster list for testing only
        # scraper = UEAssetScraper(start=33500, count=row_per_page, max_threads=0) # for thread debugging (fewer exceptions are raised if threads are used)
        scraper = UEAssetScraper(start=33500, count=row_per_page)
        scraper.save(save_ids=True, clean_database=False)
    else:
        scraper = UEAssetScraper(count=row_per_page, store_in_db=True, store_in_files=True, store_ids=True)
        scraper.save(save_ids=True, clean_database=True)
