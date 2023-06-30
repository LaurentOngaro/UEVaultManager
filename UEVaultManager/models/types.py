# coding=utf-8
"""
Definition for the types used in this module:
- CSVFieldState: Enum for the state of a field in the database
- CSVFieldType: Enum for the (simplified) type of field in the database
- DbVersionNum: The version of the database or/and class.
"""
from enum import Enum

from UEVaultManager.tkgui.modules import globals as gui_g
from UEVaultManager.tkgui.modules.functions_no_deps import convert_to_int, convert_to_float, convert_to_bool, convert_to_datetime


class CSVFieldState(Enum):
    """
    Enum for the state of a field in the database
    Used for filtering the fields regarding the context
    """
    CSV_ONLY = 0  # field is only in the CSV result file
    SQL_ONLY = 1  # field is only in the database
    CHANGED = 2  # Changed during the process. Will be preserved if already present in data (CSV file or database)
    NOT_PRESERVED = 3  # value will NOT be preserved if already present in data (CSV file or database)
    ASSET_ONLY = 4  # field is only in the property of the UEAsset class
    USER = 5  # field is only in the user data. Will be preserved if already present in data (CSV file or database)


class CSVFieldType(Enum):
    """
    Enum for the (simplified) type of field in the database
    Used for selecting the good format and/or control to show the value
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
        Cast the value to the type of the field
        :param value: value to cast
        :return: value with the cast type
        """
        if self == self.INT:
            return convert_to_int(value)
        if self == self.FLOAT:
            return convert_to_float(value)
        if self == self.BOOL:
            return convert_to_bool(value)
        if self == self.BOOL:
            return convert_to_datetime(value, formats_to_use=[gui_g.s.epic_datetime_format, gui_g.s.csv_datetime_format])
        return str(value)


class DbVersionNum(Enum):
    """
    The version of the database or/and class.
    Used when checking if database must be upgraded by comparing with the class version
    """
    # when a new version is added to the DbVersionNum enum
    # - add code for the new version to the create_tables() method
    # - add code for the new version check to the check_and_upgrade_database() method
    V0 = 0  # invalid version
    V1 = 1  # initial version : only the "standard" marketplace columns
    V2 = 2  # add the columns used fo user data to the "standard" marketplace columns
    V3 = 3  # add the last_run table to get data about the last run of the app
    V4 = 4  # add custom_attributes field to the assets table
    V5 = 5  # add added_manually column to the assets tablen
    V6 = 6  # future version
