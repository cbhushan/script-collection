#!/bin/bash
# This script moves images in sub-directory to input parent directory.
# Useful for moving images captured using Bokeh/portrait mode in recent smartphones.
#
# Copyright C Bhushan; Licensed under the Apache License v2.0.
# https://github.com/cbhushan/script-collection
#

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
if [ $# == 0 ] ; then
    echo "Usage:"
    echo -e "\t $0 </path/to/top-image-directory>"
    exit 1

elif [ ! -d "$1" ] ; then
    echo "Error: Directory not found or does not exists: $1"
    exit 1
fi

. "$script_dir"/../bash-functions.sh

top_dir=$(cd "$1" && pwd)

# iterate over directories and move images
shopt -s nullglob # Sets nullglob
shopt -s nocaseglob # Sets nocaseglob

for file in "$top_dir"/*/*.{jpg,jpeg,png} ; do
    bname=$(basename $(dirname "$file"))
    if [ "$bname" != ".picasaoriginals" ] ; then
	tarfname="$top_dir"/"$bname"_$(basename "$file")
	cmd="mv \"$file\" \"$tarfname\""
	echo "$cmd"
	eval "$cmd"
    fi
done

# delete empty folders
find "$top_dir" -type d -empty -delete

shopt -u nocaseglob # Unsets nocaseglob
shopt -u nullglob # Unsets nullglob

