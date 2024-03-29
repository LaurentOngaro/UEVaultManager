# coding=utf-8
"""
Configuration file for the Sphinx documentation builder.
"""
# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys

# add the current directory to the path, so we can import from there
# must be done BEFORE importing UEVaultManager
docs_src_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, docs_src_path)
# add the parent directory to the path, so we can import from there
src_path = os.path.abspath(os.path.join(docs_src_path, '../../'))
sys.path.insert(0, src_path)
print(f"path added docs_src_path: {docs_src_path}")
print(f"path added src_path: {src_path}")

from UEVaultManager import __name__, __version__, __copyright__, __author__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.

extensions = [
    'sphinx.ext.duration',  #
    'sphinx.ext.doctest',  #
    'sphinx.ext.autodoc',  #
    'sphinx.ext.autosummary',  #
    'sphinx.ext.intersphinx',  #
    'sphinx.ext.mathjax',  #
    'sphinx.ext.todo',  #
    'sphinx.ext.coverage',  #
    'sphinx.ext.viewcode',  #
    'sphinx.ext.extlinks',  #
    'sphinx.ext.napoleon',  #
    'sphinx_rtd_theme',  #
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),  #
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None)  #
}
intersphinx_disabled_domains = ['std']

# -- Autodoc configuration -----------------------------------------------

autodoc_mock_imports = ['_version', 'utils._appdirs']
autodoc_member_order = 'bysource'
autodoc_class_signature = 'separated'
autodoc_inherit_docstrings = True
autodoc_typehints = 'both'
autodoc_default_options = {
    'members': True,
    'undoc-members': False,
    'member-order': 'bysource',
    'exclude-members': '__init__',
    'special-members': False,
}

# General information about the project.
project = __name__
author = __author__
_full_version = __version__
# noinspection PyShadowingBuiltins
copyright = __copyright__

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = {'.rst': 'restructuredtext'}

# The master toctree document.
master_doc = 'index'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set 'language' from the command line for these cases.
language = 'en'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = ['build', '**/pptree.py']

# The name of the Pygments (syntax highlighting) style to use.
highlight_language = 'python3'
pygments_style = 'sphinx'

# If true, `to_do` and `to_doList` produce output, else they produce nothing.
todo_include_todos = True

# The reST default role (used for this markup: `text`) to use for all documents.
default_role = 'autolink'

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
# html_theme = 'agogo'
# html_theme = 'nature'

# html_theme = 'bizstyle'
# html_theme_options = {'rightsidebar': 'true'}  # for bizstyle

html_theme = 'sphinx_rtd_theme'
html_theme_options = {  # for sphinx_rtd_theme
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'vcs_pageview_mode': 'view',
    'style_nav_header_background': 'darkorange',
    # Toc options
    'collapse_navigation': False,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': False,
    'titles_only': False
}

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
# html_theme_options = {}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named 'default.css' will overwrite the builtin 'default.css'.
# html_static_path = ['_static']

# Custom sidebar templates, must be a dictionary that maps document names
# to template names.
#
# This is required for the alabaster theme
# refs: http://alabaster.readthedocs.io/en/latest/installation.html#sidebars
html_sidebars = {
    '**': [
        'relations.html',  # needs 'show_related': True theme option to display
        'searchbox.html',
    ]
}

# -- Options for EPUB output
epub_show_urls = 'footnote'
