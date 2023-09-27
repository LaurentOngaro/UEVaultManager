# coding: utf-8
"""
implementation for:
- EPCLFS: Epic Games Encrypted Config Filesystem.
"""
import configparser
import os

from UEVaultManager.lfs.utils import path_join


class EPCLFS:
    """
    Epic Games Encrypted Config Filesystem Class.
    """
    data_keys = []

    def __init__(self):
        self.manifests = dict()
        self.is_windows = os.name == 'nt'
        if self.is_windows:
            self.userprofile_path = os.path.normpath(os.path.expandvars(r'$USERPROFILE'))
            self.appdata_path = os.path.normpath(os.path.expandvars(r'%LOCALAPPDATA%\EpicGamesLauncher\Saved\Config\Windows'))
            self.programdata_path = os.path.normpath(os.path.expandvars(r'%PROGRAMDATA%\Epic\EpicGamesLauncher'))
        else:
            self.userprofile_path = os.path.normpath(os.path.expandvars(r'$HOME'))
            self.appdata_path = self.programdata_path = None
        self.config = configparser.ConfigParser(strict=False)
        self.vault_cache_folder = ''
        self.projects_path = ''
        self.engines_path = ''
        self.read_config()

    def read_config(self):
        """
        Read the EGS config files.
        """
        if not self.appdata_path:
            raise ValueError('EGS AppData path is not set')

        if not os.path.isdir(self.appdata_path):
            raise ValueError('EGS AppData path does not exist')

        self.config.read(path_join(self.appdata_path, 'GameUserSettings.ini'), encoding='utf-8')
        fallback = path_join(self.programdata_path, 'VaultCache') if self.is_windows else '/opt/Epic Games/VaultCache'
        self.vault_cache_folder = self.config.get('Launcher', 'VaultCacheDirectories', fallback=fallback)
        fallback = path_join(self.userprofile_path, '/Documents/Unreal Projects/')
        self.projects_path = self.config.get('Launcher', 'CreatedProjectPaths', fallback=fallback)
        fallback = 'C:/Program Files/Epic Games' if self.is_windows else '/opt/Epic Games'
        self.engines_path = self.config.get('Launcher', 'DefaultAppInstallLocation', fallback=fallback)
