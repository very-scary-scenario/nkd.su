Setting up your local development environment
=============================================

nkd.su is primarily built and developed on linux-based computers. I do not know
how compatible with Windows it might be, so if you do want to develop on a
Windows system, you probably want to use `WSL`_. Running on macOS should be
fine, as long as you have a package manager to install things with\ [#macos]_.

From hereon out, I'm going to assume that you are somewhat comfortable in a
unix-like terminal and that you have a package manager you're familiar with. I
also will assume you have a copy of the nkd.su git repository.

If you want to do your development on a computer running NixOS, there's
:ref:`information about how to develop on NixOS <nixos-development>` for you.

.. [#macos] Sorry, I'm out of the loop on macOS package managers. I assume
   people still use Homebrew. Are Fink and MacPorts keeping up with the annual
   releases? Is it reasonable to recommend Nix yet?

.. _WSL: https://learn.microsoft.com/en-us/windows/wsl/

.. toctree::
   :hidden:

   setup/nix

.. _system:

System packages
---------------

You will need to install some things with your system package manager:

Python 3.11
   If Python 3.11 isn't in your package manager, 3.10 might work. 3.9
   definitely won't. Barring major deprecations, I expect future versions to
   probably work.

npm
   npm will pull Node.js in as a dependency. The versions of these almost
   certainly don't matter, since we do not run any part of nkd.su itself using
   node. We only use it to pull in javascript and fonts and stuff that we will
   be serving on the website\ [#cdns]_.

.. _headers:

Headers for:
   Python itself
      Some of our dependencies are distributed in source form, which means you
      need the Python headers for them to install. This will probably be a
      package called something like ``python3.11-dev`` in your package manager.
 
   libpq
      You don't have install PostgreSQL itself. There should be a package
      called something like ``libpq-dev`` in your package manager.

.. [#cdns] Lots of websites use external CDNs to load common libraries. nkd.su,
   very consciously, does not and will never do that. It's a small thing, but
   it's a small thing in the direction of less mass surveillance on the
   internet. I am sorry that it means you have to install npm on your computer.

.. _python:

Python packages
---------------

You'll need to create a local environment for nkd.su. I strongly recommend
:ref:`virtualenv <python:tut-venv>` for this, but if you have a tool you prefer
(like Conda or something), feel free to use that. Common virtualenv names like
``venv`` in the repository root will be ignored by git.

Once you're in your environment, run ``pip install -r requirements.txt`` from
the repository root to install all of our Python dependencies.

If you get compiler errors at this point, please try to skim through them for
pointers about what the problem might be. There's a decent chance that compiler
errors mean you don't have the right :ref:`headers <headers>` installed. If you
are unable to resolve issues involving ``psycopg2``, you may be able to work
around them by temporarily editing ``requirements.txt`` to list
``psycopg2-binary`` instead of ``psycopg2`` and running ``pip install -r
requirements.txt`` again.

.. _npm:

npm packages
------------

You don't need to manually set up an environment for this one. Run ``npm
install`` from the repository root and you should be all set.

.. _setup-nkdsu:

nkd.su itself
-------------

To run the site in debug mode and not require a local PostgreSQL server, copy
``nkdsu/settings_local_example.py`` to ``nkdsu/settings_local.py``.
``settings_local.py`` is ignored by git, so if you have specific Django
settings you want to apply, feel free to add them here. Then, to set up your
local database, run ``python manage.py migrate``.

You should now be able to do routine stuff; to run the development server, run
``python manage.py runserver``. To run the tests, run ``pytest``\
[#collectstatic]_. Have a look at the ``"scripts"`` section in ``package.json``
to see how to run the linters that get run in CI.

To build these docs, ``cd`` to the ``docs/`` directory in the repository root,
and then run ``make html``.

.. [#collectstatic] At the moment, some of the tests fail if you don't run
   ``python manage.py collectstatic`` first. That's not ideal, but it does mean
   that we can make sure none of the javascript or CSS build pipelines we use
   in production are broken, so I'm not prioritising fixing this.
