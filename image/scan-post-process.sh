#!/bin/bash
read -r -d '' USAGE << EOM
This script can be used as post-processing script for Gnome Simple-Scan 
when scanning text-heavy documents.

For reference, at the time of writing the arguments from simple-scan are:
  arg #1 - the mime type, eg application/pdf
  arg #2 - whether or not to keep a copy of the original file
  arg #3 - the filename. eg: "/path/to/scanned/multi-pages.png"
  arg #4 .. N - postprocessing script arguments entered in preferences

Hence, this script needs atleast three arguments. 
Although, only 3rd argument is used by this script.

Usage:
   ${0} <mime> <keep_orig> <filename>

Inspired by: https://gist.github.com/marcosrogers/fc0250a52490e92ab8293bd781231a7e

Copyright C Bhushan; Licensed under the Apache License v2.0.
https://github.com/cbhushan/script-collection

EOM

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
# . "$script_dir"/../bash-functions.sh

if [ "$#" -lt 3 ]; then
    echo "${USAGE}"
    exit 120
fi

# inputs
filename="$3"
keep_original="$2"  # ignored

# consts
LOGFILE=/mnt/data2/tmp/scan-post-process.log
TEMPDIR="$(mktemp -d)"
DOCKERIMAGE="jbarlow83/ocrmypdf:v16.10.0"
DOCKERARGS="--rm -i --user "$(id -u):$(id -g)" -v ${TEMPDIR}:${TEMPDIR} -v /mnt:/mnt -v /home:/home"
OCRMYPDF="docker run ${DOCKERARGS} ${DOCKERIMAGE} -v 1 -O1"
IMG2PDF="docker run ${DOCKERARGS} --entrypoint img2pdf ${DOCKERIMAGE} -v"

# Enable debugging only for function
function optimize_ocr() {
  (
    echo "$(date -u)"
    echo "TEMPDIR=${TEMPDIR}"
    echo "filename=${filename}"

    set -x

    /home/chitresh/opt/miniforge3/envs/scan_docs/bin/python "${script_dir}/optimize-scanned.py" \
    -i "${filename}" \
    -o "${TEMPDIR}" \
    --out-format tiff

    ${IMG2PDF} -o "${TEMPDIR}/merged.pdf" ${TEMPDIR}/*.tiff

    ${OCRMYPDF} "${TEMPDIR}/merged.pdf" "${filename}.pdf"

  )
}


# take action based on extension
filename_base="$(basename -- "$filename")"

case "${filename_base##*.}" in
    pdf)
        ${OCRMYPDF} --force-ocr "${filename}" "${filename}"  |& tee "${LOGFILE}"
        ;;
    png|tiff|jpg|jpeg)
        optimize_ocr |& tee "${LOGFILE}"
        ;;
    *)
        echo "Unknown file extension; no action."  |& tee "${LOGFILE}"
        ;;
esac

rm -rf ${TEMPDIR}
