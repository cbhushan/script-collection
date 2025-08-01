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
import numpy as np


paper_size_inch = {  # (x-inch, y-inch)
    'A4': (8.3, 11.7),
    'Half-A4': (8.3, 5.85),
    'Letter': (8.5, 11.0),
    'Half-Letter': (8.5, 5.5),
}


def image_arr(image):
    """
    Returns numpy array from input.
    Input can be PIL.Image or np.ndarray.

    Returns:
        I: np.ndarray of the input
        input_is_image: True when input is PIL.Image.Image. 
                        False otherwise.
    """
    if isinstance(image, Image.Image):
        I = np.asarray(image)
        input_is_image = True

    elif isinstance(image, np.ndarray):
        I = image.copy()
        input_is_image = False

    else:
        raise ValueError(f'Unknown format: {type(image)}')
    
    return I, input_is_image


def pil_image(arr, ref_image):
    """
    Returns PIL.Image object created from input numpy array.
    """
    if isinstance(arr, Image.Image):
        return arr
    
    elif isinstance(arr, np.ndarray):
        image = Image.fromarray(arr)

    else:
        raise ValueError('Unknown format')
    
    # copy some sort of header from ref_image
    #  image = image.copy_stuff(ref_image)
    return image


def rescale_to_8bit(img):
    """Rescale min-max to 8-bit range [0, 255]"""
    arr, input_is_image = image_arr(img)
    
    i_min, i_max = arr.min(), arr.max()
    out_arr = 255.0 * (arr - i_min) / (i_max - i_min)
    out_arr = np.uint8(out_arr)
    
    if input_is_image:
        return pil_image(out_arr, img)
    else:
        return out_arr


def window_intensity(image, quantile=[0.006, 0.994]):
    """
    Window image intensity to a given quantile range.

    Args:
        image: PIL.Image or np.ndarray
        quantile: 'min-max' or a list/tuple of two values (e.g. [0.006, 0.994])
                   If quantile is 'min-max', then stretch to min-max range.
                   If quantile is a list or tuple of two values, then stretch to that quantile range.
    
    Returns:
        out_img: PIL.Image or np.ndarray with intensity windowed to the given quantile range.
                 When input is PIL.Image, output is also PIL.Image with 8-bit depth. 
                 Otherwise, output is np.ndarray with float values in range [0, 1].
    """

    I, input_is_image = image_arr(image)
    assert I.ndim == 2, 'input image must be single channel (grayscale image)'

    if isinstance(quantile, str) and quantile == 'min-max':
        i_min, i_max = I.min(), I.max()
    
    elif isinstance(quantile, (list, tuple, np.array)) and len(quantile) == 2:
        i_min, i_max = np.quantile(I, quantile)

    else:
        raise ValueError(f'Unsupported quantile input = {quantile}')

    # scale
    out_img = (I - i_min) / (i_max - i_min)
    out_img[out_img < 0] = 0
    out_img[out_img > 1] = 1

    if input_is_image:
        out_img = rescale_to_8bit(out_img)
        return pil_image(out_img, image)
    else:
        return out_img


def crop(image, size_inch):
    """Crops image as per desired paper size"""
    if not isinstance(image, Image.Image):
        logging.warning('Input is not PIL.Image. Will skip crop()')
        return image
    
    if 'dpi' not in image.info:
        logging.warning('Can not find DPI of input. Will skip crop()')
        return image
    
    if size_inch in paper_size_inch:
        xinch, yinch = paper_size_inch[size_inch]
    else:
        logging.warning(f'Unknown size_inch input: {size_inch}. Will skip crop()')
        return image

    try:
        xres, yres = image.info['dpi']

        o_size = int(math.ceil(xres * xinch)), int(math.ceil(yres * yinch))
        o_size = np.minimum(o_size, image.size)

        I = np.asarray(image)
        I_crp = I[:o_size[1], :o_size[0]]  # b/c numpy & PIL indexing are in opposite order!
        img_crp = pil_image(I_crp, image)
        
    except Exception as e:
        logging.error(f'Encoutered error while cropping. Will skip crop():\n\n {traceback.format_exc()}')
        img_crp = image

    return img_crp


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
    """
    Re-orients the image matrix to match to display matrix. Applies operation corresponding to
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
    """
    Rescale image by rescale_factor, maintaining aspect ratio (as much as possible).
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
