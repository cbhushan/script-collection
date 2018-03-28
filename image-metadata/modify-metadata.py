#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This script helps modifying exif tags in photos.

Copyright 2018 C Bhushan; Licensed under the Apache License v2.0.
https://github.com/cbhushan/script-collection

@author: C Bhushan
"""
import os
import sys
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime
from datetime import timedelta
import traceback
import argparse
import piexif
import math

sys.path.append(os.path.realpath(__file__))
import print_metadata


def get_exif_dict(img_file):
  try:
    exif_dict = piexif.load(img_file)
    return exif_dict
  except Exception as e:
    return None


def offset_datetime(exif_dict, t_sec):
  '''Offset datetime by t seconds, based on DateTimeOriginal. All other time stamps are
  over-written. t can be positive or negative.

  piexif.ImageIFD.DateTime
  piexif.ExifIFD.DateTimeDigitized
  piexif.ExifIFD.DateTimeOriginal
  '''
  curr_dt = exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal]
  dt_obj = datetime.strptime(curr_dt, '%Y:%m:%d %H:%M:%S')
  new_dt_obj = dt_obj + timedelta(seconds=t_sec)
  new_dt = new_dt_obj.strftime('%Y:%m:%d %H:%M:%S')

  exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = new_dt
  exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = new_dt
  exif_dict['0th'][piexif.ImageIFD.DateTime] = new_dt

  new_dt_str = new_dt_obj.strftime('%Y%m%d_%H%M%S')
  return (exif_dict, new_dt_str)



def latlon_to_GPSdict(lat, lon):
  def deg2dmstuple(degrees, second_decimal_digits=3):
    degrees = float(degrees)
    degs = math.floor(degrees)

    minsFloat = (degrees - degs) * 60.0
    mins = math.floor(minsFloat)

    secsFloat = (minsFloat - mins) * 60.0
    sec_fmt = 10**second_decimal_digits
    secs = round(secsFloat * sec_fmt)
    return ((int(degs), 1), (int(mins), 1),(int(secs), sec_fmt))

  GPS_dict = {}
  if lat < 0:
    GPS_dict[piexif.GPSIFD.GPSLatitudeRef] = 'S'
  else:
    GPS_dict[piexif.GPSIFD.GPSLatitudeRef] = 'N'

  if lon < 0:
    GPS_dict[piexif.GPSIFD.GPSLongitudeRef] = 'W'
  else:
    GPS_dict[piexif.GPSIFD.GPSLongitudeRef] = 'E'

  GPS_dict[piexif.GPSIFD.GPSLatitude] = deg2dmstuple(abs(lat))
  GPS_dict[piexif.GPSIFD.GPSLongitude] = deg2dmstuple(abs(lon))
  return GPS_dict


def update_location(exif_dict, lat, lon, overwrite=True):
  ''' Lat, lon must be specified as floating point degree values.

   "When adding GPS information to an image, it is important to set all of
   the following tags: GPSLatitude, GPSLatitudeRef, GPSLongitude,
   GPSLongitudeRef, and GPSAltitude and GPSAltitudeRef if the altitude
   is known. ExifTool will write the required GPSVersionID tag automatically if
   new a GPS IFD is added to an image."
      -- http://owl.phy.queensu.ca/~phil/exiftool/TagNames/GPS.html

  '''
  if not overwrite and piexif.GPSIFD.GPSLatitude in exif_dict['GPS']:
    return exif_dict

  GPS_dict = latlon_to_GPSdict(lat, lon)
  GPS_dict[piexif.GPSIFD.GPSAltitudeRef] = 0 # measure from sea level
  GPS_dict[piexif.GPSIFD.GPSAltitude] = (2300, 100) # 23 meters

  for k, v in GPS_dict.items():
    exif_dict['GPS'][k] = v
  return exif_dict


def print_exif(img_file):
    image = Image.open(img_file) # load an image through PIL's Image object
    exif_data = print_metadata.get_exif_data(image)
    exif_str, exif_dict = print_metadata.get_exif_str_dict(exif_data)
    print(exif_str)

def save_with_updated_metadata(img_file, geo_tag, offset_time, out_file,
                               prefix_filename_with_date):
  if geo_tag is None and offset_time is None:
    return

  exif_dict = piexif.load(img_file)
  if offset_time is not None:
    exif_dict, new_dt_str = offset_datetime(exif_dict, offset_time)
    if prefix_filename_with_date:
      hd, tl = os.path.split(out_file)
      out_file = os.path.join(hd, new_dt_str+'_'+tl)

  if geo_tag is not None:
    exif_dict = update_location(exif_dict, geo_tag[0], geo_tag[1])

  exif_bytes = piexif.dump(exif_dict)
  piexif.insert(exif_bytes, img_file, out_file)
  return out_file


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Modify exif metadata')
  parser.add_argument('--geo-tag', metavar='xx.xx', nargs=2, type=float, required=False,
                      help='Add geo location. Inputs in form of latitude and longitude in degrees')

  parser.add_argument('--offset-time', metavar='xx.xx', type=float, required=False,
                      help='Offset date-time tags by N seconds')

  parser.add_argument('-i', '--input',  metavar='/path/to/file-or-folder', required=True,
                      help='File or folder name')

  parser.add_argument('-o', '--output-dir', metavar='/path/to/folder', required=True,
                      help='File or folder name')

  parser.add_argument('--prefix-filename-with-date', default=False, action='store_true', required=False,
                      help='When used output filename is prefixed with datetime. Only used with --offset-time.')

  args = parser.parse_args()

  if not os.path.isdir(args.output_dir):
    raise ValueError('--output-dir must be an existing directory!')
  output_dir = os.path.abspath(args.output_dir)

  if os.path.isfile(args.input):
    img_file = os.path.abspath(args.input)
    hd, fn = os.path.split(img_file)
    input_dir = os.path.abspath(hd)

    if input_dir == output_dir:
       raise ValueError('--output-dir must be a different directory from source-image directory!')

    print('Original exif data: ')
    print_exif(img_file)

    out_file = os.path.join(output_dir, fn)
    saved_file = save_with_updated_metadata(img_file, args.geo_tag, args.offset_time, out_file,
                                            args.prefix_filename_with_date)

    print('Updated exif data: ')
    print_exif(saved_file)

  elif os.path.isdir(args.input):
    input_dir = os.path.abspath(args.input)
    files = os.walk(input_dir).next()[2]
    files.sort()

    if input_dir == output_dir:
       raise ValueError('--output-dir must be a different directory from source-image directory!')

    failed_processing = []
    for fn in files:
      rt, ext = os.path.splitext(fn)
      ext = ext.lower()
      if ext in ['.jpg', '.jpeg']:
        print('%s...'%fn)
        img_file = os.path.join(input_dir, fn)
        out_file = os.path.join(output_dir, fn)
        try:
          saved_file = save_with_updated_metadata(img_file, args.geo_tag, args.offset_time,
                                                  out_file, args.prefix_filename_with_date)
        except:
          failed_processing.append(fn)
          print('Error while processing:')
          print(traceback.format_exc())
          print('\n')

    if len(failed_processing)>0:
      print('Following files failed processing: ')
      for fn in failed_processing:
        print(fn)
  else:
    raise ValueError('File not found')

#dirname = '/mnt/data/tmp_dupe/test_folder'
#img_file = os.path.join(dirname, '5C2A4560.JPG')
#exif_dict = get_exif_dict(img_file)
#
#exif_dict, new_dt_str = offset_datetime(exif_dict, 2400*60)
#out_file = os.path.join(dirname, new_dt_str+'_5C2A4560.JPG')
#
#
#
#image = Image.open(img_file) # load an image through PIL's Image object
#e_data = print_metadata.get_exif_data(image)
#e_str, e_dict = print_metadata.get_exif_str_dict(e_data)
#
#
#im = Image.open('IMG_20180310_072313.jpg')
#
## save with no metadata
#data = list(im.getdata())
#image_clean = Image.new(im.mode, im.size)
#image_clean.putdata(data)
#image_clean.save("no-metadata_PIL.jpg") # this re-encodes the output image. Not good!
#
## This is fast, but saves "empty" metadata in it. Leaves behind XMP metadata if any
#piexif.remove('IMG_20180310_072313.jpg', 'no-metadata_piexif_remove.jpg')
#
## exiftool removes all metadata & reduces size a little as well
## GExiv2 solution: https://stackoverflow.com/a/19787239
#
#
## Modify exif,
## Hawaii coordinates: 19.8968 deg N, 155.5828 deg W
## NYC coordinates:    40.7128 deg N,  74.0060 deg W
#exif_dict = piexif.load(im.info["exif"])
#print(exif_dict.keys())
#
## list all GPU related keys:
#GPS_tags = vars(piexif.GPSIFD)
#for key, val in GPS_tags.items():
#  if 'GPS' in key:
#    store_val = None
#    if val in exif_dict['GPS']:
#      store_val = exif_dict['GPS'][val]
#      print('%s : %s'%(key, str(store_val)))
#
#exif_data = get_exif_data(im) # PIL
#
#
#exif_bytes = piexif.dump(exif_dict)
#image_clean.save("only-exif.jpeg", exif=exif_bytes)
#
#
## modify exif info
#w, h = im.size
#exif_dict["0th"][piexif.ImageIFD.XResolution] = (w, 1)
#exif_dict["0th"][piexif.ImageIFD.YResolution] = (h, 1)
#exif_bytes = piexif.dump(exif_dict)
#im.save(new_file, "jpeg", exif=exif_bytes)
#


