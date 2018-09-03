#!/bin/bash
# Renames image files by using exif date information to following format:
#    %Y%m%d_%H%M%S_origfilename.ext
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
    
elif programExists exiftool ; then
    EXIFTOOL="$(command -v exiftool)"

else
    echo "Cannot find exiftool on current path"
    echo "exiftool tool must be installed or EXIFTOOL variable should be set correctly in order to use $0"
    echo "exiting.."
    exit 1
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

if [ "$#" -eq 3 ] && [ "$3" = "--use-random" ] ; then
    use_random=true
else
    use_random=false
fi

shopt -s nullglob # Sets nullglob
shopt -s nocaseglob # Sets nocaseglob

failed_files=()
for file in "$srcdir"/*.{jpg,jpeg,png,mov,mp4} ; do
    if [ "$use_random" = true ] ; then
	suffix=$(randomString 12)
    else
	filename=$(basename -- "$file")
	suffix="${filename%.*}"
    fi
    
    cmd="$EXIFTOOL \
    	 '-FileName<CreateDate' \
	 -d %Y%m%d_%H%M%S_$suffix.%%e \
         -o $destdir \
         \"$file\""
    
    echo -e "\t$cmd"
    eval "$cmd"
    if [ $? -ne 0 ]; then
	failed_files+=("$file\n")
    fi    
done

shopt -u nocaseglob # Unsets nocaseglob
shopt -u nullglob # Unsets nullglob

echo "Failed files:"
echo "${failed_files[@]}"
