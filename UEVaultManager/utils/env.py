# coding=utf-8
"""
Environment detection functions.
"""
import os
import sys


def is_pyinstaller() -> bool:
    """
    Return True if the program is running in a PyInstaller bundle.
    """
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def is_windows_mac_or_pyi() -> bool:
    """
    Return True if the program is running on Windows, macOS, or in a PyInstaller bundle.
    """
    return is_pyinstaller() or os.name == 'nt' or sys.platform == 'darwin'
