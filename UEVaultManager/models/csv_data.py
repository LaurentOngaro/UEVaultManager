# coding=utf-8
"""
CSV and SQL fields mapping and utility functions
"""
import uuid
from enum import Enum

import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience


#
# CSV_headings = {
#     # title of each column and a boolean value to know if its contents must be preserved if it already exists in the output file (To Avoid overwriting data changed by the user in the file)
#     # similar list is maintained is UEAssetDbHandlerClass.py/fields_for_csv
#
#     'Asset_id': False,  # ! important: Do not Rename => this field is used as main key for each asset
#     'App name': False,
#     'App title': False,
#     'Category': False,
#     'Review': False,
#     'Developer': False,
#     'Description': False,
#     'Status': False,
#     'Discount price': False,
#     'Discount percentage': False,
#     'Discounted': False,
#     'Owned': False,
#     'Obsolete': False,
#     'Supported versions': False,
#     'Grab result': False,
#     'Price': False,  # ! important: Rename Wisely => this field is searched by text in the next lines
#     'Old price': False,  # ! important: always place it after the Price field in the list
#     # ## User Fields
#     'Comment': True,
#     'Stars': True,
#     'Must buy': True,
#     'Test result': True,
#     'Installed folder': True,
#     'Alternative': True,
#     'Origin': True,
#     # ## less important fields
#     'Page title': False,
#     'Image': False,
#     'Url': True,  # could be kept if a better url that can be used to download the asset is found
#     'Compatible versions': False,
#     'Date added': True,
#     'Creation date': False,
#     'Update date': False,
#     'UE version': False,
#     'Uid': False
# }


class FieldState(Enum):
    """
    Enum for the state of a field in the database
    """
    CSV_ONLY = 0  # field is only in the CSV result file
    SQL_ONLY = 1  # field is only in the database
    PRESERVED = 2  # value will be preserved if already present in data (CSV file or database)
    NOT_PRESERVED = 3  # value will NOT be preserved if already present in data (CSV file or database)
    ASSET_ONLY = 4  # field is only in the property of the UEAsset class


csv_sql_fields = {
    # fields mapping from csv to sql
    # key: csv field name, value: {sql name, state }
    # some field are intentionnaly duplicated because
    #   several CSV fields could come from a same database field
    #   a csv field with this name must exist to get the value
    'Asset_id': {
        'sql_name': 'asset_id',
        'state': FieldState.NOT_PRESERVED
    },
    'App name': {
        'sql_name': 'title',
        'state': FieldState.NOT_PRESERVED
    },
    'App title': {  # intentionnaly duplicated
        'sql_name': 'title',
        'state': FieldState.CSV_ONLY
    },
    'Category': {
        'sql_name': 'category',
        'state': FieldState.NOT_PRESERVED
    },
    'Review': {
        'sql_name': 'review',
        'state': FieldState.NOT_PRESERVED
    },
    'Review count': {  # not in "standard/result" csv file
        'sql_name': 'review_count',
        'state': FieldState.SQL_ONLY
    },
    'Developer': {
        'sql_name': 'author',
        'state': FieldState.NOT_PRESERVED
    },
    'Description': {
        'sql_name': 'description',
        'state': FieldState.NOT_PRESERVED
    },
    'Status': {
        'sql_name': 'status',
        'state': FieldState.NOT_PRESERVED
    },
    'Discount price': {
        'sql_name': 'discount_price',
        'state': FieldState.NOT_PRESERVED
    },
    'Discount percentage': {
        'sql_name': 'discount_percentage',
        'state': FieldState.NOT_PRESERVED
    },
    'Discounted': {
        'sql_name': 'discounted',
        'state': FieldState.NOT_PRESERVED
    },
    'Is new': {  # not in "standard/result" csv file
        'sql_name': 'is_new',
        'state': FieldState.SQL_ONLY
    },
    'Free': {  # not in "standard/result" csv file
        'sql_name': 'free',
        'state': FieldState.SQL_ONLY
    },
    'Can purchase': {  # not in "standard/result" csv file
        'sql_name': 'can_purchase',
        'state': FieldState.SQL_ONLY
    },
    'Owned': {
        'sql_name': 'owned',
        'state': FieldState.NOT_PRESERVED
    },
    'Obsolete': {
        'sql_name': 'obsolete',
        'state': FieldState.NOT_PRESERVED
    },
    'Supported versions': {
        'sql_name': 'supported_versions',
        'state': FieldState.NOT_PRESERVED
    },
    'Grab result': {
        'sql_name': 'grab_result',
        'state': FieldState.NOT_PRESERVED
    },
    'Price': {
        'sql_name': 'price',
        'state': FieldState.NOT_PRESERVED
    },
    # ## User Fields
    'Old price': {
        'sql_name': 'old_price',
        'state': FieldState.PRESERVED
    },
    'Comment': {
        'sql_name': 'comment',
        'state': FieldState.PRESERVED
    },
    'Stars': {
        'sql_name': 'stars',
        'state': FieldState.PRESERVED
    },
    'Must buy': {
        'sql_name': 'must_buy',
        'state': FieldState.PRESERVED
    },
    'Test result': {
        'sql_name': 'test_result',
        'state': FieldState.PRESERVED
    },
    'Installed folder': {
        'sql_name': 'installed_folder',
        'state': FieldState.PRESERVED
    },
    'Alternative': {
        'sql_name': 'alternative',
        'state': FieldState.PRESERVED
    },
    'Origin': {
        'sql_name': 'origin',
        'state': FieldState.PRESERVED
    },
    # ## less important fields
    'Custom attributes': {  # not in "standard/result" csv file
        'sql_name': 'custom_attributes',
        'state': FieldState.SQL_ONLY
    },
    'Page title': {
        'sql_name': 'page_title',
        'state': FieldState.NOT_PRESERVED
    },
    'Image': {
        'sql_name': 'thumbnail_url',
        'state': FieldState.NOT_PRESERVED
    },
    'Url': {
        'sql_name': 'asset_url',
        'state': FieldState.NOT_PRESERVED
    },
    'Compatible versions': {  # not in database
        'sql_name': None,
        'state': FieldState.CSV_ONLY
    },
    'Date added': {
        'sql_name': 'creation_date',
        'state': FieldState.NOT_PRESERVED
    },
    'Creation date': {
        'sql_name': 'update_date',
        'state': FieldState.NOT_PRESERVED
    },
    'Update date': {
        'sql_name': 'date_added_in_db',
        'state': FieldState.NOT_PRESERVED
    },
    'UE version': {  # not in database
        'sql_name': None,
        'state': FieldState.CSV_ONLY
    },
    'Uid': {
        'sql_name': 'id',
        'state': FieldState.NOT_PRESERVED
    },
    # ## UE asset class field only
    'Namespace': {
        'sql_name': 'namespace',
        'state': FieldState.ASSET_ONLY
    },
    'Catalog itemid': {
        'sql_name': 'catalog_item_id',
        'state': FieldState.ASSET_ONLY
    },
    'Asset slug': {
        'sql_name': 'asset_slug',
        'state': FieldState.ASSET_ONLY
    },
    'urlSlug': {  # intentionnaly duplicated
        'sql_name': 'asset_slug',
        'state': FieldState.ASSET_ONLY
    },
    'Currency code': {
        'sql_name': 'currency_code',
        'state': FieldState.ASSET_ONLY
    },
    'Technical details': {
        'sql_name': 'technical_details',
        'state': FieldState.ASSET_ONLY
    },
    'Long description': {
        'sql_name': 'long_description',
        'state': FieldState.ASSET_ONLY
    },
    'Tags': {
        'sql_name': 'tags',
        'state': FieldState.ASSET_ONLY
    },
    'Comment rating id': {
        'sql_name': 'comment_rating_id',
        'state': FieldState.ASSET_ONLY
    },
    'Rating id': {
        'sql_name': 'rating_id',
        'state': FieldState.ASSET_ONLY
    },
    'Is catalog item': {
        'sql_name': 'is_catalog_item',
        'state': FieldState.ASSET_ONLY
    },
    'Thumbnail': {  # intentionnaly duplicated
        'sql_name': 'thumbnail_url',
        'state': FieldState.ASSET_ONLY
    },
}


