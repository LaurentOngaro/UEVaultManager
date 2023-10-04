# coding=utf-8
"""
implementation for:
- EGLManifest: EGL Manifest .
"""
from copy import deepcopy

from UEVaultManager.utils.cli import str_to_bool

_template = {
    'AppCategories': ['public', 'games', 'applications'],
    'AppName': '',
    'AppVersionString': '',
    'BaseURLs': [],
    'BuildLabel': '',
    'CatalogItemId': '',
    'CatalogNamespace': '',
    'ChunkDbs': [],
    'CompatibleApps': [],
    'DisplayName': '',
    'FormatVersion': 0,
    'FullAppName': '',
    'HostInstallationGuid': '',
    'InstallComponents': [],
    'InstallLocation': '',
    'InstallSessionId': '',
    'InstallSize': 0,
    'InstallTags': [],
    'InstallationGuid': '',
    'LaunchCommand': '',
    'LaunchExecutable': '',
    'MainGameAppName': '',
    'MainWindowProcessName': '',
    'MandatoryAppFolderName': '',
    'ManifestLocation': '',
    'OwnershipToken': '',
    # 'PrereqIds': [],
    'ProcessNames': [],
    'StagingLocation': '',
    'TechnicalType': '',
    'VaultThumbnailUrl': '',
    'VaultTitleText': '',
    'bCanRunOffline': True,
    'bIsApplication': True,
    'bIsExecutable': True,
    'bIsIncompleteInstall': False,
    'bIsManaged': False,
    'bNeedsValidation': False,
    'bRequiresAuth': True
}


class EGLManifest:
    """
    EGL Manifest.
    """

    def __init__(self):
        self.app_name = None
        self.app_version_string = None
        self.base_urls = None
        self.build_label = None
        self.catalog_item_id = None
        self.namespace = None
        self.display_name = None
        self.install_location = None
        self.install_size = None
        self.install_tags = None
        self.installation_guid = None
        self.launch_command = None
        self.executable = None
        self.main_game_appname = None
        self.app_folder_name = None
        self.manifest_location = None
        self.ownership_token = None
        self.staging_location = None
        self.can_run_offline = None
        self.is_incomplete_install = None
        self.needs_validation = None

        self.remainder = dict()

    @classmethod
    def from_json(cls, json: dict) -> 'EGLManifest':
        """
        Create EGLManifest from json.
        :param json: json data.
        :return: eGLManifest.
        """
        json = deepcopy(json)
        tmp = cls()
        tmp.app_name = json.pop('AppName')
        tmp.app_version_string = json.pop('AppVersionString', None)
        tmp.base_urls = json.pop('BaseURLs', list())
        # noinspection DuplicatedCode
        tmp.build_label = json.pop('BuildLabel', '')
        tmp.catalog_item_id = json.pop('CatalogItemId', '')
        tmp.namespace = json.pop('CatalogNamespace', '')
        tmp.display_name = json.pop('DisplayName', '')
        tmp.install_location = json.pop('InstallLocation', '')
        tmp.install_size = json.pop('InstallSize', 0)
        tmp.install_tags = json.pop('InstallTags', [])
        # noinspection DuplicatedCode
        tmp.installation_guid = json.pop('InstallationGuid', '')
        tmp.launch_command = json.pop('LaunchCommand', '')
        tmp.executable = json.pop('LaunchExecutable', '')
        tmp.main_game_appname = json.pop('MainGameAppName', '')
        tmp.app_folder_name = json.pop('MandatoryAppFolderName', '')
        tmp.manifest_location = json.pop('ManifestLocation', '')
        tmp.ownership_token = str_to_bool(json.pop('OwnershipToken', 'False'))
        tmp.staging_location = json.pop('StagingLocation', '')
        tmp.can_run_offline = json.pop('bCanRunOffline', True)
        tmp.is_incomplete_install = json.pop('bIsIncompleteInstall', False)
        tmp.needs_validation = json.pop('bNeedsValidation', False)
        tmp.remainder = json.copy()
        return tmp

    def to_json(self) -> dict:
        """
        Convert EGLManifest to json.
        :return: json data.
        """
        out = _template.copy()
        out.update(self.remainder)
        # noinspection DuplicatedCode
        out['AppName'] = self.app_name
        out['AppVersionString'] = self.app_version_string
        out['BaseURLs'] = self.base_urls
        out['BuildLabel'] = self.build_label
        out['CatalogItemId'] = self.catalog_item_id
        out['CatalogNamespace'] = self.namespace
        out['DisplayName'] = self.display_name
        out['InstallLocation'] = self.install_location
        # noinspection DuplicatedCode
        out['InstallSize'] = self.install_size
        out['InstallTags'] = self.install_tags
        out['InstallationGuid'] = self.installation_guid
        out['LaunchCommand'] = self.launch_command
        out['LaunchExecutable'] = self.executable
        out['MainGameAppName'] = self.main_game_appname
        out['MandatoryAppFolderName'] = self.app_folder_name
        out['ManifestLocation'] = self.manifest_location
        out['OwnershipToken'] = str(self.ownership_token).lower()
        out['StagingLocation'] = self.staging_location
        out['bCanRunOffline'] = self.can_run_offline
        out['bIsIncompleteInstall'] = self.is_incomplete_install
        out['bNeedsValidation'] = self.needs_validation
        return out
