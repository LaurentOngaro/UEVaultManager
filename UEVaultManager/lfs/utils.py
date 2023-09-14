# coding: utf-8
"""
utilities functions for LFS
"""
import filecmp
import logging
import os
import shutil
from pathlib import Path


logger = logging.getLogger('LFS Utils')


def clean_filename(filename: str) -> str:
    """
    Clean a filename from invalid characters.
    :param filename: The filename to clean.
    :return:  The cleaned filename.
    """
    return ''.join(i for i in filename if i not in '<>:"/\\|?*')


def get_dir_size(path: str) -> int:
    """
    Get the size of a directory.
    :param path: The path to the directory.
    :return:
    """
    return sum(f.stat().st_size for f in Path(path).glob('**/*') if f.is_file())


def path_join(*paths):
    """
    Join multiple paths together. Make the return value unified
    :param paths: The paths to join.
    :return: The joined paths.
    """
    return Path(*paths).resolve().as_posix()


def copy_folder(src_folder: str, dest_folder: str, check_copy=True) -> bool:
    """
    Copy files from src_folder to dest_folder
    :param src_folder: source directory
    :param dest_folder: destination directory
    :param check_copy: check if copy was successful
    :return: True if successful, False otherwise
    """
    try:
        if not os.makedirs(dest_folder, exist_ok=True):
            return False
        for item in os.listdir(src_folder):
            src = path_join(src_folder, item)
            dest = path_join(dest_folder, item)
            if os.path.isdir(src):
                shutil.copytree(src, dest, False, None)
            else:
                shutil.copy2(src, dest)
    except (Exception, ):
        return False
    return True if not check_copy or not compare_folders(src_folder, dest_folder) else False


def compare_folders(folder1: str, folder2: str) -> list:
    """
    Compare two directories and return a list of files that are different
    :param folder1: First directory
    :param folder2: Second directory
    :return: List of files that are different
    """
    comparison = filecmp.dircmp(folder1, folder2)
    return comparison.diff_files
