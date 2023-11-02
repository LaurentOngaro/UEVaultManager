# coding=utf-8
"""
Definition for the types used in this module:
- CSVFieldState: Enum for the state of a field in the database
- CSVFieldType: Enum for the (simplified) type of field in the database
- DbVersionNum: version of the database or/and class.
"""
import datetime
from enum import Enum

from UEVaultManager.tkgui.modules.functions_no_deps import convert_to_bool, convert_to_datetime, convert_to_float, convert_to_int


class DateFormat:
    """
    for the date format.
    """
    csv: str = '%Y-%m-%d %H:%M:%S'
    epic: str = '%Y-%m-%dT%H:%M:%S.%fZ'
    us_short: str = '%Y-%m-%d'
    file_suffix: str = '%Y-%m-%d_%H-%M-%S'


class CSVFieldState(Enum):
    """
    Enum for the state of a field in the database
    Used for filtering the fields regarding the context.
    """
    NORMAL = 1  # field will NOT be preserved if already present in data (CSV file or database)
    CHANGED = 2  # field is changed during the process. Will be preserved if already present in data (CSV file or database)
    USER = 3  # field is only in the user data. Will be preserved if already present in data (CSV file or database)
    ASSET_ONLY = 4  # field is only in the property of the UEAsset class


class CSVFieldType(Enum):
    """
    Enum for the (simplified) type of field in the database
    Used for selecting the good format and/or control to show the value.
    """
    STR = 0  # short text (ie ttk.ENTRY)
    INT = 1
    FLOAT = 2
    BOOL = 3
    TEXT = 4  # long text (ie ttk.TEXT)
    DATETIME = 5  # date and time (see ttkbootstrap.widgets.DateEntry)
    LIST = 6  # list of values (ie ttk.DROPBOX)

    def cast(self, value):
        """
        Cast the value to the type of the field.
        :param value: value to cast.
        :return: value with the cast type.
        """
        if self == self.INT:
            return convert_to_int(value)
        if self == self.FLOAT:
            return convert_to_float(value)
        if self == self.BOOL:
            return convert_to_bool(value)
        if self == self.DATETIME:
            return convert_to_datetime(value, formats_to_use=[DateFormat.epic, DateFormat.csv])
        if self == self.LIST:
            return list(value)
        return str(value)

    def cast_to_type(self):
        """
        Cast the type of the field to a python type.
        :return: python type.
        """
        if self == self.INT:
            return int
        if self == self.FLOAT:
            return float
        if self == self.BOOL:
            return bool
        if self == self.DATETIME:
            return datetime
        if self == self.LIST:
            return list
        else:
            return str


class DbVersionNum(Enum):
    """
    The version of the database or/and class.
    Used when checking if database must be upgraded by comparing with the class version.
    """
    # when a new version is added to the DbVersionNum enum
    # - add code for the new version to the create_tables() method
    # - add code for the new version check to the check_and_upgrade_database() method
    V0 = 0  # invalid version
    V1 = 1  # initial version : only the "standard" marketplace columns
    V2 = 2  # add the columns used fo user data to the "standard" marketplace columns
    V3 = 3  # add the last_run table to get data about the last run of the application
    V4 = 4  # add custom_attributes field to the assets table
    V5 = 5  # add added_manually column to the assets table
    V6 = 6  # add tags column to the assets table
    V7 = 7  # add the tags table
    V8 = 8  # add the ratings tags table
    V9 = 9  # create the "assets_tags" view for the tags in the assets table
    V10 = 10  # add an autoincrement id to the last_run table
    V11 = 11  # rename column installed_folder TO installed_folders
    V12 = 12  # add release_info columns to the assets table
    V13 = 13  # add downloaded_size columns to the assets table
    V14 = 14  # add categories et grab_result views
    V15 = 15  # future version


class GetDataResult(Enum):
    """
    Result of the get_data_from_url() function.
    """
    OK = 0
    ERROR = 1
    CANCELLED = 2  # user cancelled the process
    BAD_CONTEXT = 3  # the context is not valid getting data (i.e. offine)
    NO_URL = 4  # no url to get data
    ERROR_431 = 5  # mainly occurs because the number of asset to scrap is too big
    TIMEOUT = 6  # mainly occurs because the timeout is too short for the number of asset to scrap
