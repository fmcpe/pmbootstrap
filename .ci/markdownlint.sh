#!/bin/sh -e
# Description: lint markdown files
# https://postmarketos.org/pmb-ci

if [ "$(id -u)" = 0 ]; then
	set -x
	apk -q add npm
	exec su "${TESTUSER:-build}" -c "sh -e $0"
fi

export PATH="$PATH:$PWD/node_modules/.bin"

set -x

npm i markdownlint-cli

markdownlint \
	README.md \
	CONTRIBUTING.md

rm -rf node_modules
