# coding: utf-8
"""
Implementation for:
- JSONManifest: Manifest-compatible reader for JSON based manifests.
- JSONManifestMeta: JSON Manifest Meta
- JSONCDL: JSON Chunk Data List
- JSONFML: JSON File Manifest List
"""
import json
import struct
from copy import deepcopy

from UEVaultManager.models.manifest import (CDL, ChunkInfo, ChunkPart, CustomFields, FileManifest, FML, Manifest, ManifestMeta)

debug_mode = False  # set to True to print debug messages


def blob_to_num(in_str):
    """
    Convert a string to a number.
    :param in_str: string to convert.
    :return: converted number.

    Notes:
        The JSON manifest use a rather strange format for storing numbers.
        It's essentially %03d for each char concatenated to a string instead of just putting the fucking number in the JSON...
        Also, it's still little endian, so we have to bitshift it.
    """
    num = 0
    shift = 0
    for i in range(0, len(in_str), 3):
        num += (int(in_str[i:i + 3]) << shift)
        shift += 8
    return num


def guid_from_json(in_str):
    """
    Get guid from a json string.
    :param in_str: string to convert.
    :return: the Guid
    """
    return struct.unpack('>IIII', bytes.fromhex(in_str))


def log_debug(msg):
    """
    print a debug message
    :param msg:
    """
    if debug_mode:
        print(msg)


class JSONManifest(Manifest):
    """
    Manifest-compatible reader for JSON based manifests.
    """

    def __init__(self):
        super().__init__()
        self.json_data = None

    @classmethod
    def read_all(cls, manifest):
        """
        Read all kind of manifest
        :param manifest:
        :return: a json manifest
        """
        _m = cls.read(manifest)
        _tmp = deepcopy(_m.json_data)

        _m.meta = JSONManifestMeta.read(_tmp)
        _m.chunk_data_list = JSONCDL.read(_tmp, manifest_version=_m.version)
        _m.file_manifest_list = JSONFML.read(_tmp)
        _m.custom_fields = CustomFields()
        # _m.custom_fields._dict = _tmp.pop('CustomFields', {})
        _m.custom_fields._dict = _m.meta.custom_fields

        if _tmp.keys():
            log_debug(f'Did not read JSON keys: {_tmp.keys()}!')

        # clear raw data after manifest has been loaded
        _m.data = b''
        _m.json_data = None

        return _m

    @classmethod
    def read(cls, manifest):
        """
        Read the JSON manifest.
        :param manifest: manifest data.
        :return: Manifest object.
        """
        _manifest = cls()
        _manifest.data = manifest
        _manifest.json_data = json.loads(manifest.decode('utf-8'))

        _manifest.stored_as = 0  # never compressed
        _manifest.version = blob_to_num(_manifest.json_data.get('ManifestFileVersion', '013000000000'))

        return _manifest

    def write(self, *args, **kwargs):
        """
        Write the JSON manifest.
        :param args: options passed to the command.
        :param kwargs: keyword arguments.
        :return:
        """
        # The version here only matters for the manifest header,
        # the feature level in meta determines chunk folders etc.
        # So all that's required for successful serialization is
        # setting it to something high enough to be a binary manifest
        self.version = 18
        return super().write(*args, **kwargs)


class JSONManifestMeta(ManifestMeta):
    """
    JSON Manifest Meta
    """

    def __init__(self):
        super().__init__()
        self.custom_fields = ''

    @classmethod
    def read(cls, json_data):
        """
        Read the JSON manifest metadata.
        :param json_data: JSON data.
        :return: ManifestMeta object.
        """
        _meta = cls()
        _meta.feature_level = blob_to_num(json_data.pop('ManifestFileVersion', '013000000000'))
        _meta.is_file_data = json_data.pop('bIsFileData', False)
        _meta.app_id = blob_to_num(json_data.pop('AppID', '000000000000'))
        # noinspection DuplicatedCode
        _meta.app_name = json_data.pop('AppNameString', '')
        _meta.build_version = json_data.pop('BuildVersionString', '')
        _meta.launch_exe = json_data.pop('LaunchExeString', '')
        _meta.launch_command = json_data.pop('LaunchCommand', '')
        # not used anymore _meta.prereq_ids = json_data.pop('PrereqIds', [])
        _meta.prereq_name = json_data.pop('PrereqName', '')
        _meta.prereq_path = json_data.pop('PrereqPath', '')
        _meta.prereq_args = json_data.pop('PrereqArgs', '')
        _meta.custom_fields = json_data.pop('CustomFields', '')
        return _meta


class JSONCDL(CDL):
    """
    JSON Chunk Data List
    """

    def __init__(self):
        super().__init__()

    @classmethod
    def read(cls, json_data, manifest_version=13):
        """
        Read the JSON chunk data list.
        :param json_data: JSON data.
        :param manifest_version: manifest version.
        :return: CDL object.
        """
        _cdl = cls()
        _cdl._manifest_version = manifest_version
        _cdl.count = len(json_data['ChunkFilesizeList'])

        cfl = json_data.get('ChunkFilesizeList', {})
        chl = json_data.get('ChunkHashList', {})
        csl = json_data.get('ChunkShaList', {})
        dgl = json_data.get('DataGroupList', {})
        _guids = list(cfl.keys())

        for guid in _guids:
            _ci = ChunkInfo(manifest_version=manifest_version)
            _ci.guid = guid_from_json(guid)
            _ci.file_size = blob_to_num(cfl.get(guid, 0))
            _ci.hash = blob_to_num(chl.get(guid, 0))
            _ci.sha_hash = bytes.fromhex(csl.get(guid, ''))
            _ci.group_num = blob_to_num(dgl.get(guid, 0))
            _ci.window_size = 1024 * 1024
            _cdl.elements.append(_ci)

        for _dc in (cfl, chl, csl, dgl):
            if _dc:
                log_debug(f'Non-consumed CDL stuff: {_dc}')

        return _cdl


class JSONFML(FML):
    """
    JSON File Manifest List
    """

    def __init__(self):
        super().__init__()

    @classmethod
    def read(cls, json_data):
        """
        Read the JSON file manifest list.
        :param json_data: JSON data.
        :return: FML object.
        """
        _fml = cls()
        _fml.count = len(json_data['FileManifestList'])

        for _fmj in json_data.pop('FileManifestList'):
            _fm = FileManifest()
            _fm.filename = _fmj.pop('Filename', '')
            _fm.hash = blob_to_num(_fmj.pop('FileHash')).to_bytes(160 // 8, 'little')
            _fm.flags |= int(_fmj.pop('bIsReadOnly', False))
            _fm.flags |= int(_fmj.pop('bIsCompressed', False)) << 1
            _fm.flags |= int(_fmj.pop('bIsUnixExecutable', False)) << 2
            _fm.file_size = 0
            _fm.chunk_parts = []
            _fm.install_tags = _fmj.pop('InstallTags', [])

            _offset = 0
            for _cpj in _fmj.pop('FileChunkParts'):
                _cp = ChunkPart()
                _cp.guid = guid_from_json(_cpj.pop('Guid'))
                _cp.offset = blob_to_num(_cpj.pop('Offset'))
                _cp.size = blob_to_num(_cpj.pop('Size'))
                _cp.file_offset = _offset
                _fm.file_size += _cp.size
                if _cpj:
                    log_debug(f'Non-read ChunkPart keys: {_cpj.keys()}')
                _fm.chunk_parts.append(_cp)
                _offset += _cp.size

            if _fmj:
                log_debug(f'Non-read FileManifest keys: {_fmj.keys()}')

            _fml.elements.append(_fm)

        return _fml
