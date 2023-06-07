# coding=utf-8
"""
Implementation for:
- UEScraper: a class that handles scraping data from the Unreal Engine Marketplace.
"""
import concurrent.futures
import datetime
import json
import os
import random
import tempfile
import time
from itertools import chain
from urllib.request import urlopen

URL_MARKETPLACE = 'https://www.unrealengine.com/marketplace'
# URL_ASSET_LIST = 'https://www.unrealengine.com/marketplace/api/assets'
URL_ASSET_LIST = f'{URL_MARKETPLACE}/api/assets'
# URL_OWNED_ASSETS = 'https://www.unrealengine.com/marketplace/api/assets/vault'
URL_OWNED_ASSETS = f'{URL_ASSET_LIST}/vault'
# URL_ASSET = 'https://www.unrealengine.com/marketplace/api/assets/asset'
URL_ASSET = f'{URL_ASSET_LIST}/asset'
"""
exemples

page d'un asset avec son urlSlug
UE_MARKETPLACE/en-US/product/{jjd['urlSlug']}
https://www.unrealengine.com/marketplace/en-US/product/cloudy-dungeon

detail json d'un asset avec son id (et non pas son asset_id ou son catalog_id)
UE_ASSET/{el['id']}")
https://www.unrealengine.com/marketplace/api/assets/asset/5cb2a394d0c04e73891762be4cbd7216

liste json des reviews d'un asset avec son id
https://www.unrealengine.com/marketplace/api/review/4ede75b0f8424e37a92316e75bf64cae/reviews/list?start=0&count=10&sortBy=CREATEDAT&sortDir=DESC

liste json des questions d'un asset avec son id
https://www.unrealengine.com/marketplace/api/review/5cb2a394d0c04e73891762be4cbd7216/questions/list?start=0&count=10&sortBy=CREATEDAT&sortDir=DESC

"""


def log(message: str) -> None:
    """
    Logs a message to the console.

    :param message: The message to log.
    """
    print(message)


def check_folder(folder: str) -> None:
    """
    Checks if a folder exists. If it does not exist, creates the folder.

    :param folder: A string representing the name and location of the folder.
    """
    if not os.path.exists(folder):
        os.makedirs(folder)


