# coding=utf-8
"""
CSV and SQL fields mapping and utility functions.
"""
from datetime import datetime

import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.models.types import CSVFieldState, CSVFieldType
from UEVaultManager.tkgui.modules.functions_no_deps import convert_to_int, convert_to_bool, convert_to_float, create_uid, convert_to_datetime

csv_sql_fields = {
    # fields mapping from csv to sql
    # key: csv field name, value: {sql name, state }
    # some field are intentionnaly duplicated because
    #   several CSV fields could come from a same database field
    #   a csv field with this name must exist to get the value
    'Asset_id': {
        'sql_name': 'asset_id',
        'state': CSVFieldState.NOT_PRESERVED,
        'field_type': CSVFieldType.STR
    },
    'App name': {
        'sql_name': 'title',
        'state': CSVFieldState.NOT_PRESERVED,
        'field_type': CSVFieldType.STR
    },
    'App title': {
        # intentionnaly duplicated
        'sql_name': 'title',
        'state': CSVFieldState.CSV_ONLY,
        'field_type': CSVFieldType.STR
    },
    'Category': {
        'sql_name': 'category',
        'state': CSVFieldState.NOT_PRESERVED,
        'field_type': CSVFieldType.LIST
    },
    'Review': {
        'sql_name': 'review',
        'state': CSVFieldState.NOT_PRESERVED,
        'field_type': CSVFieldType.FLOAT
    },
    'Review count': {
        # not in "standard/result" csv file
        'sql_name': 'review_count',
        'state': CSVFieldState.SQL_ONLY,
        'field_type': CSVFieldType.INT
    },
    'Developer': {
        'sql_name': 'author',
        'state': CSVFieldState.NOT_PRESERVED,
        'field_type': CSVFieldType.STR
    },
    'Description': {
        'sql_name': 'description',
        'state': CSVFieldState.NOT_PRESERVED,
        'field_type': CSVFieldType.TEXT
    },
    'Status': {
        'sql_name': 'status',
        'state': CSVFieldState.NOT_PRESERVED,
        'field_type': CSVFieldType.STR
    },
    'Discount price': {
        'sql_name': 'discount_price',
        'state': CSVFieldState.NOT_PRESERVED,
        'field_type': CSVFieldType.FLOAT
    },
    'Discount percentage': {
        'sql_name': 'discount_percentage',
        'state': CSVFieldState.NOT_PRESERVED,
        'field_type': CSVFieldType.INT
    },
    'Discounted': {
        'sql_name': 'discounted',
        'state': CSVFieldState.NOT_PRESERVED,
        'field_type': CSVFieldType.BOOL
    },
    'Is new': {
        # not in "standard/result" csv file
        'sql_name': 'is_new',
        'state': CSVFieldState.SQL_ONLY,
        'field_type': CSVFieldType.BOOL
    },
    'Free': {
        # not in "standard/result" csv file
        'sql_name': 'free',
        'state': CSVFieldState.SQL_ONLY,
        'field_type': CSVFieldType.BOOL
    },
    'Can purchase': {
        # not in "standard/result" csv file
        'sql_name': 'can_purchase',
        'state': CSVFieldState.SQL_ONLY,
        'field_type': CSVFieldType.BOOL
    },
    'Owned': {
        'sql_name': 'owned',
        'state': CSVFieldState.NOT_PRESERVED,
        'field_type': CSVFieldType.BOOL
    },
    'Obsolete': {
        'sql_name': 'obsolete',
        'state': CSVFieldState.NOT_PRESERVED,
        'field_type': CSVFieldType.BOOL
    },
    'Supported versions': {
        'sql_name': 'supported_versions',
        'state': CSVFieldState.NOT_PRESERVED,
        'field_type': CSVFieldType.STR
    },
    'Grab result': {
        'sql_name': 'grab_result',
        'state': CSVFieldState.NOT_PRESERVED,
        'field_type': CSVFieldType.LIST
    },
    'Price': {
        'sql_name': 'price',
        'state': CSVFieldState.NOT_PRESERVED,
        'field_type': CSVFieldType.FLOAT
    },
    # ## User Fields
    'Old price': {
        'sql_name': 'old_price',
        'state': CSVFieldState.CHANGED,
        'field_type': CSVFieldType.FLOAT
    },
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
    'Installed folder': {
        'sql_name': 'installed_folder',
        'state': CSVFieldState.USER,
        'field_type': CSVFieldType.STR
    },
    'Alternative': {
        'sql_name': 'alternative',
        'state': CSVFieldState.USER,
        'field_type': CSVFieldType.STR
    },
    'Origin': {
        'sql_name': 'origin',
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
        # not in "standard/result" csv file
        'sql_name': 'custom_attributes',
        'state': CSVFieldState.SQL_ONLY,
        'field_type': CSVFieldType.STR
    },
    'Page title': {
        'sql_name': 'page_title',
        'state': CSVFieldState.NOT_PRESERVED,
        'field_type': CSVFieldType.STR
    },
    'Image': {
        'sql_name': 'thumbnail_url',
        'state': CSVFieldState.NOT_PRESERVED,
        'field_type': CSVFieldType.STR
    },
    'Url': {
        'sql_name': 'asset_url',
        'state': CSVFieldState.NOT_PRESERVED,
        'field_type': CSVFieldType.STR
    },
    'Compatible versions': {
        # not in database
        'sql_name': None,
        'state': CSVFieldState.CSV_ONLY,
        'field_type': CSVFieldType.STR
    },
    'Date added': {
        'sql_name': 'date_added_in_db',
        'state': CSVFieldState.NOT_PRESERVED,
        'field_type': CSVFieldType.DATETIME
    },
    'Creation date': {
        'sql_name': 'creation_date',
        'state': CSVFieldState.NOT_PRESERVED,
        'field_type': CSVFieldType.DATETIME
    },
    'Update date': {
        'sql_name': 'update_date',
        'state': CSVFieldState.NOT_PRESERVED,
        'field_type': CSVFieldType.DATETIME
    },
    'UE version': {
        # not in database
        'sql_name': None,
        'state': CSVFieldState.CSV_ONLY,
        'field_type': CSVFieldType.STR
    },
    'Uid': {
        'sql_name': 'id',
        'state': CSVFieldState.NOT_PRESERVED,
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
        'state': CSVFieldState.ASSET_ONLY,
        'field_type': CSVFieldType.STR
    },
    'Asset slug': {
        'sql_name': 'asset_slug',
        'state': CSVFieldState.ASSET_ONLY,
        'field_type': CSVFieldType.STR
    },
    'urlSlug': {
        # intentionnaly duplicated
        'sql_name': 'asset_slug',
        'state': CSVFieldState.ASSET_ONLY,
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
        'state': CSVFieldState.ASSET_ONLY,
        'field_type': CSVFieldType.TEXT
    },
    'Tags': {
        'sql_name': 'tags',
        'state': CSVFieldState.SQL_ONLY,
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
}


def get_csv_field_name_list(exclude_sql_only=True, include_asset_only=False, return_as_string=False, filter_on_states=None):
    """
    Get the csv fields list.
    :param exclude_sql_only: if True, exclude the sql only fields from result.
    :param include_asset_only: if True, include the asset only fields from result.
    :param return_as_string: if True, return a string instead of a list.
    :param filter_on_states: if not empty, only return the fields in the given states.
    :return: csv headings.
    """
    result = []
    for csv_field, value in csv_sql_fields.items():
        if exclude_sql_only and value['state'] == CSVFieldState.SQL_ONLY:
            continue
        if not include_asset_only and value['state'] == CSVFieldState.ASSET_ONLY:
            continue
        if filter_on_states and value['state'] not in filter_on_states:
            continue
        result.append(csv_field)
    if return_as_string:
        result = ','.join(result)
    return result


def get_sql_field_name_list(exclude_csv_only=True, include_asset_only=False, return_as_string=False, add_alias=False, filter_on_states=None):
    """
    Get the sql fields list.
    :param exclude_csv_only: if True, exclude the csv only fields from result.
    :param include_asset_only: if True, include the asset only fields from result.
    :param return_as_string: if True, return a string instead of a list.
    :param add_alias: if True, add the csv name as alias to the sql field name.
    :param filter_on_states: if not empty, only return the fields in the given states.
    :return: sql headings.
    """
    result = []
    for csv_field, value in csv_sql_fields.items():
        if exclude_csv_only and value['state'] == CSVFieldState.CSV_ONLY:
            continue
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
        result = ','.join(result)
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

    # noinspection PyBroadException
    try:
        associated_field = csv_sql_fields.get(csv_field, None)
        if associated_field is not None:
            field_type = associated_field['field_type']
            typed_value = field_type.cast(value)
            return typed_value
    except Exception:
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
        print(f'Key not found {csv_field_name} in is_on_state()')  # debug only. Will flood the console
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
        field_type = get_type(csv_field_name)
        return field_type in types
    except KeyError:
        print(f'Key not found {csv_field_name} in is_from_type()')  # debug only. Will flood the console
        return default  # by default, we consider that the field is not on this type


def get_type(csv_field_name: str):
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
    field_type = get_type(csv_field_name)

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
    if field_type == CSVFieldType.DATETIME:
        return [lambda x: convert_to_datetime(x, formats_to_use=[gui_g.s.epic_datetime_format, gui_g.s.csv_datetime_format])]
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
    field_type = get_type(csv_field_name)
    default_values = {
        # CSVFieldType.LIST: [],
        # CSVFieldType.STR: '',
        # CSVFieldType.TEXT: '',
        CSVFieldType.INT: 0,
        CSVFieldType.FLOAT: 0.0,
        CSVFieldType.BOOL: False,
        CSVFieldType.DATETIME: datetime.now().strftime(gui_g.s.csv_datetime_format),
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
    return not is_on_state(csv_field_name, [CSVFieldState.NOT_PRESERVED])


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


def create_empty_csv_row(return_as_string=False):
    """
    Create an empty row for the csv file.
    :return: empty row.
    """
    data = {}
    uid = create_uid()
    for key in get_csv_field_name_list():
        data[key] = get_default_value(csv_field_name=key)
    data['Asset_id'] = gui_g.s.empty_row_prefix + uid  # dummy unique Asset_id to avoid issue
    data['Image'] = gui_g.s.empty_cell  # avoid displaying image warning on mouse over
    data['Uid'] = uid

    if return_as_string:
        data = ','.join(str(value) for value in data.values())
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
