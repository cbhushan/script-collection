#!/bin/bash
read -r -d '' USAGE << EOM
This script lists files that may have encountered a conflict in syncthing. 

Usage:
   ${0} [</path/to/syncthing/config.xml>]

Syncthing conflicts: https://docs.syncthing.net/users/faq.html#what-if-there-is-a-conflict

Copyright C Bhushan; Licensed under the Apache License v2.0.
https://github.com/cbhushan/script-collection
EOM

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
. "${script_dir}/../bash-functions.sh"

assert_program_is_available stat
assert_program_is_available find
assert_program_is_available grep
assert_program_is_available column

expect_args CONFIGXML -- "$@" "${HOME}/.config/syncthing/config.xml"

getconflicts() {
    local TOP_FOLDER
    expect_args TOP_FOLDER -- "$@"
    expect_existing "${TOP_FOLDER}"

    find "${TOP_FOLDER}" -name '*sync-conflict*' -print0 | sort -z
}


syncthing_folders="$(grep -Po '(?<=path\=\")[^"]*' "${CONFIGXML}" | sort)"

# get info in a tabular format via a temp-file
TMP_FILE=$(get_tmp_file stconflict)
echo "Modification time|File size|File Name" > "${TMP_FILE}"
while IFS= read -r line; do
    getconflicts "${line}" | xargs -r0 stat -c '%y|%s B|%n' >> "${TMP_FILE}"
done <<< "${syncthing_folders}"

echo ""
column -s "|" -t "${TMP_FILE}"  # pretty print table

echo -e "\nFor sync-mess cleaning see: https://github.com/didi1357/SyncMessCleaner"
rm -rf "${TMP_FILE}"
