#!/bin/bash
# This script concatenates videos with identical codecs, like those recoded by same video cameras (eg: dashbaord, same phone etc.).
# It uses ffmpeg with demuxer method as described here: http://trac.ffmpeg.org/wiki/Concatenate#demuxer
#
# Codes used across different video files must be identical to generate reasonable output!
#
# Copyright C Bhushan; Licensed under the Apache License v2.0.
# https://github.com/cbhushan/script-collection
#

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
. "$script_dir"/../bash-functions.sh

if program_is_available ffmpeg ; then
    FFMPEG="$(command -v ffmpeg)"

else
    echo "Cannot find ffmpeg on current path. It must be installed in order to use $0"
    echo "exiting.."
    exit 1
fi

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ] ; then
    echo "Incorrect usage: Illegal number of parameters!"
    echo -e "\nThis script concatenates videos with identical encoding, like those recoded by dashcam video cameras."
    echo -e "Usage:\n\t $0 </path/to/video-directory OR /path/to/video-list.txt>  </path/to/output-file.ext>  [<ext>]"
    exit 1

elif [ "$#" -eq 3 ] ; then
    EXT="$3"

else
    filename="$(basename -- "${2}")"
    EXT="${filename##*.}"
    echo "No extesion specified. Using extension from output-file: ${EXT}"
fi

mkdir -p "$(dirname "${2}")"
out_file="$(realpath "${2}")"
if [ -f "$out_file" ] ; then
    echo "Error: Output file already exists: $out_file"
    echo -e "\t Please remove output file to continue with merging! Exiting..."
    exit 1
fi

filename="$(basename -- "${out_file}")"
out_ext="${filename##*.}"
if [ "${out_ext}" != ${EXT} ] ; then
    echo "Error: extension of output file does not match extesion of input files!"
    echo -e "\t Input Extension files: ${EXT} \n\t Output file: ${out_file}"
    exit 1
fi


if [ -d "$1" ] ; then
    srcdir=$(cd "$1"; pwd)

    # check if files with specified extension exists
    count=$(ls -1 "${srcdir}"/*.${EXT} 2>/dev/null | wc -l)
    if [ $count -eq 0 ] ; then 
        echo "Error: No file found in source video folder with extension ${EXT}"
        echo -e "\t Source video folder file: ${srcdir}"
        exit 1
    fi 

    # create video-list file
    tmp_list=$(mktemp)
    for f in "${srcdir}"/*.${EXT}; do
        echo "file '$f'" >> "$tmp_list"
    done
    list_file="$tmp_list"
    
elif [ -f "$1" ] ; then
    list_file="$1"
    
else
    echo "Error: Directory/File not found or does not exists: $1"
    exit 1
fi

cmd="$FFMPEG -f concat -safe 0 -i $list_file -c copy $out_file"
echo "$cmd"
eval "$cmd"

if [ -n "$tmp_list" ]; then # set or none-empty
    rm "$tmp_list"
fi
