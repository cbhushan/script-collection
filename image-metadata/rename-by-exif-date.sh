#!/bin/bash
# Renames image files by using exif date information to following format:
#    %Y%m%d_%H%M%S_xxxxxxxxxx.ext
#
# It uses exiftool for all operations.
#
# Copyright C Bhushan; Licensed under the Apache License v2.0.
# https://github.com/cbhushan/script-collection
#

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
. "$script_dir"/../bash-functions.sh


if [ -n "$EXIFTOOL" ]; then # env set & none empty
    if ! [ -x "$EXIFTOOL" ]; then
    echo "EXIFTOOL executable does not exists or not executable: $EXIFTOOL"
    echo "EXIFTOOL environment variable is not set correctly. It must be set in order to use $0"
    echo "exiting.."
    exit 1
    fi
    
else
    assert_program_is_available exiftool
    EXIFTOOL="$(command -v exiftool)"
fi

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ] ; then
    echo "Incorrect usage: Illegal number of parameters!"
    echo -e "\nThis script renamed image file using date from exif information."
    echo -e "Usage:\n\t $0 </path/to/src-directory> </path/to/destination-directory> [--use-random]"
    exit 1
fi

if [ -d "$1" ] ; then
    srcdir=$(cd "$1"; pwd)
else
    echo "Error: Directory not found or does not exists: $1"
    exit 1
fi

mkdir -p "$2"
destdir=$(cd "$2"; pwd)

if [ "$srcdir" -ef "$destdir" ] ; then
    echo "Error: Source and destination directories must be different!"
    exit 1
fi

if [ "$#" -eq 3 ] && [ "$3" = "--use-random" ] ; then
    use_random=true
else
    use_random=false
fi

shopt -s nullglob # Sets nullglob
shopt -s nocaseglob # Sets nocaseglob

failed_files=()
for file in "${srcdir}"/*.{jpg,jpeg,png,mov,mp4} ; do
    filename=$(basename -- "$file")
    extension="${filename##*.}"
    if [ "$use_random" = true ] ; then
        suffix=$(random_string 12)
    else
        suffix="${filename%.*}"
    fi
    
    date_str=$("$EXIFTOOL" -d '%Y%m%d_%H%M%S' -DateTimeOriginal -s3 "${file}")
    if [ -z "${date_str}" ] ; then
        date_str=$("$EXIFTOOL" -d '%Y%m%d_%H%M%S' -CreateDate -s3 "${file}")
    fi
    
    if [ -n "$date_str" ] ; then
        new_name="$destdir"/"$date_str"_"$suffix"."$extension"
    else
        new_name="$destdir"/"$filename"
    fi

    cmd="cp -d --preserve=all \"${file}\" \"${new_name}\""
    echo "${cmd}"

    eval "${cmd}"
    if [ $? -ne 0 ]; then
        failed_files+=("$file\n")
    fi
done

shopt -u nocaseglob # Unsets nocaseglob
shopt -u nullglob # Unsets nullglob

if [ ${#failed_files[@]} -gt 0 ] ; then
    echo "Failed files:"
    echo "${failed_files[@]}"
fi

