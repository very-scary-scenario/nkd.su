#!/bin/sh -ex

make clean
make html

td="$(mktemp -d)"
mv _build/html/* "$td"

cd "$td"
git init
git checkout -b pages
git add .
git commit -m 'build'
git push 'git@codeberg.org:very-scary-scenario/nkdsu' pages --force
