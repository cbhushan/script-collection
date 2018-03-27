#!/bin/bash

topdir=$(cd "$1"; pwd)
curdir=$(pwd)

exiftool=/home/cbin/Image-ExifTool-10.86/exiftool
cd "$topdir"

for file in *; do
    [ -e "$file" ] || continue
    cmd="$exiftool \
         -all= \
         -TagsFromFile @ \
         -DateTimeOriginal \
         -DateTimeDigitized -CreateDate \
         -DateTime -ModifyDate \
         -GPSLatitude -GPSLatitudeRef \
         -GPSLongitude -GPSLongitudeRef \
         -GPSAltitude -GPSAltitudeRef \
         $file"
    echo "$cmd"
    eval "$cmd"
done

cd "$curdir"
