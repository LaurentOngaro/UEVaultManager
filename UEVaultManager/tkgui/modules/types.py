# coding=utf-8
"""
Definition for the types used in this module:
- UEAssetType: enum to represent the asset type
- DataSourceType: an enum to represent the data source type
- WidgetType: enum for the widget types
"""
from enum import Enum


class UEAssetType(Enum):
    """ Enum to represent the asset type """
    Unknown = 0
    Plugin = 1
    Project = 2


class DataSourceType(Enum):
    """ Enum to represent the data source type """
    FILE = 1
    SQLITE = 2


class WidgetType(Enum):
    """ Enum for the widget types """
    ENTRY = 0  # Entry widget
    TEXT = 1  # Text widget
    LABEL = 2  # Label widget
    CHECKBUTTON = 3  # Checkbutton widget
    BUTTON = 4  # Button widget
