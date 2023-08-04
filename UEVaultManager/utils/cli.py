# coding=utf-8
"""
CLI interface functions.
"""
import argparse
import os
import re

from UEVaultManager.models.csv_sql_fields import get_sql_field_name


def get_boolean_choice(prompt: str, default=True) -> bool:
    """
    Prompts the user with a yes/no question and returns a boolean value based on their choice.
    :param prompt: The question prompt.
    :param default: The default choice. Defaults to True.
    :return: True if the user chooses yes, False if they choose no.
    """
    yn = 'Y/n' if default else 'y/N'

    choice = input(f'{prompt} [{yn}]: ')
    if not choice:
        return default
    elif choice[0].lower() == 'y':
        return True
    else:
        return False


def get_int_choice(prompt: str, default=None, min_choice=None, max_choice=None, return_on_invalid=False) -> any:
    """
    Prompts the user to enter an integer choice within a specified range.
    :param prompt: The question prompt.
    :param default: The default choice. Defaults to None.
    :param min_choice: The minimum allowed choice. Defaults to None.
    :param max_choice: The maximum allowed choice. Defaults to None.
    :param return_on_invalid: Determines whether to return None on an invalid choice. Defaults to False.
    :return: The user's integer choice or None if return_on_invalid is True.
    """
    if default is not None:
        prompt = f'{prompt} [{default}]: '
    else:
        prompt = f'{prompt}: '

    while True:
        try:
            if inp := input(prompt):
                choice = int(inp)
            else:
                return default
        except ValueError:
            if return_on_invalid:
                return None
            return_on_invalid = True
            continue
        else:
            if min_choice is not None and choice < min_choice:
                print(f'Number must be greater than {min_choice}')
                if return_on_invalid:
                    return None
                return_on_invalid = True
                continue
            if max_choice is not None and choice > max_choice:
                print(f'Number must be less than {max_choice}')
                if return_on_invalid:
                    return None
                return_on_invalid = True
                continue
            return choice


def str_to_bool(val: str) -> bool:
    """
    Convert a string representation of truth to a boolean value.
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'. Raises ValueError if
    'val' is anything else.
    :param val: The string representation of truth.
    :return: True or False based on the string representation of truth.
    """
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return True
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return False
    else:
        raise ValueError('Invalid truth value %r' % (val, ))


def str_is_bool(val: str) -> bool:
    """
    Check if a string could be a boolean value.
    Boolean values are 'y', 'yes', 't', 'true', 'on', '1', 'n', 'no', 'f', 'false', 'off', and '0'.
    :param val: The string representation of truth.
    :return: True if the string could be a boolean value, False otherwise.
    """
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1', 'n', 'no', 'f', 'false', 'off', '0'):
        return True
    else:
        return False


def check_and_create_path(full_file_name: str) -> bool:
    """
    Checks if the given file path exists and creates it if it doesn't.
    :param full_file_name: The full path of the file.
    :return: True if the path exists or is successfully created, False otherwise.
    """
    # Split the file path and name
    file_path, file_name = os.path.split(full_file_name)

    # Check if the folder exists, create it if it doesn't
    if not os.path.isdir(file_path):
        try:
            os.makedirs(file_path, exist_ok=True)
        except OSError:
            return False

    return True


def convert_string_to_float_list(string: str, increment=0.01) -> list:
    """
    Converts a string in the format 'start - end' to a list of float values.
    :param string: The string in the format 'start - end'.
    :param increment: The increment between each float value. Defaults to 0.1.
    :return: A list of float values between the start and end values (inclusive).
    """
    start, end = map(float, string.split('-'))
    return [round(i, 2) for i in float_range(start, end, increment)]


def float_range(start: float, stop: float, step: float) -> iter:
    """
    Generator function that yields a sequence of floating-point numbers from start to stop (inclusive) with a given step size.
    :param start: The starting value of the sequence.
    :param stop: The ending value of the sequence.
    :param step: The step size between each number in the sequence.
    :return: (yield) The next floating-point number in the sequence.
    """
    while start <= stop:
        yield start
        start += step


