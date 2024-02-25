.. _nixos-development:

Developing on NixOS
===================

You can run nkd.su locally using its ``flake.nix``. With `flakes enabled`_,
from the repository root, run ``nix develop``. This will create an environment
with the system and Python dependencies for you. It won't include the node
dependencies, but it will include :ref:`npm <npm>`, so after you've run ``npm
install`` you should be able to get right to :ref:`setting up your database and
stuff <setup-nkdsu>`.

.. _flakes enabled: https://nixos.wiki/wiki/Flakes
