# coding=utf-8
"""
Definition for the types used in this module:
- UEAssetType: enum to represent the asset type
- DataSourceType: an enum to represent the data source type
- WidgetType: enum for the widget types.
"""
from enum import Enum


class DataFrameUsed(Enum):
    """ Enum to represent the data frame used for getting or setting the data"""
    AUTO = 0  # Automatically select the data frame wether it is filtered or not
    UNFILTERED = 1  # Use the data frame with unfiltered data
    FILTERED = 2  # Use the data frame with filtered data
    MODEL = 3  # Use the model.df.
    BOTH = 4  # Use both data frames


class UEAssetType(Enum):
    """ Enum to represent the asset type """
    Unknown = 0
    Plugin = 1
    Asset = 2
    Manifest = 3

    @property
    def category_name(self):
        """ Return the category name of the asset type """
        if self == self.Plugin:
            return "plugins/engine"  # existing category in the marketplace
        if self == self.Asset:
            return "local/asset"  # non-existing category in the marketplace
        if self == self.Manifest:
            return "local/manifest"  # non-existing category in the marketplace
        return "local/unknown"  # non-existing category in the marketplace


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
