# coding: utf-8
"""
utilities functions for LFS
"""
import filecmp
import logging
import os
import re
import shutil
from pathlib import Path

logger = logging.getLogger('LFS Utils')


def clean_filename(filename: str) -> str:
    """
    Clean a filename from invalid characters.
    :param filename: filename to clean.
    :return:  The cleaned filename.
    """
    return ''.join(i for i in filename if i not in '<>:"/\\|?*')


def get_dir_size(path: str) -> int:
    """
    Get the size of a directory.
    :param path: path to the directory.
    :return: size of the directory.
    """
    return sum(f.stat().st_size for f in Path(path).glob('**/*') if f.is_file())


def path_join(*paths):
    """
    Join multiple paths together. Make the return value unified
    :param paths: paths to join.
    :return: joined paths.
    """
    return os.path.normpath(Path(*paths).resolve())


def copy_folder(src_folder: str, dest_folder: str, check_copy_size=True) -> bool:
    """
    Copy files from src_folder to dest_folder
    :param src_folder: source directory.
    :param dest_folder: destination directory.
    :param check_copy_size: check if copy was successful by comparing the size of copied files.
    :return: True if successful, False otherwis.
    """
    try:
        os.makedirs(dest_folder, exist_ok=True)
        dest_size = get_dir_size(dest_folder) if check_copy_size else 0
        src_size = get_dir_size(src_folder) if check_copy_size else 0
        size_copied = 0
        for dirpath, dirnames, filenames in os.walk(src_folder):
            # Create corresponding directories in the destination folder
            dest_dirpath = path_join(dest_folder, os.path.relpath(dirpath, src_folder))
            os.makedirs(dest_dirpath, exist_ok=True)
            for filename in filenames:
                src_file = path_join(dirpath, filename)
                dest_file = path_join(dest_dirpath, filename)
                shutil.copy2(src_file, dest_file)
                if check_copy_size:
                    size_copied += os.path.getsize(dest_file)
    except (Exception, ) as error:
        logger.error(f'Error while copying folder: {error!r}')
        return False
    else:
        # Note:
        # we can not just compare folder content (by using compare_folders) because the destination folder may already contain files before copying.
        if check_copy_size:
            # Note: next lines won't work
            # final_dest_size = get_dir_size(dest_folder)
            # if (final_dest_size == dest_size + size_copied) and (size_copied == src_size):
            if size_copied == src_size:
                return True
            else:
                logger.warning(f'Source size ({src_size}) != Destination size ({dest_size + size_copied})')
                return False
        else:
            return True


def compare_folders(folder1: str, folder2: str) -> list:
    """
    Compare two directories and return a list of files that are different
    :param folder1: first directory.
    :param folder2: second directory.
    :return: list of files that are differen.
    """
    comparison = filecmp.dircmp(folder1, folder2)
    return comparison.diff_files


def generate_label_from_path(path: str) -> str:
    """
    Generate a label from a path. Used in comboboxes
    :param path: path to generate the label from.
    :return: label (ex : UE_4.26 (4.26)).

    Notes:
        path = 'C:/Program Files/Epic Games/UE_4.27/Engine/Plugins/Marketplace/MyAsset'
        Output: MyAsset (4.27)
        path = 'D:/MyFolder
        Output: MyFolder (D:)
    """
    folder_name = os.path.basename(path)
    version = get_version_from_path(path)
    if not version:
        version = os.path.splitdrive(path)[0]
    return f"{folder_name} ({version})"


def get_version_from_path(path: str) -> str:
    """
    Get the UE version from a path.
    :param path: path to get the version from (ex : C:/UE_4.26).
    :return: version (ex : 4.26).
    """
    parts = path.split(os.sep)
    patterns = [
        r'UE_(\d[\d._]*)',  # any string starting with 'UE_' followed by one or more digits, dots or underscores ex: 'UE_4_26'
        r'_UE(\d[\d._]*)',  # any string starting with '_UE' followed by one or more digits, dots or underscores ex: '_UE4_26'
        r'([4,5][\._]\d+)',  # 4 or 5 followed by a dot or underscore followed by one or more digits ex: '4.26' or '5.1'
    ]
    patterns = [re.compile(p) for p in patterns]
    for part in parts:
        for pattern in patterns:
            match = re.search(pattern, part)
            if match:
                return match.group(1)
    return ''
