#!/bin/bash
# Library of commonly used operations. This should be reusable in other bash scripts.
#
# Note that boolean bash functions return 0 for True! Because bash interprets it as error code.
#
# Copyright C Bhushan; Licensed under the Apache License v2.0.
# https://github.com/cbhushan/script-collection
#

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

isEmptyDirectory() {
    if [ -z "$(ls -A $1)" ]; then
	true
    else
	false
    fi
}


# checks if the program is installed on current PATH. If installed returns true, else returns false
programExists() {
    type "$1" &> /dev/null ;
}
