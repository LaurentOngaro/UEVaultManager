# coding: utf-8

import sys
from pathlib import Path

import setuptools
from setuptools import setup

from UEVaultManager import __name__, __version__, __license__, __author__, __author_email__, __copyright__, __description__, __url__

if sys.version_info < (3, 9):
    sys.exit('python 3.9 or higher is required for UEVaultManager')

this_directory = Path(__file__).parent
__long_description__ = Path.joinpath(this_directory, 'README.md').read_text()
# __long_description__ = ''.join(__long_description__[8:16])  # keep only description text

setup(
    name=__name__,
    version=__version__,
    license=__license__,
    author=__author__,
    author_email=__author_email__,
    copyright=__copyright__,
    description=__description__,
    long_description=__long_description__,
    long_description_content_type='text/markdown',
    url=__url__,
    packages=setuptools.find_packages(),
    # packages=[
    #     'UEVaultManager',  #
    #     'UEVaultManager.api',  #
    #     'UEVaultManager.assets',  #
    #     'UEVaultManager.downloader',  #
    #     'UEVaultManager.downloader.mp',  #
    #     'UEVaultManager.lfs',  #
    #     'UEVaultManager.models',  #
    #     'UEVaultManager.tkgui',  #
    #     'UEVaultManager.utils',  #
    # ],
    # data_files=[('', ['UEVaultManager/assets/UEVM_200x200.png','UEVaultManager/assets/main.ico'])],
    package_data={'': ['assets/*']},
    entry_points=dict(console_scripts=['UEVaultManager = UEVaultManager.cli:main']),
    install_requires=[
        'requests<3.0',  #
        'setuptools',  #
        'wheel'
    ],
    extras_require=dict(webview=['pywebview>=3.4'], webview_gtk=[
        'pywebview>=3.4',  #
        'PyGObject'
    ]),
    python_requires='>=3.9',
    classifiers=[
        'License :: OSI Approved :: BSD License',  #
        'Programming Language :: Python :: 3.9',  #
        'Programming Language :: Python :: 3.10', 'Programming Language :: Python :: 3.11',  #
        'Operating System :: OS Independent',  #
        'Development Status :: 4 - Beta'
    ]
)

if __name__ == '__main__':
    setup()
