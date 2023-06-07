# coding=utf-8
"""
Implementation for:
- CSV_headings: contains the title of each column and a boolean value to know if its contents must be preserved if it already exists in the output file (To Avoid overwriting data changed by the user in the file)
"""
import uuid

import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience

CSV_headings = {
    'Asset_id': False,  # ! important: Do not Rename => this field is used as main key for each asset
    'App name': False,
    'App title': False,
    'Category': False,
    'Review': False,
    'Developer': False,
    'Description': False,
    'Status': False,
    'Discount price': False,
    'Discount percentage': False,
    'Discounted': False,
    'Owned': False,
    'Obsolete': False,
    'Supported versions': False,
    'Grab result': False,
    'Price': False,  # ! important: Rename Wisely => this field is searched by text in the next lines
    'Old price': False,  # ! important: always place it after the Price field in the list
    # User Fields
    'Comment': True,
    'Stars': True,
    'Must buy': True,
    'Test result': True,
    'Installed folder': True,
    'Alternative': True,
    'Origin': True,
    # less important fields
    'Page title': False,
    'Image': False,
    'Url': True,  # could be kept if a better url that can be used to download the asset is found
    'Compatible versions': False,
    'Date added': True,
    'Creation date': False,
    'Update date': False,
    'UE version': False,
    'Uid': False
}


def create_emty_csv_row(return_as_string=False):
    """
    Create an empty row for the csv file
    :return: empty row
    """
    data = {}
    for key, _ in CSV_headings.items():
        data[key] = 0  # 0 is used to avoid empty cells in the csv file
    data['Asset_id'] = 'dummy_row_' + str(uuid.uuid4())[:8]  # dummy unique Asset_id to avoid issue
    data['Image'] = gui_g.s.empty_cell  # avoid displaying image warning on mouse over

    if return_as_string:
        data = ','.join(str(value) for value in data.values())
    return data


def unused_function(my_dict):
    # average of values in a dict
    # https://stackoverflow.com/a/9039961
    return sum(my_dict.values()) / len(my_dict)