def create_list_from_string(string: str) -> list:
    """
    Creates a list from a string using ',' as a separator. If an item contains a '-', it is converted into a string of float values.
    :param  string: The input string.
    :return: The resulting list.
    """
    items = string.split(',')
    result_str = ''

    for item in items:
        if '-' in item:
            float_values = convert_string_to_float_list(item)
            float_string = ','.join(map(str, float_values))
            result_str += float_string + ','
        else:
            result_str += item.strip() + ','
    # remove the last comma
    result_str = result_str[:-1]
    return result_str.split(',')


def get_max_threads() -> int:
    """
    Get the maximum number of threads supported by the system.
    :return: The maximum number of threads supported by the system.
    """
    return min(15, os.cpu_count() + 2)


def convert_to_snake_case(string: str) -> str:
    """
    Convert a string to snake case.
    :param string: The string to convert.
    :return: The converted string.
    """
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', string)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def convert_to_pascal_case(string: str) -> str:
    """
    Convert a string to pascal case.
    :param string: The string to convert.
    :return: The converted string.
    """
    return ''.join(x.capitalize() or '_' for x in string.split('_'))


def check_and_convert_key(dict_to_check: dict, key: str) -> str:
    """
    Check if a key is valid for a dict. If not, try to convert it to snake case or pascal case.
    :param dict_to_check: dict to search the key for.
    :param key: key to check.
    :return: The checked key if it is valid, '' otherwise.
    """
    # if the key (from the source dict) is in the target dict, uses it as is
    if key in dict_to_check.keys():
        return key

    key_to_ignore = [
        # key for data not used in the final json
        'ownedCount', 'headerImage', 'learnThumbnail', 'klass', 'recurrence', 'voucherDiscount', 'keyImages', 'effectiveDate', 'bundle', 'platforms',
        'purchaseLimit', 'compatibleApps', 'tax', 'featured', 'isFeatured', 'discount', 'reviewed',
        # key data already "transformed" and mapped in UEAssetscraper._parse_data()
        'priceValue', 'discountPriceValue', 'seller', 'average_rating', 'rating_total', 'rating', 'categories', 'releaseInfo', 'thumbnail'
    ]
    if key in key_to_ignore:
        return ''

    checked_key = get_sql_field_name(key)
    if checked_key:
        return checked_key
    else:
        # if no, try to convert the key to snake case
        snake_case_key = convert_to_snake_case(key)
        # if it does, use the key as is
        if snake_case_key in dict_to_check.keys():
            checked_key = snake_case_key
        else:
            # if no convert the key to pascal case
            pascal_case_key = convert_to_pascal_case(key)
            if pascal_case_key in dict_to_check.keys():
                checked_key = pascal_case_key
            else:
                # should not happen because all cases must have been treated
                # if not the saved value will be NULL and the value from asset will be lost
                # print(f"Key {key} not found in the dict_to_check") # debug only, will flood the console
                return ''
    return checked_key


def init_dict_from_data(target_dict: dict, source_dict: dict = None) -> None:
    """
    Initialize a dict from another dict. If the key is not found in the target_dict dict, try to convert it to snake case or pascal case.
    :param target_dict:  dict to initialize.
    :param source_dict: dict to use for data.
    """
    if target_dict == {}:
        return
    # copy all the keys from the source_dict dict to the target_dict dict
    for key in source_dict.keys():
        # from the source dict, check if the key exists in the target_dict dict
        checked_key = check_and_convert_key(dict_to_check=target_dict, key=key)
        if checked_key:
            target_dict[checked_key] = source_dict[key]


def remove_command_argument(parser: argparse, options: str) -> None:
    """
    Remove an argument from a command line parser.
    :param parser: The command line parser.
    :param options: The argument to remove.
    """
    for option in options:
        # noinspection PyProtectedMember
        for action in parser._actions:
            if vars(action)['option_strings'][0] == option:
                # noinspection PyProtectedMember
                parser._handle_conflict_resolve(None, [(option, action)])
                break
