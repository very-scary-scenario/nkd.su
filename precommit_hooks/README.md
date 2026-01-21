# Pre-commit hooks for nkd.su

Pre-commit hooks will check the following have not been added:

 * Superfluous whitespace at end of line or end of file
 * Missing line end at end of file
 * JavaScript code style errors as judged using eslint
 * Python code style errors as judged using black

To enable this, copy `pre-commit` into `.git/hooks/`.
