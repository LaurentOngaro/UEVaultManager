# coding: utf-8
"""
Imlementations for:
- UpdateSeverity: Enum for update severity.
- UEVMAPI: Class for interacting with the UEVaultManager API.
- extract_codename and extract_severity functions
"""
import logging
import re
from enum import Enum

import requests
from platform import system
from packaging import version

from UEVaultManager import __version__


class UpdateSeverity(Enum):
    """
    Enum for update severity.
    """
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3


def extract_codename(pypi_description: str) -> str:
    """
    Extracts the codename from the PyPI description.
    :param pypi_description: PyPI's description
    :return: codename
    """
    pattern = r'## codename:(.*?)##'
    match = re.search(pattern, pypi_description, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        return ''


def extract_severity(old_version: str, new_version: str):
    """
    Gets the update severity of a new version
    :param old_version: old version in standard format "major.minor.micro"
    :param new_version: new version in standard format "major.minor.micro"
    :return: update severity (UpdateSeverity type)
    """
    old_ver = version.parse(old_version)
    new_ver = version.parse(new_version)

    if new_ver > old_ver:
        if new_ver.major > old_ver.major:
            return UpdateSeverity.HIGH
        elif new_ver.minor > old_ver.minor:
            return UpdateSeverity.MEDIUM
        elif new_ver.micro > old_ver.micro:
            return UpdateSeverity.LOW
    else:
        return UpdateSeverity.NONE


class UEVMAPI:
    """
    Class for interacting with the UEVaultManager API.
    """
    _package_name = 'UEVaultManager'
    _user_agent = f'{_package_name}/{__version__} ({system()})'

    def __init__(self):
        self.session = requests.session()
        self.log = logging.getLogger('UEVMAPI')
        self.session.headers['User-Agent'] = self._user_agent

    def get_version_information(self) -> dict:
        """
        Gets the latest packagage version information from PyPI.
        :return: version information
        """
        url = f'https://pypi.org/pypi/{self._package_name}/json'
        r = self.session.get(url, timeout=10.0)
        r.raise_for_status()
        data = r.json()
        pypi_version = '0.0.0'
        pypi_codename = ''
        severity = UpdateSeverity.NONE
        release_url = ''
        summary = ''
        try:
            pypi_version = data['info']['version']
            pypi_codename = extract_codename(data['info']['description'])
            severity = str(extract_severity(__version__, pypi_version).name)
            release_url = data['info']['release_url']
            summary = data['info']['summary']
        except KeyError:
            self.log.warning('Failed to get version information from PyPI.')

        return dict(version=pypi_version, codename=pypi_codename, severity=severity, release_url=release_url, summary=summary)
