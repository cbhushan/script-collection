#!/bin/bash
# This script strips all metadata except date, location and color metadata from images.
# It uses exiftool for all operations. See link below for helpful shortcut tags:
#   https://sno.phy.queensu.ca/~phil/exiftool/TagNames/Shortcuts.html
#

if [ -z "$EXIFTOOL" ]; then # unset or empty
    echo "EXIFTOOL environment variable is not set correctly. It must be set in order to use $0"
    echo "exiting.."
    exit 1
elif [ ! -f "$EXIFTOOL" ]; then
    echo "EXIFTOOL executable does not exists: $EXIFTOOL"
    echo "EXIFTOOL environment variable is not set correctly. It must be set in order to use $0"
    echo "exiting.."
    exit 1
fi

if [[ "$#" -ne 2 ]]; then
    echo "Incorrect usage: Illegal number of parameters!"
    echo -e "\nThis script strips all metadata except date, location and color metadata from images."
    echo -e "Usage:\n\t $0 <src-directory> <destination-directory>"
    exit 1
fi

topdir=$(cd "$1"; pwd)
mkdir -p "$2"
destdir=$(cd "$2"; pwd)
curdir=$(pwd)

cd "$topdir"
num_files=$(ls -1 | wc -l)
COUNTER=1
for file in *; do
    [ -e "$file" ] || continue
    cmd="$EXIFTOOL \
         -all= \
         -TagsFromFile @ \
         -DateTimeOriginal \
         -DateTimeDigitized -CreateDate \
         -DateTime -ModifyDate \
         -GPSLatitude -GPSLatitudeRef \
         -GPSLongitude -GPSLongitudeRef \
         -GPSAltitude -GPSAltitudeRef \
         -ExifIFD:ColorSpace \
         -ExifIFD:Gamma \
         -InteropIFD:InteropIndex \
         -ICC_Profile \
         -Model \
         -ImageSize \
         -Quality \
         -o $destdir \
         $file"

    echo "$COUNTER/$num_files: $file"
    eval "$cmd"
    COUNTER=$((COUNTER + 1))
done

cd "$curdir"
