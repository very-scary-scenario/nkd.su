import os
import subprocess
import sys

import django


def _commit_year_range() -> str:
    """
    Return the range of years that nkd.su has been worked on during.

    It should match what's in the license:

    >>> import os
    >>> lic_path = os.path.join(os.path.dirname(__file__), '..', 'LICENSE')
    >>> with open(lic_path, 'rt') as lic:
    ...     first_line = lic.readlines()[0]
    >>> years = _commit_year_range()
    >>> assert years in first_line, f'{years!r} not in {first_line!r}'
    """

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
os.environ['BUILDING_DOCS'] = '1'
django.setup()

# Project meta

project = 'nkd.su'

# sphinx automatically replaces four-digit clusters in copyright strings if this is set:
del os.environ['SOURCE_DATE_EPOCH']

project_copyright = f'{_commit_year_range()}, colons and nkd.su contributors'
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

html_theme = 'furo'
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
        "https://docs.djangoproject.com/en/4.2",
        "https://docs.djangoproject.com/en/4.2/_objects/",
    ),
}
