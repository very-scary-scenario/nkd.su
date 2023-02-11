import os
import sys

import django

sys.path.append(os.path.abspath(os.path.join(__file__, '..', '..')))
os.environ['DJANGO_SETTINGS_MODULE'] = 'nkdsu.settings'
django.setup()

# Project meta

project = 'nkd.su'
copyright = '2012-2023, colons and nkd.su contributors'
author = 'Very Scary Scenario'

# General
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx_rtd_theme',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# HTML output
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# autodoc

autodoc_member_order = "bysource"
autodoc_typehints_format = "short"
autodoc_inherit_docstrings = False
