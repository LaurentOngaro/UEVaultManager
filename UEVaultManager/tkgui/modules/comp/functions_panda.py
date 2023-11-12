# coding=utf-8
"""
Utilities functions and tools for pandas
These functions depend on the globals.py module and can generate circular dependencies when imported.
"""
import pandas as pd

from UEVaultManager.tkgui.modules import globals as gui_g
from UEVaultManager.tkgui.modules.functions_no_deps import check_and_convert_list_to_str


def fillna_fixed(dataframe: pd.DataFrame) -> None:
    """
    Fill the empty cells in the dataframe. Fix FutureWarning messages by using the correct value for each dtype
    :param dataframe: dataframe to fill.
    """
    for col in dataframe.columns:
        if dataframe[col].dtype == 'object':
            # dataframe[col].fillna(gui_g.s.empty_cell, inplace=True)  # does not replace all possible values
            dataframe[col].replace(gui_g.s.cell_is_nan_list, gui_g.s.empty_cell, regex=False, inplace=True)
        elif dataframe[col].dtype == 'category':
            # convert to str to do the replacement
            dataframe[col] = dataframe[col].astype(str)
            dataframe[col].replace(gui_g.s.cell_is_nan_list + [''], gui_g.s.missing_category, regex=False, inplace=True)
            # convert back to category
            dataframe[col] = dataframe[col].astype('category')
        elif dataframe[col].dtype == 'int64':
            dataframe[col].fillna(0, inplace=True)
        elif dataframe[col].dtype == 'float64':
            dataframe[col].fillna(0.0, inplace=True)
        elif dataframe[col].dtype == 'bool':
            dataframe[col].fillna(False, inplace=True)


def post_update_installed_folders(installed_assets_json: dict, df: pd.DataFrame) -> None:
    """
    Update the "installed folders" AFTER loading the data.
    :param installed_assets_json: dict of installed assets.
    :param df: datatable.
    """
    # get all installed folders for a given catalog_item_id
    for app_name, asset in installed_assets_json.items():
        installed_folders = asset.get('installed_folders', None)
        if installed_folders:
            # here we use app_name because catalog_item_id does not exsist in CSV
            app_name = asset.get('app_name', None)
            installed_folders_str = check_and_convert_list_to_str(installed_folders)
            df.loc[df['Asset_id'] == app_name, 'Installed folders'] = installed_folders_str
