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
from UEVaultManager.tkgui.modules.types import FilterType


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
        :return: dict of filters

        Notes:
            It returns a dict where each entry must be
            - {'<label>': {FilterType.STR, <query string>} }
            - {'<label>': {FilterType.CALLABLE, <callable>} }
            - {'<label>': {FilterType.LIST, <list of values>} }
            where:
             <label> is the label to display in the quick filter list
             <callable> is the function to call to get the mask.
             <list of values> list of asset_id ou app_name (json encoded)
        """
        filters = {
            'Owned': [FilterType.STR, 'Owned == True'],  #
            'Not Owned': [FilterType.STR, 'Owned == False'],  #
            'Obsolete': [FilterType.STR, 'Obsolete == True'],  #
            'Not Obsolete': [FilterType.STR, 'Obsolete == False'],  #
            'Must buy': [FilterType.STR, '`Must buy` == True'],  #
            'Added manually': [FilterType.STR, '`Added manually` == True'],  #
            # 'Plugins only': [FilterType.STR, 'Category.str.contains("Plugin", case=False))'],  #
            'Plugins only': [FilterType.CALLABLE, f'search##Category##Plugin'],  #
            'Free': [FilterType.STR, 'Price == 0 or Free == True'],  #
            'Free and not owned': [FilterType.CALLABLE, "free_and_not_owned"],  #
            'Not Marketplace': [FilterType.STR, 'Origin != "Marketplace"'],
            'Downloaded': [FilterType.STR, '`Downloaded size` != ""'],  #
            'Installed in folder': [FilterType.STR, '`Installed folders` != ""'],  #
            'Local and marketplace': [FilterType.CALLABLE, 'local_and_marketplace'],  #
            'With comment': [FilterType.STR, 'Comment != ""'],  #
            # 'Empty id': [FilterType.STR, f'Asset_id.str.contains("{gui_g.s.empty_row_prefix}", case=False)'],  #
            # 'Local id': [FilterType.STR, f'Asset_id.str.contains("{gui_g.s.duplicate_row_prefix}", case=False)'],  #
            # 'Temp id': [FilterType.STR, f'Asset_id.str.contains("{gui_g.s.temp_id_prefix}", case=False)'],  #
            'Local id': [FilterType.CALLABLE, f'search##Asset_id##{gui_g.s.duplicate_row_prefix}'],  #
            'Empty id': [FilterType.CALLABLE, f'search##Asset_id##{gui_g.s.empty_row_prefix}'],  #
            'Temp id': [FilterType.CALLABLE, f'search##Asset_id##{gui_g.s.temp_id_prefix}'],  #
            'Result OK': [FilterType.STR, '`Grab result` == "NO_ERROR"'],  #
            'Result Not OK': [FilterType.STR, '`Grab result` != "NO_ERROR"'],  #
            'Tags without name': [FilterType.CALLABLE, 'filter_tags_with_number'],  #
        }

        # convert to dict of FilterValues
        result = {}
        for filter_name, value in filters.items():
            ftype, fvalue = value
            result[filter_name] = FilterValue(name=filter_name, value=fvalue, ftype=ftype)
        return result

    def get_method(self, func_name: str) -> Optional[callable]:
        """
        Get a method from its name.
        :param func_name: the name of the method to get.
        :return: the method or None if not found.
        """
        if not func_name:
            return None
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
                flag (optional): a column name to get a True value from. If the column name starts with '^', the value is negated.
        """
        col_name = args[0]
        value = args[1]
        flag = args[2] if len(args) > 2 else None
        if col_name.lower() == gui_g.s.default_value_for_all.lower():
            mask = False
            for col in self.df.columns:
                mask |= self.df[col].astype(str).str.lower().str.contains(value.lower())
        else:
            mask = self.df[col_name].str.contains(value, case=False)
        if flag:
            # remove ` from flag
            flag = flag.replace('`', '')
            if flag.startswith('^'):
                mask &= ~self.df[flag[1:]]
            else:
                mask &= self.df[flag]
        return mask
