# !/usr/bin/env python
# coding: utf-8

import sys

from setuptools import setup

from UEVaultManager import __version__ as app_version

if sys.version_info < (3, 9):
    sys.exit('python 3.9 or higher is required for UEVaultManager')

with open("README.md", "r") as fh:
    long_description_l = fh.readlines()
    del long_description_l[2:5]  # remove discord/twitter link and logo
    long_description = ''.join(long_description_l)

setup(
    name='UEVaultManager',
    version=app_version,
    license='GPL-3',
    author='Laurent Ongaro',
    author_email='laurent@gameamea.com',
    packages=[
        'UEVaultManager',
        'UEVaultManager.api',
        'UEVaultManager.downloader',
        'UEVaultManager.downloader.mp',
        'UEVaultManager.lfs',
        'UEVaultManager.models',
        'UEVaultManager.utils',
    ],
    entry_points=dict(
        console_scripts=['UEVaultManager = UEVaultManager.cli:main']
    ),
    install_requires=[
        'requests<3.0',
        'setuptools',
        'wheel'
    ],
    extras_require=dict(
        webview=['pywebview>=3.4'],
        webview_gtk=['pywebview>=3.4', 'PyGObject']
    ),
    url='https://github.com/LaurentOngaro/UEVaultManager',
    description='Free and open-source replacement for the Epic Games Launcher application, mainly to manage the assets for Unreal Engine',
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires='>=3.9',
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.9',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Games/Entertainment',
        'Development Status :: 0.9 - beta',
    ]
)
