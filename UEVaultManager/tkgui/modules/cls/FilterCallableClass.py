# coding=utf-8
"""
Implementation for:
- FilterCallable class: a class that contains methods to create dynamic filters.
"""
from typing import Optional

import pandas as pd

import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.cls.FilterValueClass import FilterValue


class FilterCallable:
    """
    A class that contains methods to create dynamic filters.
    :param df: the dataframe to filter.
    """

    def __init__(self, df: pd.DataFrame):
        self.df: pd.DataFrame = df

    @staticmethod
    def create_dynamic_filters() -> {str: str}:
        """
        Create a dynamic filters list that can be added to the filter frame quick filter list.
        :return: dict of query (string) using column name as key or a 'callable'

        Notes:
            It returns a dict where each entry must be
            - {'<label>': {str, query} }
            - {'<label>': {'callable', <callable>} }
                where:
                 <label> is the label to display in the quick filter list
                 <callable> is the function to call to get the mask.
        """
        filters = {
            'Owned': [str, 'Owned == True'],  #
            'Not Owned': [str, 'Owned == False'],  #
            'Obsolete': [str, 'Obsolete == True'],  #
            'Not Obsolete': [str, 'Obsolete == False'],  #
            'Must buy': [str, '`Must buy` == True'],  #
            'Added manually': [str, '`Added manually` == True'],  #
            # 'Plugins only': [str, 'Category.str.contains("Plugin", case=False))'],  #
            'Plugins only': ['callable', f'search##Category##Plugin'],  #
            'Free': [str, 'Price == 0 or Free == True'],  #
            'Free and not owned': ['callable', "free_and_not_owned"],  #
            'Not Marketplace': [str, 'Origin != "Marketplace"'],
            'Downloaded': [str, '`Downloaded size` != ""'],  #
            'Installed in folder': [str, '`Installed folders` != ""'],  #
            'Local and marketplace': ['callable', 'local_and_marketplace'],  #
            'With comment': [str, 'Comment != ""'],  #
            # 'Empty id': [str, f'Asset_id.str.contains("{gui_g.s.empty_row_prefix}", case=False)'],  #
            # 'Local id': [str, f'Asset_id.str.contains("{gui_g.s.duplicate_row_prefix}", case=False)'],  #
            # 'Temp id': [str, f'Asset_id.str.contains("{gui_g.s.temp_id_prefix}", case=False)'],  #
            'Local id': ['callable', f'search##Asset_id##{gui_g.s.duplicate_row_prefix}'],  #
            'Empty id': ['callable', f'search##Asset_id##{gui_g.s.empty_row_prefix}'],  #
            'Temp id': ['callable', f'search##Asset_id##{gui_g.s.temp_id_prefix}'],  #
            'Result OK': [str, '`Grab result` == "NO_ERROR"'],  #
            'Result Not OK': [str, '`Grab result` != "NO_ERROR"'],  #
            'Tags without name': ['callable', 'filter_tags_with_number'],  #
        }

        # convert to dict of FilterValues
        result = {}
        for filter_name, value in filters.items():
            ftype, fvalue = value
            result[filter_name] = FilterValue(filter_name, ftype, fvalue)
        return result

    def get_method(self, func_name: str) -> Optional[callable]:
        """
        Get a method from its name.
        :param func_name: the name of the method to get.
        :return: the method or None if not found.
        """
        try:
            method = getattr(self, func_name)
        except (Exception, ):
            return None
        return method

    def filter_tags_with_number(self) -> pd.Series:
        """
        Create a mask to filter the data with tags that contains an integer.
        :return: mask to filter the data.
        """
        mask = self.df['Tags'].str.split(',').apply(lambda x: any(gui_fn.is_an_int(i, gui_g.s.tag_prefix, prefix_is_mandatory=True) for i in x))
        return mask

    def filter_free_and_not_owned(self) -> pd.Series:
        """
        Create a mask to filter the data that are not owned and with a price <=0.5 or free.
        Assets that custom attributes contains external_link are also filtered.
        :return: mask to filter the data.
        """
        # Ensure 'Discount price' and 'Price' are float type
        self.df['Discount price'] = self.df['Discount price'].astype(float)
        self.df['Price'] = self.df['Price'].astype(float)
        mask = self.df['Owned'].ne(True) & (self.df['Free'].eq(True) | self.df['Discount price'].le(0.5) | self.df['Price'].le(0.5))
        try:
            # next line could produce an error: {TypeError}bad operand type for unary ~: 'NoneType'
            other_mask = ~self.df['Custom attributes'].str.contains('external_link', case=False)
            mask &= other_mask
        except (Exception, ):
            pass
        return mask

    def filter_local_and_marketplace(self) -> pd.Series:
        """
        Create a mask to filter the data that are not owned and with a price <=0.5 or free.
        Assets that custom attributes contains external_link are also filtered.
        :return: mask to filter the data.
        """
        # all the local assets
        local_asset_rows = self.df['Origin'].ne(gui_g.s.origin_marketplace)
        # all the marketplace assets with a local version
        marketplace_asset_rows_with_local = self.df['Page title'].isin(self.df.loc[local_asset_rows, 'Page title'])
        marketplace_asset_rows_with_local &= self.df['Origin'].eq(gui_g.s.origin_marketplace)
        # only the rows that are local and marketplace
        mask = self.df['Page title'].isin(self.df.loc[marketplace_asset_rows_with_local, 'Page title'])
        return mask

    def filter_search(self, *args) -> pd.Series:
        """
        Create a mask to filter the data where a columns (or 'all') contains a value. Search is case-insensitive.
        :param args: list of parameters.
        :return: mask to filter the data.

        Notes:
            args: list with the following values in order:
                the column name to search in. If 'all', search in all columns.
                the value to search for.
        """
        col_name = args[0]
        value = args[1]
        if col_name == gui_g.s.default_value_for_all.lower():
            mask = False
            for col in self.df.columns:
                mask |= self.df[col].astype(str).str.lower().str.contains(value.lower())
        # if col_name.lower() == 'all':
        #     # search in all columns
        #     mask = self.df.apply(lambda x: x.str.contains(value, case=False).any(), axis=1)
        else:
            mask = self.df[col_name].str.contains(value, case=False)
        return mask
