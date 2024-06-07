# coding: utf-8
"""
UEVaultManager setup file.
"""
import sys
from pathlib import Path
try:
    import requirements
    use_requirements = True
except (ImportError, ModuleNotFoundError):
    print('requirements module not found, please install it with: pip install requirements-parser')
    use_requirements = False

import setuptools
from setuptools import setup

from UEVaultManager import __name__, __version__, __codename__, __license__, __author__, __author_email__, __description__, __url__

if sys.version_info < (3, 10):
    sys.exit('python 3.10 or higher is required for UEVaultManager')

current_folder = Path(__file__).parent

# Read __long_description__ from README.md
######################
__long_description__ = Path.joinpath(current_folder, 'README.md').read_text()
# add information about the version and codename in the PyPI page because codename s not available by default
__long_description__ += f'\n\n {__name__} ## version:{__version__} ## codename: {__codename__}'
# __long_description__ = ''.join(__long_description__[8:16])  # keep only description text

# Read requirements from the requirements.txt file
######################
if not use_requirements:
    requirements_from_file = [
        'Pillow', 'beautifulsoup4', 'future', 'pandastable', 'pandas', 'pywebview', 'requests', 'screeninfo', 'setuptools', 'termcolor',
        'ttkbootstrap', 'packaging', 'Faker', 'UEVaultManager'
    ]
else:
    # Note: This can cause problems with hyphenated package names.
    # It is fairly common for PyPi packages to be listed with a hyphen in their name,
    # but for all other references to them to have underscores.
    # see: https://github.com/pypa/setuptools/issues/1080
    requirements_from_file = []
    with open(Path.joinpath(current_folder, 'requirements.txt')) as fd:
        for req in requirements.parse(fd):
            if req.name:
                name = req.name.replace('-', '_')
                full_line = name + "".join(["".join(list(spec)) for spec in req.specs])
                requirements_from_file.append(full_line)
            else:
                # no name meens it's a package from a source URL , e.g.:
                # a GitHub URL doesn't have a name
                # I am not sure what to do with this, actually, right now I just ignore it...
                pass

setup(
    name=__name__,
    version=__version__,
    license=__license__,
    author=__author__,
    author_email=__author_email__,
    description=__description__,
    long_description=__long_description__,
    long_description_content_type='text/markdown',
    url=__url__,
    packages=setuptools.find_packages(),
    # data_files=[('', ['UEVaultManager/assets/UEVM_200x200.png','UEVaultManager/assets/main.ico'])],
    package_data={'': ['assets/*']},
    entry_points=dict(console_scripts=['UEVaultManager = UEVaultManager.cli:main']),
    install_requires=requirements_from_file,
    extras_require=dict(webview=['pywebview>=3.4'], webview_gtk=[
        'pywebview>=3.4',  #
        'PyGObject'
    ]),
    python_requires='>=3.9',
    classifiers=[
        'License :: OSI Approved :: BSD License',  #
        'Programming Language :: Python :: 3.9',  #
        'Programming Language :: Python :: 3.10',  #
        'Programming Language :: Python :: 3.11',  #
        'Programming Language :: Python :: 3.12',  #
        'Operating System :: OS Independent',  #
        'Development Status :: 5 - Production/Stable'
        # 'Development Status :: 4 - Beta'
    ]
)

if __name__ == '__main__':
    setup()
