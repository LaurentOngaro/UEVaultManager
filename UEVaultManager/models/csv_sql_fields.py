# coding=utf-8
"""
CSV and SQL fields mapping and utility functions.
"""
from datetime import datetime

from pandas import CategoricalDtype

import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.models.types import CSVFieldState, CSVFieldType, DateFormat
from UEVaultManager.tkgui.modules.functions_no_deps import check_and_convert_list_to_str, convert_to_bool, convert_to_float, convert_to_int, \
    create_uid
from UEVaultManager.tkgui.modules.types import DataSourceType, GrabResult, UEAssetType

# noinspection GrazieInspection
csv_sql_fields = {
    # fields mapping from csv to sql
    # key: csv field name, value: {sql name, state }
    'Asset_id': {
        'sql_name': 'asset_id',
        'state': CSVFieldState.CHANGED,
        'field_type': CSVFieldType.STR,
        'label': 'Latest release id'
    },
    'App name': {
        'sql_name': 'title',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.STR
    },
    'Category': {
        'sql_name': 'category',
        'state': CSVFieldState.CHANGED,
        'field_type': CSVFieldType.LIST
    },
    'Review': {
        'sql_name': 'review',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.FLOAT
    },
    'Review count': {
        'sql_name': 'review_count',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.INT
    },
    'Developer': {
        'sql_name': 'author',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.STR
    },
    'Description': {
        'sql_name': 'description',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.TEXT
    },
    'Status': {
        'sql_name': 'status',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.STR
    },
    'Discount price': {
        'sql_name': 'discount_price',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.FLOAT
    },
    'Discount percentage': {
        'sql_name': 'discount_percentage',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.INT
    },
    'Discounted': {
        'sql_name': 'discounted',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.BOOL
    },
    'Is new': {
        'sql_name': 'is_new',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.BOOL
    },
    'Free': {
        'sql_name': 'free',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.BOOL
    },
    'Can purchase': {
        'sql_name': 'can_purchase',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.BOOL
    },
    'Owned': {
        'sql_name': 'owned',
        'state': CSVFieldState.CHANGED,
        'field_type': CSVFieldType.BOOL
    },
    'Obsolete': {
        'sql_name': 'obsolete',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.BOOL
    },
    'Supported versions': {
        'sql_name': 'supported_versions',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.STR
    },
    'Grab result': {
        'sql_name': 'grab_result',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.LIST
    },
    'Price': {
        'sql_name': 'price',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.FLOAT
    },
    'Old price': {
        'sql_name': 'old_price',
        'state': CSVFieldState.CHANGED,
        'field_type': CSVFieldType.FLOAT
    },
    'Origin': {
        'sql_name': 'origin',
        'state': CSVFieldState.CHANGED,
        'field_type': CSVFieldType.STR
    },
    # ## User Fields
    'Comment': {
        'sql_name': 'comment',
        'state': CSVFieldState.USER,
        'field_type': CSVFieldType.TEXT
    },
    'Stars': {
        'sql_name': 'stars',
        'state': CSVFieldState.USER,
        'field_type': CSVFieldType.INT
    },
    'Must buy': {
        'sql_name': 'must_buy',
        'state': CSVFieldState.USER,
        'field_type': CSVFieldType.BOOL
    },
    'Test result': {
        'sql_name': 'test_result',
        'state': CSVFieldState.USER,
        'field_type': CSVFieldType.STR
    },
    'Installed folders': {
        'sql_name': 'installed_folders',
        'state': CSVFieldState.USER,
        'field_type': CSVFieldType.STR,
        'label': 'Installed in  folders\n(all releases)'
    },
    'Alternative': {
        'sql_name': 'alternative',
        'state': CSVFieldState.USER,
        'field_type': CSVFieldType.STR
    },
    'Added manually': {
        'sql_name': 'added_manually',
        'state': CSVFieldState.USER,
        'field_type': CSVFieldType.BOOL
    },
    # ## less important fields
    'Custom attributes': {
        'sql_name': 'custom_attributes',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.STR
    },
    'Page title': {
        'sql_name': 'page_title',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.STR
    },
    'Image': {
        'sql_name': 'thumbnail_url',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.STR
    },
    'Url': {
        'sql_name': 'asset_url',
        'state': CSVFieldState.CHANGED,
        'field_type': CSVFieldType.STR
    },
    'Date added': {
        'sql_name': 'date_added',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.DATETIME
    },
    'Creation date': {
        'sql_name': 'creation_date',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.DATETIME
    },
    'Update date': {
        'sql_name': 'update_date',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.DATETIME
    },
    'Uid': {
        'sql_name': 'id',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.STR
    },
    # ## UE asset class field only
    'Namespace': {
        'sql_name': 'namespace',
        'state': CSVFieldState.ASSET_ONLY,
        'field_type': CSVFieldType.STR
    },
    'Catalog itemid': {
        'sql_name': 'catalog_item_id',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.STR
    },
    'Asset slug': {
        'sql_name': 'asset_slug',
        'state': CSVFieldState.CHANGED,
        'field_type': CSVFieldType.STR
    },
    'Currency code': {
        'sql_name': 'currency_code',
        'state': CSVFieldState.ASSET_ONLY,
        'field_type': CSVFieldType.STR
    },
    'Technical details': {
        'sql_name': 'technical_details',
        'state': CSVFieldState.ASSET_ONLY,
        'field_type': CSVFieldType.STR
    },
    'Long description': {
        'sql_name': 'long_description',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.TEXT
    },
    'Tags': {
        'sql_name': 'tags',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.STR
    },
    'Comment rating id': {
        'sql_name': 'comment_rating_id',
        'state': CSVFieldState.ASSET_ONLY,
        'field_type': CSVFieldType.STR
    },
    'Rating id': {
        'sql_name': 'rating_id',
        'state': CSVFieldState.ASSET_ONLY,
        'field_type': CSVFieldType.STR
    },
    'Is catalog item': {
        'sql_name': 'is_catalog_item',
        'state': CSVFieldState.ASSET_ONLY,
        'field_type': CSVFieldType.BOOL
    },
    'Thumbnail': {
        # intentionnaly duplicated
        'sql_name': 'thumbnail_url',
        'state': CSVFieldState.ASSET_ONLY,
        'field_type': CSVFieldType.STR
    },
    'Release info': {
        'sql_name': 'release_info',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.STR
    },
    'Downloaded size': {
        'sql_name': 'downloaded_size',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.STR
    },
    'In group': {
        'sql_name': 'in_group',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.STR
    },
    'License': {
        'sql_name': 'license',
        'state': CSVFieldState.NORMAL,
        'field_type': CSVFieldType.STR
    },
}


