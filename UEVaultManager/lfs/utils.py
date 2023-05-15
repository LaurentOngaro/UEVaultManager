# coding: utf-8

import logging
from pathlib import Path

logger = logging.getLogger('LFS Utils')


def clean_filename(filename: str) -> str:
    """
    Clean a filename from invalid characters
    :param filename: The filename to clean
    :return:  The cleaned filename
    """
    return ''.join(i for i in filename if i not in '<>:"/\\|?*')


def get_dir_size(path: str) -> int:
    """
    Get the size of a directory
    :param path: The path to the directory
    :return:
    """
    return sum(f.stat().st_size for f in Path(path).glob('**/*') if f.is_file())
