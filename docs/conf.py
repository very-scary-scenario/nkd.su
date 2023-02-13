import os
import subprocess
import sys

import django


def _commit_year_range() -> str:
    commit_years = [
        int(y)
        for y in subprocess.check_output(
            ['git', 'log', '--format=%cd', '--date=format:%Y']
        )
        .decode('ascii')
        .split('\n')
        if y
    ]
    return f'{commit_years[-1]}-{commit_years[0]}'


sys.path.append(os.path.abspath(os.path.join(__file__, '..', '..')))
os.environ['DJANGO_SETTINGS_MODULE'] = 'nkdsu.settings'
django.setup()

# Project meta

project = 'nkd.su'
copyright = f'{_commit_year_range()}, colons and nkd.su contributors'
author = 'Very Scary Scenario'

# General
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# HTML output
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']

# autodoc

autodoc_member_order = "bysource"
autodoc_typehints_format = "short"
autodoc_inherit_docstrings = False
autodoc_default_options = {
    'private-members': True,
}

# intersphinx

intersphinx_mapping = {
    "python": ("https://docs.python.org/3.11", None),
    "django": (
        "https://docs.djangoproject.com/en/3.2",
        "https://docs.djangoproject.com/en/3.2/_objects/",
    ),
}
