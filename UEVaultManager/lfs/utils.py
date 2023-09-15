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
    return os.path.normpath(Path(*paths).resolve())


def copy_folder(src_folder: str, dest_folder: str, check_copy_size=True) -> bool:
    """
    Copy files from src_folder to dest_folder
    :param src_folder: source directory
    :param dest_folder: destination directory
    :param check_copy_size: check if copy was successful by comparing the size of copied files
    :return: True if successful, False otherwise
    """
    try:
        os.makedirs(dest_folder, exist_ok=True)
        dest_size = get_dir_size(dest_folder)
        src_size = get_dir_size(src_folder)
        size_copied = 0
        for dirpath, dirnames, filenames in os.walk(src_folder):
            # Create corresponding directories in the destination folder
            dest_dirpath = os.path.join(dest_folder, os.path.relpath(dirpath, src_folder))
            os.makedirs(dest_dirpath, exist_ok=True)
            for filename in filenames:
                src_file = os.path.join(dirpath, filename)
                dest_file = os.path.join(dest_dirpath, filename)
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
    :param folder1: First directory
    :param folder2: Second directory
    :return: List of files that are different
    """
    comparison = filecmp.dircmp(folder1, folder2)
    return comparison.diff_files
