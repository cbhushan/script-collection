#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This script print a few tags from exif metadata as comma separated values, with intention of batch
filtering and processing.

Copyright 2018 C Bhushan; Licensed under the Apache License v2.0.
https://github.com/cbhushan/script-collection

Some parts of this script are derived from  a GitHub Gist by Eran Sandler at
https://gist.github.com/erans/983821, which is licensed under MIT license.

@author: C Bhushan
"""

import os
import sys
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime
import traceback
import numpy as np
from pandas.compat import StringIO
import pandas as pd

def get_exif_data(image):
    """Returns a dictionary from the exif data of an PIL Image item. Also converts the GPS Tags"""
    exif_data = {}
    info = image._getexif()
    if info:
        for tag, value in info.items():
            decoded = TAGS.get(tag, tag)
            if decoded == "GPSInfo":
                gps_data = {}
                for t in value:
                    sub_decoded = GPSTAGS.get(t, t)
                    gps_data[sub_decoded] = value[t]

                exif_data[decoded] = gps_data
            else:
                exif_data[decoded] = value
    return exif_data

def _get_if_exist(data, key):
    if key in data:
        return data[key]
    return None

def _convert_to_degress(value):
    """Helper function to convert the GPS coordinates stored in the EXIF to degress in float format"""
    d0 = value[0][0]
    d1 = value[0][1]
    d = float(d0) / float(d1)

    m0 = value[1][0]
    m1 = value[1][1]
    m = float(m0) / float(m1)

    s0 = value[2][0]
    s1 = value[2][1]
    s = float(s0) / float(s1)

    return d + (m / 60.0) + (s / 3600.0)

def get_lat_lon(exif_data):
    """Returns the latitude and longitude, if available, from the provided
    exif_data (obtained through get_exif_data above)"""
    lat = None
    lon = None

    if "GPSInfo" in exif_data:
        gps_info = exif_data["GPSInfo"]

        gps_latitude = _get_if_exist(gps_info, "GPSLatitude")
        gps_latitude_ref = _get_if_exist(gps_info, 'GPSLatitudeRef')
        gps_longitude = _get_if_exist(gps_info, 'GPSLongitude')
        gps_longitude_ref = _get_if_exist(gps_info, 'GPSLongitudeRef')

        if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
            lat = _convert_to_degress(gps_latitude)
            if gps_latitude_ref != "N":
                lat = 0 - lat

            lon = _convert_to_degress(gps_longitude)
            if gps_longitude_ref != "E":
                lon = 0 - lon
    return {'latitude':lat, 'longitude':lon}



def get_datetime(exif_data):
  """Returns all the three dateTime if available, from the provided
  exif_data (obtained through get_exif_data above)"""
  dt_dict = {}
  dt_tags = ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']
  for tag in dt_tags:
    dt_dict[tag] = None
    dt_dict[tag+'_unix'] = np.NaN
    if tag in exif_data:
      dt_info = exif_data[tag]
      dt_dict[tag] = dt_info
      try: # convert to datatime object
        dt_obj = datetime.strptime(dt_info, '%Y:%m:%d %H:%M:%S')
        dt_dict[tag+'_unix'] = (dt_obj - datetime(1970,1,1)).total_seconds()
      except Exception:
        print('Could not convert string to datetime object:')
        print(traceback.format_exc())
  return dt_dict


def get_exif_str_dict(exif_data=None):
  if exif_data is None:
    exif_str = 'DateTime,DateTimeOriginal,DateTimeDigitized,\
                DateTime_unix,DateTimeOriginal_unix,DateTimeDigitized_unix,\
                latitude,longitude'
    df = pd.read_csv(StringIO(exif_str))
    exif_dict = {}
    for cl in df.columns:
      key = cl.strip()
      exif_dict[key] = []

  else:
    exif_dict = get_lat_lon(exif_data)
    exif_dict.update(get_datetime(exif_data))
    exif_str = '%s,%s,%s,%f,%f,%f,%s,%s'%(exif_dict['DateTime'],
                                 exif_dict['DateTimeOriginal'],
                                 exif_dict['DateTimeDigitized'],
                                 exif_dict['DateTime_unix'],
                                 exif_dict['DateTimeOriginal_unix'],
                                 exif_dict['DateTimeDigitized_unix'],
                                 exif_dict['latitude'],
                                 exif_dict['longitude'])

  return(exif_str, exif_dict)

if __name__ == "__main__":
  if len(sys.argv)<2 or len(sys.argv)>3:
    print("Prints and, optionally, saves CSV file with date and location meta tags.")
    print("Usage: %s <path/to/file-or-folder> [<path/to/output.csv>]"%sys.argv[0])

  header, pd_dict = get_exif_str_dict(None)
  if os.path.isfile(sys.argv[1]):
    image = Image.open(sys.argv[1]) # load an image through PIL's Image object
    exif_data = get_exif_data(image)
    exif_str, _ = get_exif_str_dict(exif_data)
    print(header)
    print(exif_str)

  elif os.path.isdir(sys.argv[1]):
    dirname = sys.argv[1]
    files = os.walk(dirname).next()[2]
    files.sort()

    header = 'filename,%s'%header
    pd_dict['filename'] = []

    print(header)
    for fn in files:
      rt, ext = os.path.splitext(fn)
      ext = ext.lower()
      if ext in ['.jpg', '.jpeg', '.tiff', '.png']:
        image = Image.open(os.path.join(dirname, fn))
        exif_data = get_exif_data(image)
        exif_str, exif_dict = get_exif_str_dict(exif_data)

        pd_dict['filename'].append(fn)
        for key, val in exif_dict.items():
          pd_dict[key].append(val)

        print('%s,%s'%(fn,exif_str))

    if len(sys.argv)>2:
      df = pd.DataFrame(pd_dict)
      df = df.sort_values(by=['DateTimeOriginal_unix', 'filename'])
      df['shift_mins'] = (df.DateTimeOriginal_unix - df.DateTimeOriginal_unix.min())/60.0

      # re-arrange columns
      new_cols = ['filename']
      for cl in df.columns:
        if cl not in new_cols:
          new_cols.append(cl)
      df = df.ix[:, new_cols]
      df.to_csv(sys.argv[2], index=False)

