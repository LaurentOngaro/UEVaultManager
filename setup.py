# !/usr/bin/env python
# coding: utf-8

import os
import sys

from setuptools import setup

from UEVaultManager import __name__, __version__, __license__, __author__, __author_email__, __copyright__, __description__

if sys.version_info < (3, 9):
    sys.exit('python 3.9 or higher is required for UEVaultManager')

root_path = os.path.dirname(os.path.abspath(__file__))
readme_path = os.path.abspath(os.path.join(root_path, "README.rst"))

with open(readme_path, "r") as fh:
    long_description_l = fh.readlines()
    del long_description_l[4:10]  # keep only description text
    long_description = ''.join(long_description_l)

setup(
    name=__name__,
    version=__version__,
    license=__license__,
    author=__author__,
    author_email=__author_email__,
    copyright=__copyright__,
    description=__description__,
    packages=[
        'UEVaultManager', 'UEVaultManager.api', 'UEVaultManager.downloader', 'UEVaultManager.downloader.mp', 'UEVaultManager.lfs',
        'UEVaultManager.models', 'UEVaultManager.utils',
    ],
    entry_points=dict(console_scripts=['UEVaultManager = UEVaultManager.cli:main']),
    install_requires=['requests<3.0', 'setuptools', 'wheel'],
    extras_require=dict(webview=['pywebview>=3.4'], webview_gtk=['pywebview>=3.4', 'PyGObject']),
    url='https://github.com/LaurentOngaro/UEVaultManager',
    long_description_content_type="text/markdown",
    python_requires='>=3.9',
    classifiers=[
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
    ]
)

if __name__ == "__main__":
    setup()
