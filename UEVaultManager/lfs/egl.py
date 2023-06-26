# coding: utf-8
"""
implementation for:
- EPCLFS: Epic Games Encrypted Config Filesystem
"""

import configparser
import os


class EPCLFS:
    """
    Epic Games Encrypted Config Filesystem Class
    """
    # Known encryption key(s) for JSON user data
    # encrypted using AES-256-ECB mode
    data_keys = []

    def __init__(self):
        if os.name == 'nt':
            self.appdata_path = os.path.expandvars(r'%LOCALAPPDATA%\EpicGamesLauncher\Saved\Config\Windows')
            self.programdata_path = os.path.expandvars(r'%PROGRAMDATA%\Epic\EpicGamesLauncher\Data\Manifests')
        else:
            self.appdata_path = self.programdata_path = None

        self.config = configparser.ConfigParser(strict=False)
        self.config.optionxform = lambda option: option

        self.manifests = dict()

    def read_config(self):
        """
        Reads the EGS config files
        """
        if not self.appdata_path:
            raise ValueError('EGS AppData path is not set')

        if not os.path.isdir(self.appdata_path):
            raise ValueError('EGS AppData path does not exist')

        self.config.read(os.path.join(self.appdata_path, 'GameUserSettings.ini'), encoding='utf-8')