class UEScraper:
    """
    A class that handles scraping data from the Unreal Engine Marketplace.
    It saves the data in csv files
    """

    def __init__(self, start=0, count=100, sort_by='effectiveDate', sort_order='DESC') -> None:
        """
        Initializes an instance of the AssetsParser class.

        :param start: An int representing the starting index for the data to retrieve. Defaults to 0.
        :param count: An int representing the number of items to retrieve per request. Defaults to 100.
        :param sort_by: A string representing the field to sort by. Defaults to 'effectiveDate'.
        :param sort_order: A string representing the sort order. Defaults to 'ASC'.
        """
        self.start = start
        self.count = count
        self.sort_by = sort_by
        self.sort_order = sort_order
        self.base_url = URL_ASSET_LIST
        self.last_updated_filename = 'last_updated.json'
        self.urls_list_filename = 'urls_list.txt'
        self.data_folder = os.path.join(tempfile.gettempdir(), 'UEScraper', 'marketplace')  # TODO: get it from the code base when integrated
        self.max_threads = 10  # TODO: get it from the code base when integrated
        self.threads_count = 0

        self.files_count = 0
        self.assets_data = []  # the scraper assets_data. Increased on each call to get_data_from_url(). Could be huge !!
        self.assets_ids = []  # store IDs of all items
        self.url = ''  # current url
        self.urls = []  # list of all urls to scrap

    def parse_data(self, response='') -> []:
        """
        Parses on or more asset data from the response of an url query.
        :param response: The response of an url query.
        :return: A list containing the parsed data.
        """
        if not response:
            return []
        json_data = json.loads(response)
        content = []
        for asset in json_data["data"]["elements"]:
            if asset["priceValue"] > 0:
                # tbh the logic here is flawed as hell lol. discount should only be set if there's a discount Epic wtf
                price = asset["priceValue"] if asset["priceValue"] == asset["discountPriceValue"] else asset["discountPriceValue"]
                has_discount = asset["priceValue"] != asset["discountPriceValue"]
                price /= 100  # price is in cents
            else:
                price = 0
                has_discount = False
            category_slug = asset["categories"][0]["path"].split('assets/')[1]
            content.append(
                [
                    {
                        'id': asset['id'],
                        'namespace': asset['namespace'],
                        'catalog_item_id': asset['catalogItemId'],
                        'title': asset['title'],
                        "category": asset['categories'][0]['name'],
                        'category_slug': category_slug,
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
                        'discount_price': asset['discountPriceValue'],
                        # 'voucher_discount':asset[ 'voucherDiscount'],
                        'discount_percentage': asset['discountPercentage'],
                        'is_featured': asset['isFeatured'],
                        'is_catalog_item': asset['isCatalogItem'],
                        'is_new': asset['isNew'],
                        'free': asset['free'],
                        'discounted': asset['discounted'],
                        'can_purchase': asset['canPurchase'],
                        'owned': asset['owned'],
                        'review': asset['rating']['averageRating'],
                        'review_count': asset['rating']['total']
                    }
                ]
            )
            self.assets_ids.append(asset['id'])
        return content

    def update_url(self) -> None:
        """
        Updates the URL with the current properties of the class (start, count, sort_by, sort_order).
        """
        self.url = f'{self.base_url}?start={self.start}&count={self.count}&sortBy={self.sort_by}&sortDir={self.sort_order}'

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

        check_folder(self.data_folder)
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
            log(f'Data saved into {filename}')
            return True
        except PermissionError as error:
            log(f'The following error occured when saving data into {filename}:{error!r}')
            return False

    def gather_urls(self, empty_list_before=False, save_result=True) -> None:
        """
        Gathers all the URLs (with pagination) to be parsed and stores them in a list for further use.
        """
        if empty_list_before:
            self.urls = []
        start_time = time.time()

        json_content = json.loads(urlopen(self.base_url).read())
        assets_count = json_content['data']['paging']['total']
        pages_count = int(assets_count / self.count)
        if (assets_count % self.count) > 0:
            pages_count += 1
        for i in range(int(pages_count)):
            self.start = i * self.count
            self.update_url()
            self.urls.append(self.url)
        log(f'It took {time.time() - start_time} seconds to gather {len(self.urls)} urls')
        if save_result:
            self.save_to_file(filename=self.urls_list_filename, data=self.urls, is_json=False)

    def get_data_from_url(self, url='') -> None:
        """
        Grabs the data from the given url and stores it in the assets_data property.
        :param url: The url to grab the data from. If not given, uses the url property of the class.
        """
        if not url:
            self.update_url()
            url = self.url
        log(f'Parsing url {url}')
        try:
            response = urlopen(url).read()
            if response.get('status') != 'OK':
                log(f'Error while reading url {url}')
                return
        except Exception as error:
            log(f'Error while reading url {url}: {error!r}')
            return
        self.assets_data.append(self.parse_data(response))
        if self.threads_count > 1:
            # add a delay when multiple threads are used
            time.sleep(random.uniform(1.0, 3.0))

    def download_assets_data(self) -> None:
        """
        Downloads the items from the URLs gathered by gather_urls() and stores them in the assets_data property.
        The execution is done in parallel using threads.
        """
        self.threads_count = min(self.max_threads, len(self.urls))
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.threads_count) as executor:
            executor.map(self.get_data_from_url, self.urls)

    def save_all(self, save_ids=False) -> None:
        """
        Saves all JSON data retrieved from the Unreal Engine Marketplace API to paginated files.
        :param save_ids: A boolean indicating whether to store the store IDs extracted from the data in the self.tems_ids. Defaults to False. Could be time and memory consuming.
        """

        start_time = time.time()
        self.download_assets_data()
        log(f'It took {start_time - time.time()} seconds to download assets for {len(self.urls)} urls')

        start_time = time.time()
        # format the list to be 1 long list rather than multiple lists nested in a list - [['1'], ['2'], ...] -> ['1','2', ...]
        new_content = list(chain.from_iterable(self.assets_data))
        self.files_count = 0
        for item in new_content:
            self.save_to_file(json.dumps(item))
            self.files_count += 1

        log(f'It took {start_time - time.time()} seconds to save the data')

        filename = os.path.join(self.data_folder, self.last_updated_filename)
        content = {'last_updated': str(datetime.datetime.now()), 'files_count': self.files_count, 'items_count': len(new_content)}
        if save_ids:
            content['items_ids'] = self.assets_ids
        with open(filename, 'w') as fh:
            json.dump(content, fh)


if __name__ == '__main__':
    row_per_page = 36  # TODO: get it from the code base when integrated
    scraper = UEScraper(count=row_per_page)
    # UEScraper(start=33400).save_all(save_ids=True)

    scraper.gather_urls(empty_list_before=True)
    scraper.save_all(save_ids=True)

    # this below is used to test the data that comes in on 1 page to avoid doing a ton of requests when testing

    # text = urlopen('https://www.unrealengine.com/marketplace/api/assets?count=100&sortBy=effectiveDate&sortDir=DESC&start=0').read()
    # parse_data(text)

    # new_content = list(chain.from_iterable(assets_data))
    # with open('yeeto.json', "w") as fh:
    #     fh.write(json.dumps(new_content))
