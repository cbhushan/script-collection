#!/bin/bash
read -r -d '' USAGE << EOM
This script downloads the latest static build of ffmpeg from the BtbN FFmpeg-Builds 
repository on GitHub and extracts it into the target folder.
It also creates a symlink pointing to the latest version.

Obtains Linux x64 builds for v7.x branch of ffmpeg.

Usage:
   $0 </path/to/target-directory>

Copyright C Bhushan; Licensed under the Apache License v2.0.
https://github.com/cbhushan/script-collection
EOM

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
. "${script_dir}/../bash-functions.sh"

# as per https://ffmpeg.org/download.html#build-linux
GITHUB_API_URL="https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest"
DWLD_URL="https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-n7.1-latest-linux64-gpl-7.1.tar.xz"

expect_args target_folder -- "$@"
expect_existing "${target_folder}"
target_folder="$(readlink -m "${target_folder}")"

## figure out latest version
# Fetch first "name" & extracts its value. Example string below
#   "name": "Latest Auto-Build (2025-08-03 14:07)",
RELEASE_NAME=$(curl -s "$GITHUB_API_URL" | grep -oP -m 1 '"name":\s*"\K(.*?)(?=")')

# Extract timestamp without spaces and colons. Eg: "2025-08-03_1407"
LATEST_TIMESTAMP=$(echo "$RELEASE_NAME" | grep -oP '\(\K[^)]+' | sed 's/ /_/; s/://g')

echo "🌐 Latest release name: ${RELEASE_NAME}"
echo "🌐 Latest release timestamp: ${LATEST_TIMESTAMP}"
expect_vars LATEST_TIMESTAMP


## check if the latest version already exists
destination_folder="${target_folder}/ffmpeg-v7-${LATEST_TIMESTAMP}"
if [ -d "${destination_folder}" ]; then
  echo "✅ Latest version already exists at: ${destination_folder}"
  exit 0
fi


## Download the latest ffmpeg build
pushd "${target_folder}"
echo "Fetching ${DWLD_URL}"
curl -L -o "ffmpeg-n7.1-latest-linux64-gpl-7.1.tar.xz" --progress-bar "${DWLD_URL}"

extract_archive_into "ffmpeg-n7.1-latest-linux64-gpl-7.1.tar.xz"  "${destination_folder}" --strip-components=1

rm -f ./latest-v7
ln -s "${destination_folder}" ./latest-v7

rm -f "ffmpeg-n7.1-latest-linux64-gpl-7.1.tar.xz"
popd


echo "✅ Updated the latest version at: ${destination_folder}"
echo "Launch ffmpeg using symlinked version:"
echo "   ${target_folder}/latest-v7/bin/ffmpeg"
echo " ------------------------------------------------------"
echo "Here is the version info:"
echo 

set -x
${target_folder}/latest-v7/bin/ffmpeg
set +x
