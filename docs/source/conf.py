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
    'sphinx.ext.intersphinx',  #
    'myst_parser'  #
]

myst_enable_extensions = ["deflist",]
source_suffix = {'.rst': 'restructuredtext', '.txt': 'markdown', '.md': 'markdown'}

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),  #
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None)  #
}
intersphinx_disabled_domains = ['std']

templates_path = ['_templates']

exclude_patterns = ['build/*']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# html_theme = 'alabaster'
html_theme = 'piccolo_theme'
html_static_path = ['_static']

# -- Options for EPUB output
epub_show_urls = 'footnote'
