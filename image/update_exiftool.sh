#!/usr/bin/env bash
read -r -d '' USAGE << EOM
This script downloads the latest ExifTool from official website
and extracts it into the target folder.
It also creates a symlink pointing to the latest version.

Usage:
   $0 </path/to/target-directory>

Copyright C Bhushan; Licensed under the Apache License v2.0.
https://github.com/cbhushan/script-collection
EOM

set -euo pipefail

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
. "${script_dir}/../bash-functions.sh"

expect_args target_folder -- "$@"
expect_existing "${target_folder}"
target_folder="$(readlink -m "${target_folder}")"

# Find the latest tar.gz
BASE_URL="https://exiftool.org"
LATEST_TAR=$(curl -s "$BASE_URL" | grep -oE 'Image-ExifTool-[0-9.]+\.tar\.gz' | head -n1)

if [[ -z "$LATEST_TAR" ]]; then
    echo "Error: Could not find latest ExifTool archive." >&2
    exit 1
fi
echo "Latest version found: $LATEST_TAR"


## check if the latest version already exists
LATEST_NAME="${LATEST_TAR%.tar.gz}"
destination_folder="${target_folder}/${LATEST_NAME}"
if [ -d "${destination_folder}" ]; then
  echo "[DONE] Latest version already exists at: ${destination_folder}"
  exit 0
fi


## Download the latest version
DWLD_URL="${BASE_URL}/${LATEST_TAR}"
pushd "${target_folder}"
echo "Fetching ${DWLD_URL}"
curl -L -O --progress-bar "${DWLD_URL}"

extract_archive_into "${LATEST_TAR}"  "${destination_folder}" --strip-components=1

rm -f ./latest
ln -s "${destination_folder}" ./latest

rm -f "${LATEST_TAR}"
popd


# run test
echo "Test latest ExifTool..."
pushd "${destination_folder}"
perl Makefile.PL
make test
popd


echo "[DONE] Updated the latest version at: ${destination_folder}"
echo "Launch exiftool using symlinked version:"
echo "   ${target_folder}/latest/exiftool"
echo " ------------------------------------------------------"
echo "Here is the version info:"
echo

set -x
${target_folder}/latest/exiftool -ver
set +x

