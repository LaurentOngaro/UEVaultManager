# coding=utf-8
"""
implementation for:
- UEAsset:  A class to represent an Unreal Engine asset.
"""

from UEVaultManager.models.csv_sql_fields import get_default_value, get_sql_field_name_list
from UEVaultManager.utils.cli import init_dict_from_data


class UEAsset:
    """
    A class to represent an Unreal Engine asset. With the EGS data and user data.
    :param engine_version_for_obsolete_assets: the engine version to use to check if an asset is obsolete.
    """
    # unused logger = logging.getLogger(__name__.split('.')[-1])  # keep only the class name
    # unused update_loggers_level(logger)

    def __init__(self, engine_version_for_obsolete_assets: str = ''):
        if not engine_version_for_obsolete_assets:
            self.engine_version_for_obsolete_assets = '4.26'  # no access to the engine_version_for_obsolete_assets global settings here without importing its module
        else:
            self.engine_version_for_obsolete_assets = engine_version_for_obsolete_assets
        self.data = {}
        self.init_data()

    def __str__(self) -> str:
        """
        Return a string representation of the asset.
        :return: a string representation of the asset.
        """
        return ','.join(str(value) for value in self.data.values())

    def init_data(self) -> None:
        """
        Initialize the EGS data dictionary.

        Notes:
            The keys of self.Data dict are initialized here.
        """
        data = {}
        for key in get_sql_field_name_list(include_asset_only=True):
            data[key] = get_default_value(sql_field_name=key)
        self.data = data

    def init_from_dict(self, data: dict = None) -> None:
        """
        Initialize the asset data from the given dictionaries.
        :param data: source dictionary for the EGS data.
        """
        if data:
            self.init_data()
            # copy all the keys from the data dict to the self.data dict
            init_dict_from_data(self.data, data)

    def init_from_list(self, data: list = None) -> None:
        """
        Initialize the asset data from the given lists.
        :param data: source list for the EGS data.
        """
        if data:
            self.init_data()
            # fill dictionary with the data from the list
            # Note: keep in mind that the order for the values of the list and must correspond to the order of the keys in self.data
            keys = self.data.keys()
            self.data = dict(zip(keys, data))
