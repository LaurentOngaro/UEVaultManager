# coding=utf-8
"""
implementation for:
- UEAsset:  A class to represent an Unreal Engine asset.
"""

from UEVaultManager.models.csv_sql_fields import get_default_value, get_sql_field_name_list
from UEVaultManager.tkgui.modules.functions_no_deps import check_and_convert_list_to_str
from UEVaultManager.utils.cli import init_dict_from_data


class UEAsset:
    """
    A class to represent an Unreal Engine asset. With the EGS data and user data.
    :param engine_version_for_obsolete_assets: engine version to use to check if an asset is obsolete.
    """

    # unused logger = logging.getLogger(__name__.split('.')[-1])  # keep only the class name
    # unused update_loggers_level(logger)

    def __init__(self, engine_version_for_obsolete_assets: str = ''):
        if not engine_version_for_obsolete_assets:
            self.engine_version_for_obsolete_assets = '4.26'  # no access to the engine_version_for_obsolete_assets global settings here without importing its module
        else:
            self.engine_version_for_obsolete_assets = engine_version_for_obsolete_assets
        self._data = {}
        self.init_data()

    def __str__(self) -> str:
        """
        Return a string representation of the asset.
        :return: string representation of the asset.
        """
        return check_and_convert_list_to_str(str(value) for value in self._data.values())

    def init_data(self) -> None:
        """
        Initialize the EGS data dictionary.

        Notes:
            The keys of self.Data dict are initialized here.
        """
        data = {}
        for key in get_sql_field_name_list(include_asset_only=True):
            data[key] = get_default_value(sql_field_name=key)
        self._data = data

    def init_from_dict(self, data: dict = None) -> None:
        """
        Initialize the asset data from the given dictionaries.
        :param data: source dictionary for the EGS data.
        """
        if data:
            self.init_data()
            # copy all the keys from the data dict to the self.data dict
            init_dict_from_data(self._data, data)

    def init_from_list(self, data: list = None) -> None:
        """
        Initialize the asset data from the given lists.
        :param data: source list for the EGS data.
        """
        if data:
            self.init_data()
            # fill dictionary with the data from the list
            # Note: keep in mind that the order for the values of the list and must correspond to the order of the keys in self.data
            keys = self._data.keys()
            self._data = dict(zip(keys, data))

    def get_data(self) -> dict:
        """
        Return the asset data.
        :return: asset data.
        """
        return self._data

    def set_data(self, data: dict) -> None:
        """
        Set the asset data.
        :param data: asset data.
        """
        self._data = data

    def get(self, key: str, default=None):
        """
        Return the value of the given key.
        :param key: key to get the value from.
        :param default: default value to return if the key is not found.
        :return: value or the default value.
        """
        return self._data.get(key, default)

    def set(self, key: str, value):
        """
        Set the value of the given key.
        :param key: key to set the value to.
        :param value: value to set.
        """
        self._data[key] = value