def get_csv_field_name_list(include_asset_only=False, return_as_string=False, filter_on_states=None):
    """
    Get the csv fields list.
    :param include_asset_only: whether to include the asset only fields from result.
    :param return_as_string: whether to return a string instead of a list.
    :param filter_on_states: if not empty, only return the fields in the given states.
    :return: csv headings.
    """
    result = []
    for csv_field, value in csv_sql_fields.items():
        if csv_field == gui_g.s.index_copy_col_name:
            continue
        if not include_asset_only and value['state'] == CSVFieldState.ASSET_ONLY:
            continue
        if filter_on_states and value['state'] not in filter_on_states:
            continue
        if csv_field and csv_field not in result:  # some sql fields could be NONE or duplicate
            result.append(csv_field)
    if return_as_string:
        result = ','.join(result)  # keep join() here to raise an error if installed_folders is not a list of strings
    return result


def get_sql_field_name_list(include_asset_only=False, return_as_string=False, add_alias=False, filter_on_states=None):
    """
    Get the sql fields list.
    :param include_asset_only: whether to include the asset only fields from result.
    :param return_as_string: whether to return a string instead of a list.
    :param add_alias: whether to add the csv name as alias to the sql field name.
    :param filter_on_states: if not empty, only return the fields in the given states.
    :return: sql headings.
    """
    result = []
    for csv_field, value in csv_sql_fields.items():
        if not include_asset_only and value['state'] == CSVFieldState.ASSET_ONLY:
            continue
        if filter_on_states and value['state'] not in filter_on_states:
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
        result = ','.join(result)  # keep join() here to raise an error if installed_folders is not a list of strings
    return result


