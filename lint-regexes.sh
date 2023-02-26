#!/bin/sh -e

complain() {
  echo
  echo "-> linting failed: $1"
  false
}

which rg || complain 'you need to install ripgrep'

(! rg --replace '[trailing whitespace]' '\s+$') || complain 'there are files containing trailing whitespace'
