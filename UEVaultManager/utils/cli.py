# coding=utf-8
"""
CLI interface functions
"""
import os


def get_boolean_choice(prompt, default=True):
    """
    Prompts the user with a yes/no question and returns a boolean value based on their choice.

    Args:
        prompt (str): The question prompt.
        default (bool, optional): The default choice. Defaults to True.

    Returns:
        bool: True if the user chooses yes, False if they choose no.

    """
    yn = 'Y/n' if default else 'y/N'

    choice = input(f'{prompt} [{yn}]: ')
    if not choice:
        return default
    elif choice[0].lower() == 'y':
        return True
    else:
        return False


def get_int_choice(prompt, default=None, min_choice=None, max_choice=None, return_on_invalid=False):
    """
    Prompts the user to enter an integer choice within a specified range.

    Args:
        prompt (str): The question prompt.
        default (int, optional): The default choice. Defaults to None.
        min_choice (int, optional): The minimum allowed choice. Defaults to None.
        max_choice (int, optional): The maximum allowed choice. Defaults to None.
        return_on_invalid (bool, optional): Determines whether to return None on an invalid choice. Defaults to False.

    Returns:
        int or None: The user's integer choice or None if return_on_invalid is True.

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


def str_to_bool(val):
    """
    Convert a string representation of truth to a boolean value.

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'. Raises ValueError if
    'val' is anything else.

    Args:
        val (str): The string representation of truth.

    Returns:
        bool: True or False based on the string representation of truth.

    Raises:
        ValueError: If the input value is not a valid truth representation.

    """
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return True
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return False
    else:
        raise ValueError('Invalid truth value %r' % (val,))


def check_and_create_path(full_file_name: str) -> bool:
    """
    Checks if the given file path exists and creates it if it doesn't.

    Args:
        full_file_name (str): The full path of the file.

    Returns:
        bool: True if the path exists or is successfully created, False otherwise.

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


def convert_string_to_float_list(string, increment=0.01):
    """
    Converts a string in the format 'start - end' to a list of float values.

    Args:
        string (str): The string in the format 'start - end'.
        increment: The increment between each float value. Defaults to 0.1.

    Returns:
        list: A list of float values between the start and end values (inclusive).
    """
    start, end = map(float, string.split('-'))
    return [round(i, 2) for i in float_range(start, end, increment)]


def float_range(start, stop, step):
    """
    Generator function that yields a sequence of floating-point numbers from start to stop (inclusive) with a given step size.

    Args:
        start (float): The starting value of the sequence.
        stop (float): The ending value of the sequence.
        step (float): The step size between each number in the sequence.

    Yields:
        float: The next floating-point number in the sequence.
    """
    while start <= stop:
        yield start
        start += step


def create_list_from_string(string):
    """
    Creates a list from a string using ',' as a separator. If an item contains a '-', it is converted into a string of float values.

    Args:
        string (str): The input string.

    Returns:
        list: The resulting list.

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