def get_typed_value(csv_field='', sql_field='', value='') -> (any, ):
    """
    Get the typed value for a field in CSV or SQL format. Only one of the two fields is required.
    :param csv_field: name of the field (csv format).
    :param sql_field: name of the field (sql format).
    :param value: value to cast.
    :return: typed value.
    """
    if sql_field and not csv_field:
        csv_field = get_csv_field_name(sql_field)
    try:
        associated_field = csv_sql_fields.get(csv_field, None)
        if associated_field is not None:
            field_type = associated_field['field_type']
            typed_value = field_type.cast(value)
            return typed_value
    except (Exception, ):
        # print(f'Failed to cast value {value}')
        return value
    return value


def is_on_state(csv_field_name: str, states: list[CSVFieldState], default=False) -> bool:
    """
    Check if the csv field is in the given states.
    :param csv_field_name: csv field name.
    :param states: list of states to check.
    :param default: default value if the field is not in the list.
    :return: True if is in the given states.
    """
    if not isinstance(states, list):
        states = [states]
    try:
        state = get_state(csv_field_name)
        return state in states
    except KeyError:
        # print(f'Key not found {csv_field_name} in is_on_state()')  # debug only. Will flood the console
        return default  # by default, we consider that the field is not on this state


def is_from_type(csv_field_name: str, types: list[CSVFieldType], default=False) -> bool:
    """
    Check if the csv field is in the given types.
    :param csv_field_name: csv field name.
    :param types: list of types to check.
    :param default: default value if the field is not in the list.
    :return: True if is in the given types.
    """
    if not isinstance(types, list):
        types = [types]
    try:
        field_type = get_field_type(csv_field_name)
        return field_type in types
    except KeyError:
        # print(f'Key not found {csv_field_name} in is_from_type()')  # debug only. Will flood the console
        return default  # by default, we consider that the field is not on this type


def get_field_type(csv_field_name: str):
    """
    Get the type of field.
    :param csv_field_name: csv field name.
    :return: type of the field.
    """
    try:
        return csv_sql_fields[csv_field_name]['field_type']
    except KeyError:
        return None


def get_converters(csv_field_name: str):
    """
    Get the converter of field.
    :param csv_field_name: csv field name.
    :return: list of converters to use sequentially. [str] will be returned if the field is not found.
    """
    field_type = get_field_type(csv_field_name)

    if csv_field_name == 'Category':
        return [CategoricalDtype(categories=gui_g.s.asset_categories, ordered=True)]
    if csv_field_name == 'Grab result':
        # this is the list off all the possible value for the field 'Grab result'. It should be updated if necessary
        cat_list = [grab_result.name for grab_result in GrabResult]
        return [CategoricalDtype(categories=cat_list, ordered=True)]
    if field_type == CSVFieldType.LIST:
        # this is a special case. Use a 'category' for pandas datatable.
        # The caller should handle this case where the converter is not callable
        return ['category']
    if field_type == CSVFieldType.INT:
        return [convert_to_int, int]
    if field_type == CSVFieldType.FLOAT:
        return [convert_to_float, float]
    if field_type == CSVFieldType.BOOL:
        return [convert_to_bool, bool]

    # not use full to convert date: Causes issue when loading a filter
    #    if field_type == CSVFieldType.DATETIME:
    #        return [lambda x: convert_to_datetime(x, formats_to_use=[DateFormat.epic, DateFormat.csv])]
    else:
        return [str]


def get_default_value(csv_field_name: str = '', sql_field_name: str = ''):
    """
    Get the default value of field.
    :param csv_field_name: csv field name.
    :param sql_field_name: sql field name. If not provided, the csv field name will be used.
    :return: default value of the field.
    """
    if sql_field_name and not csv_field_name:
        csv_field_name = get_csv_field_name(sql_field_name)
    field_type = get_field_type(csv_field_name)
    default_values = {
        # CSVFieldType.LIST: [],
        # CSVFieldType.STR: '',
        # CSVFieldType.TEXT: '',
        CSVFieldType.INT: 0,
        CSVFieldType.FLOAT: 0.0,
        CSVFieldType.BOOL: False,
        CSVFieldType.DATETIME: datetime.now().strftime(DateFormat.csv),
    }
    return default_values.get(field_type, 'None')


def get_state(csv_field_name: str):
    """
    Get the state of field.
    :param csv_field_name: csv field name.
    :return: state of the field.
    """
    try:
        return csv_sql_fields[csv_field_name]['state']
    except KeyError:
        return None


