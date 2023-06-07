# coding=utf-8
from urllib.request import urlopen

import os
import tempfile
import json
import requests

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

details INTERESSANTS (pas tous affichés ici) du json renvoyé par UE_ASSET/{el['id']}
[
  {
    "id": "4ede75b0f8424e37a92316e75bf64cae",
    "catalogItemId": "20ad74585dae4eb18932545a7a147db3",
    "namespace": "ue",
    "title": "Cloudy Dungeon",
    "currencyCode": "EUR",
    "priceValue": 3919,
    "discountPriceValue": 3919,
    "voucherDiscount": 0,
    "discountPercentage": 100,
    "description": "Let\u2019s get started on your fantasy dungeon game with these low poly and hand-painted 3D assets",
    "technicalDetails": "Designed for Desktop and Mobile<br /><br />This pack use one textures atlas at 4094\u00d74096 pixel! <br />This CloudyDungeon set contains the following models: <br />- Two archways <br />- One door <br />- One entrance<br />- One exit <br />- Two Fences <br />- Three floors <br />- Eighteen walls pieces <br />- Ten pillars <br />- Fourteen stairs variability <br />- Two Towers variability <br />- Two Torchs variability <br />- Over ten sample moduals",
    "longDescription": "Let\u2019s get started on your fantasy dungeon game with these low poly and hand-painted 3D assets. Most elements here can be reshaped, re-arrange and assemble so quickly and easy to form a new Cloudy Dungeon. <br />",
    "isFeatured": false,
    "isCatalogItem": false,
    "categories": [{ "path": "assets/environments", "name": "Environments" }],
    "urlSlug": "cloudy-dungeon",
    "tags": [736, 10756, 37, 10757, 38, 136, 2984, 73, 52, 53, 22, 24, 344, 61],
    "commentRatingId": "20ad74585dae4eb18932545a7a147db3",
    "ratingId": "4ede75b0f8424e37a92316e75bf64cae",
    "isNew": false,
    "free": false,
    "discounted": false,
    "thumbnail": "https://cdn1.epicgames.com/ue/item/CloudyDungeon_Thumbnail_284-284x284-95bc56d92ccba709ca769e09076bc923.png",
    "status": "ACTIVE",
    "price": "\u20ac39.19",
    "discount": "\u20ac0.00",
    "discountPrice": "\u20ac39.19",
    "canPurchase": true,
    "owned": false,
    "rating": {
      "averageRating": 3.33,
      "total": 3,
    }
  }
]
"""

class VaultDataExtractor:
    """
    Extract data from the json dump of the vault
    NOT TESTED - FOR REFERENCE ONLY
    """
    def __int__(self):

        self.url_marketplace = "https://www.unrealengine.com/marketplace"
        self.data_folder = "./data"
        self.result_file = "mp_vault_list.md"

    def extract_data(self):
        """
        Extract data from the json dump of the vault
        """
        json_datas = []
        cost = 0.
        discount_price = 0.
        currency = ""
        count = 0
        for f in os.listdir(self.data_folder):
            if not f.endswith(".json"):
                continue
            with open(os.path.join(self.data_folder, f)) as fd:
                j = json.load(fd)
                count += len(j['data']['elements'])
                json_datas.append(j)

        with open(self.result_file, "w+") as fd:
            fd.write(f"# Vault content\n\n")
            i = 0
            for json_data in json_datas:
                for item in json_data['data']['elements']:
                    i += 1
                    print(f"\rProcessing Vault {i}/{count}", end="")
                    # The ID found in the json dump is completely valid, and we have to resolve it to the urlSlug if we want a nice and valid URL
                    with urlopen(f"{self.url_marketplace}/api/assets/asset/{item['id']}") as f:
                        asset = json.load(f)
                        asset_data = asset['data']['data']
                        fd.write(f"* [{asset_data['title']}]({self.url_marketplace}/en-US/product/{asset_data['urlSlug']})\n")
                        cost += asset_data['priceValue']
                        currency = asset_data['currencyCode']
                        try:
                            discount_price += asset_data['discountPriceValue']
                        except KeyError:
                            pass

            fd.write(f"\n# Vault stats\n\n")
            fd.write(f"* Value: {cost / 100}{currency}\n")
            fd.write(f"* Current cost: {discount_price / 100}{currency}\n")
            fd.write(f"* Size: {count}\n")


class AssetsParser:
    """
    A class that handles parsing data from the Unreal Engine Marketplace.
    """

    def __init__(self, start=0, count=100, sort_by='effectiveDate', sort_order='ASC') -> None:
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
        # 'id': '4ede75b0f8424e37a92316e75bf64cae'
        # catalogItemId': '20ad74585dae4eb18932545a7a147db3'
        # namespace': 'ue'
        # title': 'Cloudy Dungeon'
        # recurrence': 'ONCE'
        # currencyCode': 'EUR'
        # priceValue': 3919
        # discountPriceValue': 3919
        # voucherDiscount': 0
        # discountPercentage': 100
        # md5': 'f12f1d6a20f7487783e57714b541ca2b', 'width': 1920, 'height': 1080, 'size': 2432968, 'uploadedDate': '2014-10-24T20:52:55.556Z'}, {'type': 'Screenshot', 'url': 'https://cdn1.epicgames.com/ue/item/CloudyDungeon_Screenshot_02-1920x1080-bfd550127545b1e62a1acdd2d14aa4ee.png', 'md5': 'bfd550127545b1e62a1acdd2d14aa4ee', 'width': 1920, 'height': 1080, 'size': 2554882, 'uploadedDate': '2014-10-24T20:52:32.330Z'}, {'type': 'Screenshot', 'url': 'https://cdn1.epicgames.com/ue/item/CloudyDungeon_Screenshot_01-1920x1080-2f87b9944d4a69339f81207d37601e73.png', 'md5': '2f87b9944d4a69339f81207d37601e73', 'width': 1920, 'height': 1080, 'size': 2242966, 'uploadedDate': '2014-10-24T20:52:15.585Z'}, {'type': 'Screenshot', 'url': 'https://cdn1.epicgames.com/ue/item/CloudyDungeon_Screenshot_05-1920x1080-0dcd0cdeec0c2bf7d71d105d3660bd98.png', 'md5': '0dcd0cdeec0c2bf7d71d105d3660bd98', 'width': 1920, 'height': 1080, 'size': 2036785, 'uploadedDate': '2014-10-24T20:53:23.312Z'}, {'type': 'Thumbnail', 'url': 'https://cdn1.epicgames.com/ue/item/CloudyDungeon_Thumbnail_284-284x284-95bc56d92ccba709ca769e09076bc923.png', 'md5': '95bc56d92ccba709ca769e09076bc923', 'width': 284, 'height': 284, 'size': 245071, 'uploadedDate': '2015-03-06T21:50:56.327Z'}, {'type': 'Featured', 'url': 'https://cdn1.epicgames.com/ue/item/CloudyDungeon_Featured-476x246-3cd79bce9d45614d97017728d51020f8.png', 'md5': '3cd79bce9d45614d97017728d51020f8', 'width': 476, 'height': 246, 'size': 190724, 'uploadedDate': '2014-10-24T20:50:27.888Z'}, {'type': 'ComingSoon_Small', 'url': 'https://cdn1.epicgames.com/ue/item/CloudyDungeon_ComingSoon_Small-145x208-7d8059a6f56c9e3f9781f8866b29892a.png', 'md5': '7d8059a6f56c9e3f9781f8866b29892a', 'width': 145, 'height': 208, 'size': 123647, 'uploadedDate': '2014-10-24T20:51:23.745Z'}, {'type': 'ComingSoon', 'url': 'https://cdn1.epicgames.com/ue/item/CloudyDungeon_ComingSoon-394x208-fece0f4dd2ed26110ddc015b0b270373.png', 'md5': 'fece0f4dd2ed26110ddc015b0b270373', 'width': 394, 'height': 208, 'size': 330855, 'uploadedDate': '2014-10-24T20:50:49.125Z'}], 'viewableDate': '2014-03-01T00:00:00.000Z', 'effectiveDate': '2014-03-01T00:00:00.000Z', 'seller': {'id': 'o-2410dcb5284ea49cc3058400b1d699', 'noAi': False, 'owner': '0d601e7287254589bfa2a57e46e23ecc', 'status': 'ACTIVE', 'financeCheckExempted': False, 'name': '3dFancy'}, 'description': 'Let’s get started on your fantasy dungeon game with these low poly and hand-painted 3D assets', 'technicalDetails': 'Designed for Desktop and Mobile<br /><br />This pack use one textures atlas at 4094×4096 pixel! <br />This CloudyDungeon set contains the following models: <br />- Two archways <br />- One door <br />- One entrance<br />- One exit <br />- Two Fences <br />- Three floors <br />- Eighteen walls pieces <br />- Ten pillars <br />- Fourteen stairs variability <br />- Two Towers variability <br />- Two Torchs variability <br />- Over ten sample moduals', 'longDescription': 'Let’s get started on your fantasy dungeon game with these low poly and hand-painted 3D assets. Most elements here can be reshaped, re-arrange and assemble so quickly and easy to form a new Cloudy Dungeon. <br />', 'isFeatured': False, 'isCatalogItem': False, 'categories': [{'path': 'assets/environments', 'name': 'Environments'}], 'bundle': False, 'releaseInfo': [{'id': '1a02614c09cb4b5988358de4986857bf', 'appId': 'CloudyDungeon', 'compatibleApps': ['UE_4.0', 'UE_4.1', 'UE_4.2', 'UE_4.3', 'UE_4.4', 'UE_4.5', 'UE_4.6', 'UE_4.7', 'UE_4.8', 'UE_4.9', 'UE_4.10', 'UE_4.11', 'UE_4.12', 'UE_4.13', 'UE_4.14', 'UE_4.15', 'UE_4.16', 'UE_4.17', 'UE_4.18', 'UE_4.19', 'UE_4.20', 'UE_4.21', 'UE_4.22', 'UE_4.23', 'UE_4.24', 'UE_4.25', 'UE_4.26', 'UE_4.27'], 'platform': ['Windows', 'Mac', 'PS4', 'iOS', 'Android', 'Xbox One', 'Oculus'], 'dateAdded': '2014-10-13T00:00:00.000Z', 'versionTitle': 'CloudyDungeon'}], 'platforms': [{'key': 'windows', 'value': 'Windows 64-bit'}, {'key': 'apple', 'value': 'MacOS'}, {'key': 'laptop', 'value': 'Other'}, {'key': 'mobile', 'value': 'iOS'}, {'key': 'android', 'value': 'Android'}, {'key': 'eye', 'value': 'Oculus'}], 'compatibleApps': ['4.0', '4.1', '4.2', '4.3', '4.4', '4.5', '4.6', '4.7', '4.8', '4.9', '4.10', '4.11', '4.12', '4.13', '4.14', '4.15', '4.16', '4.17', '4.18', '4.19', '4.20', '4.21', '4.22', '4.23', '4.24', '4.25', '4.26', '4.27'], 'urlSlug': 'cloudy-dungeon', 'purchaseLimit': 1, 'tax': 0, 'tags': [736, 10756, 37, 10757, 38, 136, 2984, 73, 52, 53, 22, 24, 344, 61], 'commentRatingId': '20ad74585dae4eb18932545a7a147db3', 'ratingId': '4ede75b0f8424e37a92316e75bf64cae', 'klass': '', 'isNew': False, 'free': False, 'discounted': False, 'featured': 'https://cdn1.epicgames.com/ue/item/CloudyDungeon_Featured-476x246-3cd79bce9d45614d97017728d51020f8.png', 'thumbnail': 'https://cdn1.epicgames.com/ue/item/CloudyDungeon_Thumbnail_284-284x284-95bc56d92ccba709ca769e09076bc923.png', 'learnThumbnail': 'https://cdn1.epicgames.com/ue/item/CloudyDungeon_Featured-476x246-3cd79bce9d45614d97017728d51020f8.png', 'headerImage': 'https://cdn1.epicgames.com/ue/item/CloudyDungeon_Screenshot_04-1920x1080-5e3df75b1ca284353e05fd0c0439aadb.png', 'status': 'ACTIVE', 'price': '€39.19', 'discount': '€0.00', 'discountPrice': '€39.19', 'ownedCount': 0, 'canPurchase': True, 'owned': False, 'rating': {'targetId': '4ede75b0f8424e37a92316e75bf64cae', 'averageRating': 3.33, 'rating5': 1, 'rating4': 1, 'rating3': 0, 'rating2': 0, 'rating1': 1, 'legacyRatingNum': 3, 'total': 3, 'rating5Percent': 33.33, 'rating4Percent': 33.33, 'rating3Percent': 0, 'rating2Percent': 0, 'rating1Percent': 33.33}}
        self.base_url = 'https://www.unrealengine.com/marketplace/api/assets'
        self.save_folder = os.path.join(tempfile.gettempdir(), 'assets_parser_files')

        self.items_count = 0
        self.files_count = 0
        self.latest_data = {}  # latest retrieved data
        self.items_ids = []  # store IDs of all items
        self.url = ''

    def update_url(self) -> None:
        """
        Updates the URL with the current properties of the class (start, count, sort_by, sort_order).

        """
        self.url = f'{self.base_url}?start={self.start}&count={self.count}&sortBy={self.sort_by}&sortDir={self.sort_order}'

    def save_to_file(self, prefix='assets', json_data=None) -> bool:
        """
        Saves JSON data to a file.

        :param json_data: A dictionary containing the JSON data to save. Defaults to None. If None, the data will be used.
        :param prefix: A string representing the prefix to use for the file name. Defaults to 'assets'.
        :return: A boolean indicating whether the file was saved successfully.
        """
        if json_data is None:
            json_data = self.get_data_from_url()

        check_folder(self.save_folder)
        file_name = prefix
        if self.start > 0:
            file_name += '_' + str(self.start)
            file_name += '_' + str(self.start + self.count)
        file_name += '.json'
        file_name = os.path.join(self.save_folder, file_name)
        try:
            with open(file_name, 'w') as f:
                json.dump(json_data, f)
            log(f"Data saved into {file_name}")
            return True
        except PermissionError as error:
            log(f"Error: permission denied:{error!r}")
            return False

    def get_data_from_url(self) -> dict:
        """
        Retrieves JSON data from the Unreal Engine Marketplace API using the current properties of the class (url, start, count).

        :return: A dictionary containing the JSON data.
        """
        self.update_url()
        items = {}
        try:
            response = requests.get(self.url)
            json_data = response.json()
            items = json_data['data']['elements']
            self.latest_data = items
        except Exception as e:
            print(e)
        return items

    def save_all(self, save_ids=False) -> None:
        """
        Saves all JSON data retrieved from the Unreal Engine Marketplace API to individual files.
        :param save_ids: A boolean indicating whether to store the store IDs extracted from the data in the self.tems_ids. Defaults to False. Could be time and memory consuming.
        """
        self.files_count = 0
        self.items_count = 0
        while True:
            self.update_url()
            data = self.get_data_from_url()
            count = len(data)
            if count <= 0:
                break
            self.save_to_file(json_data=data)
            self.start += self.count
            self.items_count += count
            self.files_count += 1
            if save_ids:
                self.items_ids.extend([item['id'] for item in data])
        log(f"Saved {self.files_count} files to {self.save_folder}")
        if len(self.items_ids):
            data = {'assets_count': self.items_count, 'asset_ids': self.items_ids}
            self.save_to_file(prefix='assets_ids', json_data=data)


if __name__ == '__main__':
    AssetsParser(start=0, count=1).save_to_file(prefix='first_row_only')
    AssetsParser(start=33400).save_all(save_ids=True)
