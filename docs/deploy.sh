#!/bin/sh -ex

cd "$(dirname "$0")"

# build the docs
make clean
make html

# move the build to a new temporary directory
td="$(mktemp -d)"
mv _build/html/* "$td"

# make a single-commit git reposotory containing the build
cd "$td"
git init
git checkout -b pages
git add .
git commit -m 'build'

# deploy it to the pages branch of the repo
git push 'git@codeberg.org:very-scary-scenario/nkdsu' pages --force

# clean up
cd -
rm -rf "$td"
