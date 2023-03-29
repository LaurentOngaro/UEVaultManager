# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# for MarkdownParser
from sphinx_markdown_parser.parser import MarkdownParser
# for CommonMarkParser (please see note above!)
from sphinx_markdown_parser.parser import CommonMarkParser
# for use reStructuredText in Markdown
from sphinx_markdown_parser.transform import AutoStructify


def setup(app):
    return
    app.add_source_parser(MarkdownParser)
    app.add_config_value(
        'markdown_parser_config', {
            'auto_toc_tree_section': 'Content',
            'enable_auto_doc_ref': True,
            'enable_auto_toc_tree': True,
            'enable_eval_rst': True,
            'enable_inline_math': True,
            'enable_math': True,
            'extensions': ['extra', 'nl2br', 'sane_lists', 'smarty', 'toc', 'wikilinks', 'pymdownx.arithmatex',],
        }, True
    )
    app.add_transform(AutoStructify)


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'UEVaultManager'
copyright = '2023, Laurent Ongaro'
author = 'Laurent Ongaro'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

# -- General configuration

# note:
# markdown can be used as source file for doc with the usage of sphinx-markdown-parser
# see https://github.com/clayrisser/sphinx-markdown-parser

extensions = [
    'sphinx.ext.duration',  #
    'sphinx.ext.doctest',  #
    'sphinx.ext.autodoc',  #
    'sphinx.ext.autosummary',  #
    'sphinx.ext.intersphinx',  #
    'sphinx_markdown_builder',  #
    'myst_parser'
]

myst_enable_extensions = ["deflist",]
source_suffix = {'.rst': 'restructuredtext', '.txt': 'markdown', '.md': 'markdown'}

intersphinx_mapping = {'python': ('https://docs.python.org/3/', None), 'sphinx': ('https://www.sphinx-doc.org/en/master/', None)}
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
