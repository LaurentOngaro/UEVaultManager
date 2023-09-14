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
    def is_dlc(self) -> bool:
        """
        Check if app is a DLC.
        :return: True if DLC, False otherwise.
        """
        return self.metadata and 'mainGameItem' in self.metadata

    @property
    def third_party_store(self):
        """
        Get third party store.
        :return: third party store.
        """
        if not self.metadata:
            return None
        return self.metadata.get('customAttributes', {}).get('ThirdPartyManagedApp', {}).get('value', None)

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
    install_path: str
    title: str
    version: str
    base_urls: List[str] = field(default_factory=list)
    egl_guid: str = ''
    install_size: int = 0
    manifest_path: str = ''
    needs_verification: bool = False
    platform: str = 'Windows'

    @classmethod
    def from_json(cls, json) -> 'InstalledApp':
        """
        Create InstalledApp from json.
        :param json: data. 
        :return: an InstalledApp.
        """
        tmp = cls(
            app_name=json.get('app_name', ''),
            install_path=json.get('install_path', ''),
            title=json.get('title', ''),
            version=json.get('version', ''),
        )

        tmp.base_urls = json.get('base_urls', list())
        tmp.egl_guid = json.get('egl_guid', '')
        tmp.install_size = json.get('install_size', 0)
        tmp.manifest_path = json.get('manifest_path', '')
        tmp.needs_verification = json.get('needs_verification', False) is True
        tmp.platform = json.get('platform', 'Windows')
        return tmp


class VerifyResult(Enum):
    """
    Result of a verification.
    """
    HASH_MATCH = 0
    HASH_MISMATCH = 1
    FILE_MISSING = 2
    OTHER_ERROR = 3
