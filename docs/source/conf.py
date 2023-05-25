# Configuration file for the Sphinx documentation builder.

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys

docs_src_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, docs_src_path)
src_path = os.path.abspath(os.path.join(docs_src_path, "..", "UEVaultManager"))
sys.path.insert(0, src_path)


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
    "sphinx.ext.mathjax",  #
    "sphinx.ext.todo",  #
    "sphinx.ext.coverage",  #
    "sphinx.ext.viewcode",  #
    "sphinx.ext.extlinks",  #
    "sphinx.ext.napoleon"  #
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),  #
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None)  #
}
intersphinx_disabled_domains = ['std']

# -- Autodoc configuration -----------------------------------------------

autodoc_mock_imports = ["_version", "utils._appdirs"]
autodoc_member_order = "bysource"
autodoc_class_signature = "separated"
autodoc_inherit_docstrings = True
autodoc_typehints = "both"
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "member-order": "bysource",
    "exclude-members": "__init__",
    "special-members": False,
}

# General information about the project.
project = 'UEVaultManager'
author = 'Laurent Ongaro'
# noinspection PyShadowingBuiltins
copyright = '2023 Laurent Ongaro'
_full_version = '1.5.0'

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = {'.rst': 'restructuredtext'}

# The master toctree document.
master_doc = "index"

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = "en"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = ["build", "**/pptree.py"]

# The name of the Pygments (syntax highlighting) style to use.
highlight_language = "python3"
pygments_style = "sphinx"

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True

# The reST default role (used for this markup: `text`) to use for all documents.
default_role = "autolink"

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme_options = {
    "canonical_url": "",
    "analytics_id": ""
}

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
# html_theme_options = {}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ["_static"]

# Custom sidebar templates, must be a dictionary that maps document names
# to template names.
#
# This is required for the alabaster theme
# refs: http://alabaster.readthedocs.io/en/latest/installation.html#sidebars
html_sidebars = {
    "**": [
        "relations.html",  # needs 'show_related': True theme option to display
        "searchbox.html",
    ]
}

# -- Options for EPUB output
epub_show_urls = 'footnote'
