#!/bin/bash
read -r -d '' USAGE << EOM
This script concatenates videos with identical codecs or concatenable container.
Use -demux option for video with same codec, like those recoded by same video 
camera, eg: dashbaord, same phone etc.
Use -cat for concatenable containers, which allows file-level concatenation of 
files, eg: MPEG-1, MPEG-2 PS, DV etc.

Usage:
   $0 </path/to/video-directory> </path/to/output-file.ext> <-demux or -cat>  [<ext>]
   $0 </path/to/video-list.txt>  </path/to/output-file.ext> -demux  [<ext>]

It uses ffmpeg with concat demuxer or concat protocol as described here:
http://trac.ffmpeg.org/wiki/Concatenate
http://ffmpeg.org/faq.html#How-can-I-concatenate-video-files

Copyright C Bhushan; Licensed under the Apache License v2.0.
https://github.com/cbhushan/script-collection
EOM

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
. "$script_dir"/../bash-functions.sh

assert_program_is_available ffmpeg
FFMPEG="$(command -v ffmpeg)"

if [ "$#" -lt 3 ] || [ "$#" -gt 4 ] ; then
    echo -e "Incorrect usage: Illegal number of parameters!\n"
    echo "${USAGE}"
    exit 1

elif [ "$#" -eq 4 ] ; then
    EXT="$4"

else
    filename="$(basename -- "${2}")"
    EXT="${filename##*.}"
    echo "No extesion specified. Using extension from output-file: ${EXT}"
fi

case "$3" in

  -demux)
    use_demux=true
    ;;

  -cat)
    use_demux=false
    ;;

  *)
    echo -n "ERROR: Unknown flag for third argument: ${3}"
    echo "${USAGE}"
    exit 1
    ;;
esac


mkdir -p "$(dirname "${2}")"
out_file="$(realpath "${2}")"
if [ -f "$out_file" ] ; then
    echo "ERROR: Output file already exists: $out_file"
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
    if [ "$use_demux" = true ] ; then
        tmp_list=$(mktemp)
        for f in "${srcdir}"/*.${EXT}; do
            echo "file '$f'" >> "$tmp_list"
        done
        list_file="$tmp_list"
    
    else
        file_list=$(ls "${srcdir}"/*.${EXT} | xargs printf '%s|')
        
    fi
    
elif [ -f "$1" ] ; then
    list_file="$1"
    if [ "$use_demux" = false ] ; then
        echo "Error: video-list.txt can only be used with -demux flag."
        exit 1
    fi
else
    echo "Error: Directory/File not found or does not exists: $1"
    exit 1
fi

cmd="$FFMPEG -f concat -safe 0 -i \"${list_file}\" -c copy \"${out_file}\""
echo "${cmd}"
eval "${cmd}"

if [ -n "$tmp_list" ]; then # set or none-empty
    rm "$tmp_list"
fi
