# coding=utf-8
"""
implementation for:
- UEAsset:  A class to represent an Unreal Engine asset
"""
import logging
import os

from UEVaultManager.models.UEAssetDbHandlerClass import UEAssetDbHandler
from UEVaultManager.tkgui.modules.functions_no_deps import path_from_relative_to_absolute
from UEVaultManager.utils.cli import init_dict_from_data, check_and_create_path


class UEAsset:
    """
    A class to represent an Unreal Engine asset. With the EGS data and user data.
    """

    def __init__(self):
        self.data = {}
        self.user_data = {}
        self.log = logging.getLogger('UEAsset')
        self.log.setLevel(logging.INFO)
        self.init_data()

    def init_data(self) -> None:
        """
        Initialize the EGS data dictionary.
        """
        self.data = {
            'id': None,
            'namespace': None,
            'catalog_item_id': None,
            'title': None,
            "category": None,
            # 'category_slug': None,
            'author': None,
            'thumbnail_url': None,
            'current_price_discounted': None,
            'asset_slug': None,
            'currency_code': None,
            'description': None,
            'technical_details': None,
            'long_description': None,
            'tags': None,
            'comment_rating_id': None,
            'rating_id': None,
            'status': None,
            'price': None,
            'discount': None,
            # 'discount_price':data['discountPrice'],
            # 'discount_price_value':data[ 'discountPriceValue'],
            'discount_price': None,
            # 'voucher_discount':data[ 'voucherDiscount'],
            'discount_percentage': None,
            'is_catalog_item': None,
            'is_new': None,
            'free': None,
            'discounted': None,
            'can_purchase': None,
            'owned': None,
            'review': None,
            'review_count': None,
            'asset_id': None,
            'asset_url': None,
            'comment': None,
            'stars': None,
            'must_buy': None,
            'test_result': None,
            'installed_folder': None,
            'alternative': None,
            'origin': None,
            'supported_versions': None,
            'creation_date': None,
            'update_date': None,
            'grab_result': None
        }

    def init_from_dict(self, data: dict = None) -> None:
        """
        Initialize the asset data from the given dictionaries.
        :param data: source dictionary for the EGS data
        """
        if data:
            self.init_data()
            # copy all the keys from the data dict to the self.data dict
            init_dict_from_data(self.data, data)
            self.convert_tag_list_to_string()

    def init_from_list(self, data: list = None) -> None:
        """
        Initialize the asset data from the given lists.
        :param data: source list for the EGS data
        """
        if data:
            # create empty dictionary
            self.init_data()
            # fill dictionary with data from list
            self.data = dict(zip(self.data.keys(), data))
            self.convert_tag_list_to_string()

    def convert_tag_list_to_string(self) -> None:
        """
        INPLACE Convert the tags id list of an asset_data dict to a string.
        """
        tags = self.data['tags']
        tags = [str(i) for i in tags]  # convert each item to a string, if not an error will be raised
        self.data['tags'] = ','.join(tags)


if __name__ == "__main__":
    # the following code is just for class testing purposes
    clean_data = True
    db_folder = path_from_relative_to_absolute('../../../scraping/')
    db_name = os.path.join(db_folder, 'assets.db')
    check_and_create_path(db_name)
    asset_handler = UEAssetDbHandler(database_name=db_name, reset_database=clean_data)
    rows_to_create = 300
    if clean_data:
        print(f"Deleting database")
        asset_handler.delete_all_assets()
    else:
        rows_count = asset_handler.get_row_count()
        print(f"Rows count: {rows_count}")
        rows_to_create -= rows_count
    print(f"Creating {rows_to_create} rows")
    asset_handler.generate_test_data(rows_to_create)

    # Read assets
    # asset_list = asset_handler.get_assets()
    # print("Assets:", asset_list)
