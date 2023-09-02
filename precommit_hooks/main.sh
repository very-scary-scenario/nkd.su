#!/bin/sh

root_dir="$(git rev-parse --show-toplevel)"
original_wd="${PWD}"
detailed_log=/dev/null
dirty=

if git rev-parse --verify HEAD >/dev/null 2>&1
then
	against=$(git rev-parse HEAD)
else
	# Initial commit: diff against an empty tree object
	against=$(git hash-object -t tree /dev/null)
fi

# If you want to allow non-ASCII filenames set this variable to true.
allownonascii=$(git config --type=bool hooks.allownonascii)

# Redirect output to stderr.
exec 1>&2

status=0

# If there are whitespace errors, print the offending file names and fail.
echo "Checking for superfluous whitespace..."
git diff-index --check --cached $against --
status=$[$status + $?]

echo "Checking for missing newlines at EOF..."
if git diff-index --cached ${against} --patch -- | grep -e '^+++ b' -e 'No newline at end of file' | sed 's:+++ b/::' | grep -B1 '^\\ No newline at end of file'
then
    echo
    status=$[$status + 1]
fi


if git diff-index --cached ${against} -- | grep '\.py$' >> "${detailed_log}"
then
    python_modified=1
else
    python_modified=
fi

if git diff-index --cached ${against} -- | grep '\.js$' >> "${detailed_log}"
then
    js_modified=1
else
    js_modified=
fi

if git diff-index --cached ${against} -- | grep '\.rst$' >> "${detailed_log}"
then
    rst_modified=1
else
    rst_modified=
fi

exit_with_status() {
    if [[ ${status} > 0 ]]
    then
        echo "One or more tests failed, aborting commit."
        echo "Please see details above as to what needs to be fixed."
    fi

    exit ${status}
}

if [[ ${python_modified} || ${js_modified} || ${yaml_modified} || ${rst_modified} ]]
then
    temp_dir=$(mktemp -d)
    if [ "$?" != 0 ]
    then
	echo "Unable to create temporary directory, skipping checks that need a clean repo."
	exit_with_status
    fi

    echo "Temporary directory created at ${temp_dir}" >> "${detailed_log}"

    # Copy everything and then clean up later
    # More efficient would be to only copy what we need, but that's a harder problem to solve
    cp -r ${root_dir} ${temp_dir}/
    if [ "$?" != 0 ]
    then
	echo "Unable to copy repository into temporary directory, skipping checks that need a clean repo."
	rm -r ${temp_dir}
	exit_with_status
    fi

    cd ${temp_dir}/$(basename ${root_dir})

    # We need to look just at our staging area
    # Temporarily complete this commit so git can clean up the rest
    git commit --no-verify -m "temporary commit" > "${detailed_log}"
    git clean -- ':!node_modules' > "${detailed_log}"

    cleanup() {
	rm -r ${temp_dir}
    }

    cleanup_and_exit() {
	cleanup

	exit 1
    }

    trap 'cleanup_and_exit' SIGINT

    if [ ${python_modified} ]
    then
	echo "Checking Python code quality with black..."
	if ! npm run-script lint-black
	then
	    status=$[$status + 1]
	    echo
	fi

	echo "Checking Python code quality with flake8..."
	if ! npm run-script lint-flake8
	then
	    status=$[$status + 1]
	    echo
	fi

	echo "Type-checking Python with mypy..."
	if ! npm run-script lint-mypy
	then
	    status=$[$status + 1]
	    echo
	fi

	echo "Checking Django migrations..."
	if ! npm run-script check-migrations
	then
	    status=$[$status + 1]
	    echo
	fi
    else
	echo "Skipping Python code-quality check with black"
	echo "Skipping Python code-quality check with flake8"
	echo "Skipping Python type check with mypy"
	echo "Skipping Django migrations check"
    fi

    if [[ ${python_modified} || ${rst_modified} ]]
    then
	echo "Checking documentation builds..."
	cd docs
	if ! make html
	then
	    status=$[$status + 1]
	    echo
	fi
	cd ..
    fi

    if [ ${js_modified} ]
    then
	echo "Checking JavaScript code-quality with eslint..."
	if ! npm run-script lint-js
	then
	    status=$[$status + 1]
	    echo
	fi
    else
	echo "Skipping JavaScript code-quality check with eslint"
	echo
    fi

    cleanup
fi

exit_with_status
