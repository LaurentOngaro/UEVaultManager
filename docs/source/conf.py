# Configuration file for the Sphinx documentation builder.

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'UEVaultManager'
copyright = '2023, Laurent Ongaro'
author = 'Laurent Ongaro'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

# -- General configuration

extensions = [
    'sphinx.ext.duration',  #
    'sphinx.ext.doctest',  #
    'sphinx.ext.autodoc',  #
    'sphinx.ext.autosummary',  #
    'sphinx.ext.intersphinx'  #
]

source_suffix = {'.rst': 'restructuredtext'}

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),  #
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None)  #
}
intersphinx_disabled_domains = ['std']

exclude_patterns = ['build/*']


# -- Options for EPUB output
epub_show_urls = 'footnote'
