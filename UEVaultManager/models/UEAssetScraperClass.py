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
from UEVaultManager.tkgui.modules.functions_no_deps import check_and_get_folder
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience


class UEAssetScraper:
    """
    A class that handles scraping data from the Unreal Engine Marketplace.
    It saves the data in csv files and/or in a sqlite database
    """

    def __init__(self, start=0, count=100, sort_by='effectiveDate', sort_order='DESC', timeout=10.0, max_threads=8) -> None:
        """
        Initializes an instance of the AssetsParser class.

        :param start: An int representing the starting index for the data to retrieve. Defaults to 0.
        :param count: An int representing the number of items to retrieve per request. Defaults to 100.
        :param sort_by: A string representing the field to sort by. Defaults to 'effectiveDate'.
        :param sort_order: A string representing the sort order. Defaults to 'ASC'.
        :param timeout: A float representing the timeout for the requests. Defaults to 10.0.
        :param max_threads: An int representing the maximum number of threads to use. Defaults to 8. Set to 0 to disable multithreading.
        """
        self.start = start
        self.count = count
        self.sort_by = sort_by
        self.sort_order = sort_order
        self.last_updated_filename = 'last_updated.json'
        self.urls_list_filename = 'urls_list.txt'
        self.data_folder = os.path.join(gui_g.s.scraping_folder, 'assets', 'marketplace')
        self.max_threads = max_threads
        self.threads_count = 0

        self.files_count = 0
        self.assets_data = []  # the scraper assets_data. Increased on each call to get_data_from_url(). Could be huge !!
        self.assets_ids = []  # store IDs of all items
        self.urls = []  # list of all urls to scrap
        self.log = logging.getLogger('Scraper')
        self.log.setLevel(logging.INFO)
        self.egs = EPCAPI(timeout=timeout)
        self.log.info(f'UEAssetScraper initialized with max_threads= {max_threads}, start= {start}, count= {count}, sort_by= {sort_by}, sort_order= {sort_order}')

    def parse_data(self, json_data: dict = None) -> []:
        """
        Parses on or more asset data from the response of an url query.
        :param json_data: A dictionary containing the data to parse.
        :return: A list containing the parsed data.
        """
        content = []
        if json_data is None:
            return content
        for asset in json_data['data']['elements']:
            price = 0
            discount_price = 0
            discount_percentage = 0
            average_rating = 0
            rating_total = 0
            # category_slug = ''
            if asset["priceValue"] > 0:
                # tbh the logic here is flawed as hell lol. discount should only be set if there's a discount Epic wtf
                price = asset['priceValue'] if asset['priceValue'] == asset['discountPriceValue'] else asset['discountPriceValue']
                price /= 100  # price is in cents
                discount_percentage = asset['discountPercentage']
                discount_price = asset['discountPriceValue']
            if discount_price == 0:
                discount_price = price
            has_discount = price != discount_price
            # try:
            #     category_slug = asset["categories"][0]["path"].split('assets/')[1]
            # except (KeyError,IndexError):
            #     self.log.debug(f'No category_slug for {asset["title"]}')
            try:
                average_rating = asset['rating']['averageRating']
                rating_total = asset['rating']['total']
            except KeyError:
                self.log.debug(f'No rating for {asset["title"]}')
            # try:
            asset_dict = {
                'id': asset['id'],
                'namespace': asset['namespace'],
                'catalog_item_id': asset['catalogItemId'],
                'title': asset['title'],
                "category": asset['categories'][0]['name'],
                # 'category_slug': category_slug,
                'author': asset['seller']['name'],
                'thumbnail_url': asset['thumbnail'],
                'current_price_discounted': has_discount,
                'asset_slug': asset['urlSlug'],
                'currency_code': asset['currencyCode'],
                'description': asset['description'],
                'technical_details': asset['technicalDetails'],
                'long_description': asset['longDescription'],
                'categories': asset['categories'],
                'tags': asset['tags'],
                'comment_rating_id': asset['commentRatingId'],
                'rating_id': asset['ratingId'],
                'status': asset['status'],
                'price': price,
                'discount': asset['discount'],
                # 'discount_price':asset['discountPrice'],
                # 'discount_price_value':asset[ 'discountPriceValue'],
                'discount_price': discount_price,
                # 'voucher_discount':asset[ 'voucherDiscount'],
                'discount_percentage': discount_percentage,
                'is_featured': asset['isFeatured'],
                'is_catalog_item': asset['isCatalogItem'],
                'is_new': asset['isNew'],
                'free': asset['free'],
                'discounted': asset['discounted'],
                'can_purchase': asset['canPurchase'],
                'owned': asset['owned'],
                'review': average_rating,
                'review_count': rating_total
            }
            content.append(asset_dict)
            self.assets_ids.append(asset['id'])
            # except (Exception, KeyError) as error:
            #     self.log.warning(f'Content parsing failed for {asset["title"]}:error {error!r}')
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
        self.log.info(f'It took {(time.time() - start_time):.3f} seconds to gather {len(self.urls)} urls')
        if save_result:
            self.save_to_file(filename=self.urls_list_filename, data=self.urls, is_json=False)

    def get_data_from_url(self, url='') -> None:
        """
        Grabs the data from the given url and stores it in the assets_data property.
        :param url: The url to grab the data from. If not given, uses the url property of the class.
        """
        if not url:
            url = self.egs.get_scrap_url(self.start, self.count, self.sort_by, self.sort_order)
        self.log.info(f'Parsing url {url}')
        json_data = self.egs.get_scrapped_assets(url)
        if json_data:
            content = self.parse_data(json_data)
            self.assets_data.append(content)
        if self.threads_count > 1:
            # add a delay when multiple threads are used
            time.sleep(random.uniform(1.0, 3.0))

    def download_assets_data(self) -> None:
        """
        Downloads the items from the URLs gathered by gather_urls() and stores them in the assets_data property.
        The execution is done in parallel using threads.
        """
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
            self.log.debug(f'Data saved into {filename}')
            return True
        except PermissionError as error:
            self.log.warning(f'The following error occured when saving data into {filename}:{error!r}')
            return False

    def save_all_to_files(self, save_ids=False) -> None:
        """
        Saves all JSON data retrieved from the Unreal Engine Marketplace API to paginated files.
        :param save_ids: A boolean indicating whether to store the store IDs extracted from the data in the self.tems_ids. Defaults to False. Could be time and memory consuming.
        """

        start_time = time.time()
        self.download_assets_data()
        self.log.info(f'It took {(time.time() - start_time):.3f} seconds to download assets for {len(self.urls)} urls')

        start_time = time.time()
        # format the list to be 1 long list rather than multiple lists nested in a list - [['1'], ['2'], ...] -> ['1','2', ...]
        new_content = list(chain.from_iterable(self.assets_data))
        self.files_count = 0
        for asset in new_content:
            asset_id = asset['id']
            self.save_to_file(filename=f'asset_{asset_id}.json', data=asset)
            self.files_count += 1
        self.log.info(f'It took {(time.time() - start_time):.3f} seconds to save the data')

        filename = os.path.join(self.data_folder, self.last_updated_filename)
        content = {'last_updated': str(datetime.datetime.now()), 'files_count': self.files_count, 'items_count': len(new_content)}
        if save_ids:
            content['items_ids'] = self.assets_ids
        with open(filename, 'w') as fh:
            json.dump(content, fh)


if __name__ == '__main__':
    row_per_page = 36
    scraper = UEAssetScraper(count=row_per_page)
    # scraper = UEAssetScraper(start=33500, count=row_per_page, max_threads=0)  # shorter list for testing only
    scraper.gather_urls(empty_list_before=True)
    scraper.save_all_to_files(save_ids=True)