def get_csv_field_name_list(exclude_sql_only=True, return_as_string=False):
    """
    Get the csv fields list
    :param exclude_sql_only: if True, exclude the sql only fields from result
    :param return_as_string: if True, return a string instead of a list
    :return: csv headings
    """
    result = []
    for csv_field, value in csv_sql_fields.items():
        if exclude_sql_only and value['state'] == FieldState.SQL_ONLY:
            continue

        result.append(csv_field)
    if return_as_string:
        result = ','.join(result)
    return result


def get_sql_field_name_list(exclude_csv_only=True, return_as_string=False, add_alias=False):
    """
    Get the sql fields list
    :param exclude_csv_only: if True, exclude the csv only fields from result
    :param return_as_string: if True, return a string instead of a list
    :param add_alias: if True, add the csv name as alias to the sql field name
    :return: sql headings
    """
    result = []
    for csv_field, value in csv_sql_fields.items():
        if (exclude_csv_only and value['state'] == FieldState.CSV_ONLY) or value['state'] == FieldState.ASSET_ONLY:
            continue

        sql_name = value['sql_name']
        if add_alias:
            if ' AS ' in sql_name:
                result.append(sql_name)
            else:
                result.append(f"{sql_name} AS '{csv_field}'")
        else:
            result.append(sql_name)

    if return_as_string:
        result = ','.join(result)
    return result


def is_preserved(csv_field_name: str) -> bool:
    """
    Check if the csv field is preserved
    :param csv_field_name: csv field name
    :return: True if preserved
    """
    try:
        return csv_sql_fields[csv_field_name]['state'] == FieldState.PRESERVED
    except KeyError:
        return True  # by default, we consider that the field is preserved


def get_sql_field_name(csv_field_name: str):
    """
    Get the sql field name for a csv field name
    :param csv_field_name: csv field name
    :return: sql field name
    """
    try:
        return csv_sql_fields[csv_field_name]['sql_name']
    except KeyError:
        return None


def get_csv_field_name(sql_field_name: str) -> str:
    """
    Get the csv field name for a sql field name
    :param sql_field_name: sql field name
    :return: csv field name
    """
    result = None
    for key, value in csv_sql_fields.items():
        if value['sql_name'] == sql_field_name:
            result = key
            break
    return result


def create_empty_csv_row(return_as_string=False):
    """
    Create an empty row for the csv file
    :return: empty row
    """
    data = {}
    for key in get_csv_field_name_list(exclude_sql_only=True):
        data[key] = 0  # 0 is used to avoid empty cells in the csv file
    data['Asset_id'] = 'dummy_row_' + str(uuid.uuid4())[:8]  # dummy unique Asset_id to avoid issue
    data['Image'] = gui_g.s.empty_cell  # avoid displaying image warning on mouse over

    if return_as_string:
        data = ','.join(str(value) for value in data.values())
    return data
