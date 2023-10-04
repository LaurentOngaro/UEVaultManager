# coding: utf-8
"""
implementation for:
- AssetBase: Asset base data
- Asset: Combination of Asset, Asset metadata and Asset extra as stored on disk
- VerifyResult: Result of a verification
.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List

from UEVaultManager.tkgui.modules.functions_no_deps import merge_lists_or_strings


@dataclass
class AssetBase:
    """
    An asset with minimal data.
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
    def from_egs_json(cls, json) -> 'AssetBase':
        """
        Create AssetBase from EGS.
        :param json: data.
        :return: an AssetBase.
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
    def from_json(cls, json) -> 'AssetBase':
        """
        Create AssetBase from json.
        :param json: data.
        :return: an AssetBase.
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
class Asset:
    """
    Combination of a base asset, asset metadata and asset extra as stored on disk.
    """
    app_name: str
    app_title: str

    asset_infos: Dict[str, AssetBase] = field(default_factory=dict)
    base_urls: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def app_version(self, platform: str = 'Windows'):
        """
        Get Asset version for a given platform.
        :param platform: platform.
        :return: Asset version.
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
    def from_json(cls, asset_data: dict) -> 'Asset':
        """
        Create Asset from json.
        :param asset_data: data.
        :return: an Asset.
        """
        tmp = cls(app_name=asset_data.get('app_name', ''), app_title=asset_data.get('app_title', ''), )  # call to the class constructor
        tmp.metadata = asset_data.get('metadata', dict())
        if 'asset_infos' in asset_data:
            tmp.asset_infos = {k: AssetBase.from_json(v) for k, v in asset_data['asset_infos'].items()}
        else:
            # Migrate old asset_info to new asset_infos
            tmp.asset_infos['Windows'] = AssetBase.from_json(asset_data.get('asset_info', dict()))

        tmp.base_urls = asset_data.get('base_urls', list())
        return tmp

    @property
    def __dict__(self):
        """This is just here so asset_infos gets turned into a dict as well"""
        assets_dict = {k: v.__dict__ for k, v in self.asset_infos.items()}
        return dict(metadata=self.metadata, asset_infos=assets_dict, app_name=self.app_name, app_title=self.app_title, base_urls=self.base_urls)


@dataclass
class InstalledAsset:
    """
    Local metadata for an installed asset
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
    def from_json(cls, asset_data: dict) -> 'InstalledAsset':
        """
        Create InstalledAsset from json.
        :param asset_data: data.
        :return: an InstalledAsset.
        """
        tmp = cls(
            app_name=asset_data.get('app_name', ''),
            installed_folders=asset_data.get('installed_folders', []),
            title=asset_data.get('title', ''),
            version=asset_data.get('version', ''),
        )
        tmp.base_urls = asset_data.get('base_urls', [])
        tmp.egl_guid = asset_data.get('egl_guid', '')
        tmp.install_size = asset_data.get('install_size', 0)
        tmp.manifest_path = asset_data.get('manifest_path', '')
        tmp.platform = asset_data.get('platform', 'Windows')
        return tmp

    def _add_to_installed_folders(self, path: str):
        """
        Add path to installed_folders.
        :param path: path to add.
        """
        path = path.strip()
        if not path or len(path) == 0:
            return
        result = merge_lists_or_strings(self.installed_folders, path)
        self.installed_folders = result

    @property
    def install_path(self) -> str:
        """
        Get the "install path" of the installed asset.
        :return: install path.

        Notes:
            Will return the most recent values from installed_folders property.
        """
        install_path = ''
        if isinstance(self.installed_folders, list) and len(self.installed_folders) > 0:
            install_path = self.installed_folders[-1]
        return install_path

    @install_path.setter
    def install_path(self, path: str):
        """
        Set an "install path"
        :param path: install path.

        Notes:
            Add the path to the installed_folders property.
        """
        self._add_to_installed_folders(path)


class VerifyResult(Enum):
    """
    Result of a verification.
    """
    HASH_MATCH = 0
    HASH_MISMATCH = 1
    FILE_MISSING = 2
    OTHER_ERROR = 3