def is_preserved(csv_field_name: str) -> bool:
    """
    Check if the csv field is preserved.
    :param csv_field_name: csv field name.
    :return: True if is preserved.
    """
    return not is_on_state(csv_field_name, [CSVFieldState.NORMAL])


def get_sql_field_name(csv_field_name: str):
    """
    Get the sql field name for a csv field name.
    :param csv_field_name: csv field name.
    :return: sql field name.
    """
    try:
        return csv_sql_fields[csv_field_name]['sql_name']
    except KeyError:
        return None


def get_label_for_field(csv_field_name: str):
    """
    Get the label associated to a csv field name. Can be used for widgets, usefull when it differs from the csv field name.
    :param csv_field_name: csv field name.
    :return: label for field name or the field name if no label is found.
    """
    try:
        return csv_sql_fields[csv_field_name]['label']
    except KeyError:
        return csv_field_name.replace('_', ' ').title()


def get_csv_field_name(sql_field_name: str) -> str:
    """
    Get the csv field name for a sql field name.
    :param sql_field_name: sql field name.
    :return: csv field name.
    """
    result = None
    for key, value in csv_sql_fields.items():
        if value['sql_name'] == sql_field_name:
            result = key
            break
    return result


def get_sql_user_fields() -> list:
    """
    Get the sql user fields.
    :return: sql user fields.

    Notes:
        The user fields must be preserved when updating the database
        These fields are also present in the asset table and in the UEAsset.init_data() method
        THEY WILL BE PRESERVED when parsing the asset data
    """
    return get_sql_field_name_list(filter_on_states=[CSVFieldState.USER])


def get_sql_preserved_fields() -> list:
    """
    Get the sql preserved fields.
    :return: sql preserved fields.

    Notes:
        The field kept for previous data.
        NEED TO BE SEPARATED FROM self.user_fields
        THEY WILL BE USED (BUT NOT FORCELY PRESERVED) when parsing the asset data
    """
    result = get_sql_field_name_list(filter_on_states=[CSVFieldState.USER, CSVFieldState.CHANGED, CSVFieldState.ASSET_ONLY])
    result.append('id')
    return result


def set_default_values(data: dict, for_sql: bool = False, uid: str = '') -> dict:
    """
    Set default values to a new row.
    :param data: data to set default values to.
    :param for_sql: flag indicating if the data is for SQL.
    :param uid: uid to use for the row. If not provided, a new one will be created.
    :return: data with default values set.
    """
    uid = uid or create_uid()
    new_data = {
        'Asset_id': gui_g.s.empty_row_prefix + uid,
        'Image': gui_g.s.empty_cell,
        'Added manually': True,
        'Uid': uid,
        'Tags': gui_g.s.empty_cell,
        'Category': UEAssetType.Unknown.category_name,
        'Grab result': GrabResult.INCONSISTANT_DATA.name
    }
    if for_sql:
        # replace CSV field names by SQL field names
        for key, value in new_data.items():
            sql_key = get_sql_field_name(key)
            data[sql_key] = value
    else:
        data.update(new_data)
    return data


def create_empty_csv_row(return_as_string=False):
    """
    Create an empty row for the csv file.
    :return: empty row.
    """
    data = {}
    for key in get_csv_field_name_list():
        data[key] = get_default_value(csv_field_name=key)
    data = set_default_values(data)
    if return_as_string:
        return check_and_convert_list_to_str(data.values())
    return data


def convert_csv_row_to_sql_row(csv_row: dict) -> dict:
    """
    Convert a csv row to a sql row.
    :param csv_row: csv row.
    :return: sql row.
    """
    sql_row = {}
    for csv_field, value in csv_row.items():
        sql_field = get_sql_field_name(csv_field)
        if sql_field:
            sql_row[sql_field] = value
    return sql_row


