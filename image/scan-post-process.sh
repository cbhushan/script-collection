#!/bin/bash
#
# Set this file as the post-processing script in the simple-scan preferences.
# 
# For reference, at the time of writing the arguments from simple-scan are:
# $1    - the mime type, eg application/pdf
# $2    - whether or not to keep a copy of the original file
# $3    - the filename. eg: "/mnt/data/Main-shared/scanned/multi-pages.png"
# $4..N - postprocessing script arguments entered in preferences
# 
# https://gist.github.com/marcosrogers/fc0250a52490e92ab8293bd781231a7e

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
# . "$script_dir"/../bash-functions.sh

if [ "$#" -lt 3 ]; then
    echo "Need atleast three params. Only 3rd param is used. Usage:"
    echo "$0 <mime> <keep_orig> <filename>"
    exit 120
fi

# inputs
filename="$3"
keep_original="$2"  # ignored

# consts
LOGFILE=/mnt/data2/tmp/scan-post-process.log
TEMPDIR="$(mktemp -d)"
DOCKERARGS="--rm -i --user "$(id -u):$(id -g)" -v ${TEMPDIR}:${TEMPDIR} -v /mnt:/mnt -v /home:/home"
OCRMYPDF="docker run ${DOCKERARGS} jbarlow83/ocrmypdf -v 1 -O1"
IMG2PDF="docker run ${DOCKERARGS} --entrypoint /usr/local/bin/img2pdf jbarlow83/ocrmypdf -v"

# Enable debugging only for function
function optimize_ocr() {
  ( 
    echo "$(date -u)"
    echo "${TEMPDIR}"
    echo "filename=${filename}"

    set -x

    /home/chitresh/opt/miniconda3/envs/scan_docs/bin/python "${script_dir}/optimize-scanned.py" \
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
        ${OCRMYPDF} "${filename}" "${filename}"  |& tee "${LOGFILE}"
        ;;
    png|tiff|jpg|jpeg)
        optimize_ocr |& tee "${LOGFILE}"
        ;;
    *)
        echo "Unknown file extension; no action."  |& tee "${LOGFILE}"
        ;;
esac

rm -rf ${TEMPDIR}
