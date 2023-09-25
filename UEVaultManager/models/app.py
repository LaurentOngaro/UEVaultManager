# coding: utf-8
"""
implementation for:
- AppAsset: App asset data
- App: Combination of app asset, app metadata and app extra as stored on disk
- VerifyResult: Result of a verification
.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


@dataclass
class AppAsset:
    """
    App asset data.
    """
    app_name: str = ''
    asset_id: str = ''
    build_version: str = ''
    catalog_item_id: str = ''
    label_name: str = ''
    namespace: str = ''
    metadata: Dict = field(default_factory=dict)

    # noinspection DuplicatedCode
    @classmethod
    def from_egs_json(cls, json) -> 'AppAsset':
        """
        Create AppAsset from EGS.
        :param json: data.
        :return: an AppAsset.
        """
        tmp = cls()
        tmp.app_name = json.get('appName', '')
        tmp.asset_id = json.get('assetId', '')
        tmp.build_version = json.get('buildVersion', '')
        tmp.catalog_item_id = json.get('catalogItemId', '')
        tmp.label_name = json.get('labelName', '')
        tmp.namespace = json.get('namespace', '')
        tmp.metadata = json.get('metadata', {})
        return tmp

    # noinspection DuplicatedCode
    @classmethod
    def from_json(cls, json) -> 'AppAsset':
        """
        Create AppAsset from json.
        :param json: data.
        :return: an AppAsset.
        """
        tmp = cls()
        tmp.app_name = json.get('app_name', '')
        tmp.asset_id = json.get('asset_id', '')
        tmp.build_version = json.get('build_version', '')
        tmp.catalog_item_id = json.get('catalog_item_id', '')
        tmp.label_name = json.get('label_name', '')
        tmp.namespace = json.get('namespace', '')
        tmp.metadata = json.get('metadata', {})
        return tmp


@dataclass
class App:
    """
    Combination of app asset, app metadata and app extra as stored on disk.
    """
    app_name: str
    app_title: str

    asset_infos: Dict[str, AppAsset] = field(default_factory=dict)
    base_urls: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def app_version(self, platform='Windows'):
        """
        Get app version for a given platform.
        :param platform: platform.
        :return: app version.
        """
        if platform not in self.asset_infos:
            return None
        return self.asset_infos[platform].build_version

    @property
    def catalog_item_id(self):
        """
        Get catalog item id.
        :return: catalog item id.
        """
        if not self.metadata:
            return None
        return self.metadata['id']

    @property
    def namespace(self):
        """
        Get namespace.
        :return: namespace.
        """
        if not self.metadata:
            return None
        return self.metadata['namespace']

    @classmethod
    def from_json(cls, json) -> 'App':
        """
        Create App from json.
        :param json: data.
        :return: an App.
        """
        tmp = cls(app_name=json.get('app_name', ''), app_title=json.get('app_title', ''), )  # call to the class constructor
        tmp.metadata = json.get('metadata', dict())
        if 'asset_infos' in json:
            tmp.asset_infos = {k: AppAsset.from_json(v) for k, v in json['asset_infos'].items()}
        else:
            # Migrate old asset_info to new asset_infos
            tmp.asset_infos['Windows'] = AppAsset.from_json(json.get('asset_info', dict()))

        tmp.base_urls = json.get('base_urls', list())
        return tmp

    @property
    def __dict__(self):
        """This is just here so asset_infos gets turned into a dict as well"""
        assets_dict = {k: v.__dict__ for k, v in self.asset_infos.items()}
        return dict(metadata=self.metadata, asset_infos=assets_dict, app_name=self.app_name, app_title=self.app_title, base_urls=self.base_urls)


@dataclass
class InstalledApp:
    """
    Local metadata for an installed app (i.e. asset)
    """
    app_name: str
    title: str = ''
    version: str = ''
    base_urls: List[str] = field(default_factory=list)
    egl_guid: str = ''
    install_size: int = 0
    manifest_path: str = ''
    platform: str = 'Windows'
    installed_folders: List[str] = field(default_factory=list)

    @classmethod
    def from_json(cls, json) -> 'InstalledApp':
        """
        Create InstalledApp from json.
        :param json: data.
        :return: an InstalledApp.
        """
        tmp = cls(
            app_name=json.get('app_name', ''),
            installed_folders=json.get('installed_folders', []),
            title=json.get('title', ''),
            version=json.get('version', ''),
        )
        tmp.base_urls = json.get('base_urls', [])
        tmp.egl_guid = json.get('egl_guid', '')
        tmp.install_size = json.get('install_size', 0)
        tmp.manifest_path = json.get('manifest_path', '')
        tmp.platform = json.get('platform', 'Windows')
        return tmp

    @property
    def install_path(self) -> str:
        """
        Get the "install path" (i.e. the last from installed_folders).
        :return: install path.
        """
        install_path = self.installed_folders
        if isinstance(install_path, list):
            install_path = install_path.pop()
        return install_path

    @install_path.setter
    def install_path(self, path):
        """
        Set the "install path" (i.e. add it to the installed_folders ).
        :param path: install path.
        """
        if path not in self.installed_folders:
            self.installed_folders.append(path)
        # sorted(self.installed_folders) # if sorted, the "install path" won't be the last one anymore


class VerifyResult(Enum):
    """
    Result of a verification.
    """
    HASH_MATCH = 0
    HASH_MISMATCH = 1
    FILE_MISSING = 2
    OTHER_ERROR = 3
