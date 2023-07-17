# coding=utf-8
"""
implementation for:
- UEAsset:  A class to represent an Unreal Engine asset
"""
import logging

from UEVaultManager.models.csv_sql_fields import get_sql_field_name_list, get_default_value
from UEVaultManager.utils.cli import init_dict_from_data


class UEAsset:
    """
    A class to represent an Unreal Engine asset. With the EGS data and user data.
    :param engine_version_for_obsolete_assets: The engine version to use to check if an asset is obsolete
    """

    def __init__(self, engine_version_for_obsolete_assets=None):
        if engine_version_for_obsolete_assets is None:
            self.engine_version_for_obsolete_assets = '4.26'  # no access to the engine_version_for_obsolete_assets global settings here without importing its module
        else:
            self.engine_version_for_obsolete_assets = engine_version_for_obsolete_assets
        self.data = {}
        self.log = logging.getLogger('UEAsset')
        self.log.setLevel(logging.INFO)
        self.init_data()

    def __str__(self) -> str:
        """
        Return a string representation of the asset.
        :return: A string representation of the asset.
        """
        return ','.join(str(value) for value in self.data.values())

    def init_data(self) -> None:
        """
        Initialize the EGS data dictionary.

        Note: the keys of self.Data dict are initialized here
        """
        data = {}
        for key in get_sql_field_name_list(include_asset_only=True):
            data[key] = get_default_value(sql_field_name=key)
        self.data = data

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
            self.init_data()
            # fill dictionary with the data from the list
            # Note: keep in mind that the order for the values of the list and must correspond to the order of the keys in self.data
            keys = self.data.keys()
            self.data = dict(zip(keys, data))
            self.convert_tag_list_to_string()

    def convert_tag_list_to_string(self) -> None:
        """
        INPLACE Convert the tags id list of an asset_data dict to a string.
        """
        tags = self.data.get('tags', None)
        if not tags or tags == [] or tags == {}:
            tags = ''
        else:
            # TODO : find to get the value associated to each tag id. Not sure, it's possible using the API
            tags = [str(i) for i in tags]  # convert each item to a string, if not an error will be raised when joining
            tags = ','.join(tags)
        self.data['tags'] = tags
        # print(f"{self.data['asset_id']} tags converted: {tags}") # debug only
