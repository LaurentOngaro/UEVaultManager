# coding=utf-8
"""
implementation for:
- UEAsset:  A class to represent an Unreal Engine asset
"""
import logging
from UEVaultManager.utils.cli import init_dict_from_data


class UEAsset:
    """
    A class to represent an Unreal Engine asset. With the EGS data and user data.
    :param engine_version_for_obsolete_assets: The engine version to use to check if an asset is obsolete
    """

    def __init__(self, engine_version_for_obsolete_assets: str = '4.26'):
        self.engine_version_for_obsolete_assets = engine_version_for_obsolete_assets
        self.data = {}
        self.user_data = {}
        self.log = logging.getLogger('UEAsset')
        self.log.setLevel(logging.INFO)
        self.init_data()

    def init_data(self) -> None:
        """
        Initialize the EGS data dictionary.
        Note: the keys of self.user_data dict are initialized here
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
            'page_title': None,
            'obsolete': None,
            'supported_versions': None,
            'creation_date': None,
            'update_date': None,
            'date_added_in_db': None,
            'grab_result': None,
            'old_price': None

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