def debug_parsed_data(asset_data: dict, mode: DataSourceType) -> None:
    """
    Debug the parsed data to see missing or empty keys.
    :param asset_data: instance of asset used to fill the datatable.
    :param mode: mode of the application (could be from DataSourceType. DATABASE or DataSourceType. FILE).
    """
    if gui_g.UEVM_log_ref:
        debug_func = gui_g.UEVM_log_ref.info  # info and debug here because we want to see even if debug mode is disabled in CLI (but enabled in GUI)
    else:
        debug_func = print

    # Notes:
    # all the field names in the genuine data (via old or new method) are in pascalCase
    # all the field names in asset data are in snake_case
    # the CSV header (in datatable or CSV file) are the keys of csv_sql_fields and fierrent of the previous both

    # all the fields that are present in data grabbed with the "old" method (ie file/csv mode)
    csv_data_keys_saved = [
        'categories', 'creationDate', 'description', 'developer', 'developerId', 'endOfSupport', 'entitlementName', 'entitlementType', 'id',
        'itemType', 'keyImages', 'lastModifiedDate', 'longDescription', 'namespace', 'releaseInfo', 'requiresSecureAccount', 'status',
        'technicalDetails', 'title', 'unsearchable'
    ]
    # all the fields that are present in data scraped with the "new" method (ie database mode)
    new_data_keys = [
        'id', 'catalogItemId', 'namespace', 'title', 'recurrence', 'currencyCode', 'priceValue', 'discountPriceValue', 'voucherDiscount',
        'discountPercentage', 'keyImages', 'effectiveDate', 'seller', 'description', 'technicalDetails', 'longDescription', 'isFeatured',
        'isCatalogItem', 'categories', 'bundle', 'releaseInfo', 'platforms', 'compatibleApps',
        # 'urlSlug',
        'purchaseLimit', 'tax', 'tags', 'commentRatingId', 'ratingId', 'klass', 'isNew', 'free', 'discounted', 'featured', 'thumbnail',
        'learnThumbnail', 'headerImage', 'status', 'price', 'discount', 'discountPrice', 'ownedCount', 'canPurchase', 'owned', 'isDownloadable',
        'isSunset', 'isBuyAble', 'distributionMethod', 'legacyCommentCount'
    ]

    # fields used in asset data when the application is in FILE mode
    file_field_names = get_csv_field_name_list(include_asset_only=True)
    # we need to convert the field names to ie snake_case to compare with the asset data
    file_field_names = [get_sql_field_name(field_name) for field_name in file_field_names]
    # fields used in asset data when the application is in DB mode
    db_field_names = get_sql_field_name_list(include_asset_only=True)

    debug_func('keys in old_data_keys that are not in new_data_keys.\nThese data will be LOST when switching from FILE to db mode')
    key_lost_from_file = [key for key in csv_data_keys_saved if key not in new_data_keys]
    debug_func(key_lost_from_file)

    debug_func('keys in new_data_keys that are not in old_data_keys.\nThese data will be LOST when switching from DB to file mode')
    key_lost_from_db = [key for key in new_data_keys if key not in csv_data_keys_saved]
    debug_func(key_lost_from_db)

    if mode == DataSourceType.FILE:
        # not pertinent because keys are different
        # debug_func('keys in file_field_names that are not in old_data_keys.\nThese data will always be empty in FILE mode')
        # key_empty_in_file = [key for key in file_field_names if key not in old_csv_data_keys]
        # debug_func(key_empty_in_file)
        debug_func(
            'keys in file_field_names that are not in the asset data.\nThese data have not been copied from existing data in FILE mode.\nThis could be a data loss'
        )
        key_csv_not_in_asset = [key for key in file_field_names if key not in asset_data]
        debug_func(key_csv_not_in_asset)
    elif mode == DataSourceType.DATABASE:
        # not pertinent because keys are different
        # debug_func('keys in db_field_names that are not in new_data_keys.\nThese data will always be empty in ESQLITE mode')
        # key_empty_in_db = [key for key in db_field_names if key not in asset_data.keys()]
        # debug_func(key_empty_in_db)
        debug_func(
            'keys in db_field_names that are not in the asset data.\nThese data have not been copied from existing data in when using the DataSourceType.DATABASE type.\nThis could be a data loss.\nTHIS SHOULD BE EMPTY'
        )
        key_csv_not_in_asset = [key for key in db_field_names if key not in asset_data.keys()]
        debug_func(key_csv_not_in_asset)


def convert_data_to_csv(sql_asset_data: dict) -> dict:
    """
    Return the asset data as a dictionary with the csv field names.
    :param sql_asset_data: asset data with keys in sql format.
    :return: asset data with keys in csv format.
    """
    # return asset_data to record by converting the "sql" field names to "csv" field names
    csv_field_names = get_csv_field_name_list()
    asset_data = {
        get_csv_field_name(key): value for key, value in sql_asset_data.items() if get_csv_field_name(key) in csv_field_names and value is not None
    }
    return asset_data
