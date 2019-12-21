#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generic helper functions for working with images.

Copyright 2018 C Bhushan; Licensed under the Apache License v2.0.
https://github.com/cbhushan/script-collection

@author: C Bhushan
"""
from __future__ import absolute_import, division, print_function, unicode_literals
import os
import sys
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import traceback
import piexif
import math


def get_exif_dict(img):
    """Returns exif metadata in form of a dictionary.
    Implemented to gracefully return None in case or error"""
    try:
        if isinstance(img, Image.Image):
            exif_dict = piexif.load(img.info["exif"])
        else:
            exif_dict = piexif.load(img)
        return exif_dict

    except Exception as e:
        print('Error while processing: %s' % img)
        print('img must be either filename or PIL.Image object')
        print(traceback.format_exc())
        return None


def display_size(img):
    """
    Returns display size (width, height) of the image, after decoding the orientation flag.
    Orientation flag has following convention (https://www.sno.phy.queensu.ca/~phil/exiftool/TagNames/EXIF.html) :
        1 = Horizontal (normal)
        2 = Mirror horizontal
        3 = Rotate 180
        4 = Mirror vertical
        5 = Mirror horizontal and rotate 270 CW
        6 = Rotate 90 CW
        7 = Mirror horizontal and rotate 90 CW
        8 = Rotate 270 CW
    """
    exif_dict = get_exif_dict(img)
    if exif_dict is None:
        raise ValueError('img_data must be either filename or PIL.Image object')

    if isinstance(img, Image.Image):
        im = img
    else:
        im = Image.open(img)

    matrix_w, matrix_h = im.size
    if (piexif.ImageIFD.Orientation in exif_dict["0th"]
            and exif_dict['0th'][piexif.ImageIFD.Orientation] in [5, 6, 7, 8]):
        display_w, display_h = matrix_h, matrix_w
    else:
        display_w, display_h = matrix_w, matrix_h

    return display_w, display_h


def rotate_to_display_orientation(img):
    """Re-orients the image matrix to match to display matrix. Applies operation corresponding to
    orientation flag to image-matrix.
    Similar to https://piexif.readthedocs.io/en/latest/sample.html#rotate-image-by-exif-orientation
    """
    if isinstance(img, Image.Image):
        im = img
    else:
        im = Image.open(img)
    exif_dict = get_exif_dict(im)

    im_out = im
    if piexif.ImageIFD.Orientation in exif_dict["0th"]:
        orientation = exif_dict["0th"].pop(piexif.ImageIFD.Orientation)

        if orientation == 2:
            im_out = im.transpose(Image.FLIP_LEFT_RIGHT)
        elif orientation == 3:
            im_out = im.rotate(180)
        elif orientation == 4:
            im_out = im.rotate(180).transpose(Image.FLIP_LEFT_RIGHT)
        elif orientation == 5:
            im_out = im.rotate(-90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
        elif orientation == 6:
            im_out = im.rotate(-90, expand=True)
        elif orientation == 7:
            im_out = im.rotate(90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
        elif orientation == 8:
            im_out = im.rotate(90, expand=True)

    exif_bytes = piexif.dump(exif_dict)
    return im_out, exif_bytes


def rescale_img(img, rescale_factor, resampler=Image.LANCZOS):
    """Rescale image by rescale_factor, maintaining aspect ratio (as much as possible).
    rescale_factor must be scalar and a value of less than one implies to reducing the size of the image.
    Returns PIL.Image object.
    """
    if isinstance(img, Image.Image):
        im = img
    else:
        im = Image.open(img)

    if rescale_factor == 1.0:
        im_out = im.copy()
    else:
        img_size = im.size
        new_size = [int(math.ceil(img_size[0] * rescale_factor)),
                    int(math.ceil(img_size[1] * rescale_factor))]
        im_out = im.resize((new_size[0], new_size[1]), resample=resampler)

    im_out.format = im.format
    return im_out
