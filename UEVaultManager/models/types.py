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
        # NO !!! it will convert a category value in a list of chars
        # if self == self.LIST:
        #     return list(value)
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
    JSON_DECODE = 7  # json decoding error


class BooleanOperator(Enum):
    """
    Boolean operators for the filters.
    """
    AND = 0  # added to the previous filter with an & operator
    OR = 1  # added to the previous filter with an | operator
    NOT = 2  # added to the previous filter with a not operator
    ALL_AND = 3  # added to the all the previous filters with an & operator
    ALL_OR = 4  # added to the all the previous filters with an | operator
    ALL_NOT = 5  # added to the all the previous filters with a not operator

    @staticmethod
    def get_from_name(name: str) -> 'BooleanOperator':
        """
        Returns the BooleanOperator corresponding to the given name.
        :param name: name of the BooleanOperator.
        :return: the BooleanOperator corresponding to the given name.
        """
        for operator in BooleanOperator:
            if operator.name == name or operator == name:
                return operator
        raise ValueError(f"No BooleanOperator found with name '{name}'.")
