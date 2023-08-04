# coding=utf-8
"""
Implementation for:
- AppConf: ConfigParser subclass that saves modification time of config file.
"""
import configparser
import os
import time


class AppConf(configparser.ConfigParser):
    """
    ConfigParser subclass that saves modification time of config file.
    :param args: arguments.
    :param kwargs: keyword arguments.
    """

    def __init__(self, *args, **kwargs):
        self.modified = False
        self.read_only = False
        self.mod_time = None
        super().__init__(*args, **kwargs)
        self.optionxform = str

    def read(self, filename: str, **kwargs) -> list:
        """
        Read config file and save modification time.
        :param filename: file to read.
        :param kwargs: keyword arguments.
        :return: content of the file.
        """
        # if config file exists, save modification time
        if os.path.exists(filename):
            self.mod_time = int(os.stat(filename).st_mtime)

        return super().read(filename)

    def write(self, *args, **kwargs) -> None:
        """
        Write config file and save modification time.
        :param args: arguments.
        :param kwargs: keyword arguments.
        """
        self.modified = False
        super().write(*args, **kwargs)
        self.mod_time = int(time.time())

    def set(self, section: str, option: str, value=None) -> None:
        """
        Set a config option.
        :param section: section name in the config file. If the section does not exist, it will be created.
        :param option: option name.
        :param value: value to set.
        """
        if self.read_only:
            return

        # ensure config section exists
        if not self.has_section(section):
            self.add_section(section)

        self.modified = True
        if value is None:
            super().set(section, option)
        else:
            value = str(value)
            super().set(section, option, value)

    def remove_option(self, section: str, option: str) -> bool:
        """
        Remove an option from the config file.
        :param section: section name in the config file. If the section does not exist, it will be created.
        :param option: option name.
        :return: True if the option was removed, False otherwise.
        """
        if self.read_only:
            return False

        self.modified = True
        return super().remove_option(section, option)

    def __setitem__(self, key: str, value) -> None:
        """
        (internal) Set a config option.
        :param key: key name.
        :param value: value to set.
        """
        if self.read_only:
            return

        self.modified = True
        super().__setitem__(key, value)
