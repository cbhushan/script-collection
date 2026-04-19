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
import logging
from datetime import datetime
import subprocess
import json

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


def stretch_contast(img, quantile=[0.02, 0.99]):
    """
    Stretches contrast of input RGB Image.
    It applies linear stretching on lightness channel in LAB space.
    Assumes input is RGB without checks.
    """
    pimg = pil_image(img, None)

    lab_img = pimg.convert('LAB')  # L*a*b color space; 8-bit integers
    lab_arr = np.asarray(lab_img)

    # stretch contrast on lightness channel; retains color
    l_arr = lab_arr[..., 0]  # lightness channel
    l_arr_new = window_intensity(l_arr, quantile=quantile)
    l_arr_new = rescale_to_8bit(l_arr_new)

    lab_arr_new = lab_arr.copy()
    lab_arr_new[..., 0] = l_arr_new

    lab_img_new = Image.fromarray(lab_arr_new, mode='LAB')
    rgb_img_new = lab_img_new.convert('RGB')
    return rgb_img_new


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
    """
    Returns exif metadata in form of a dictionary.
    Implemented to gracefully return None in case or error
    """
    try:
        if isinstance(img, Image.Image):
            exif_dict = piexif.load(img.info["exif"])
        else:
            exif_dict = piexif.load(img)
        return exif_dict

    except Exception as e:
        print(f'Error while processing img = {img}')
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
        assert os.path.isfile(img), f'File not found: {img}'
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


def parse_datettime_str(s):
    """
    Parses common data-time strings & returns datetime.datetime object.
    Returns None when input is in unexpected format.
    """
    if s is None:
        return None
    s = str(s).strip()

    # try ISO-like strings first (handle trailing Z)
    try:
        if s.endswith('Z'):
            s2 = s[:-1] + '+00:00'
            return datetime.fromisoformat(s2)
        return datetime.fromisoformat(s)
    except Exception:
        pass

    # try common formats
    fmts = [
        '%Y:%m:%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y%m%d%H%M%S',
    ]
    for f in fmts:
        try:
            return datetime.strptime(s, f)
        except Exception:
            continue

    # final fallback: try to extract leading 19/10 char timestamp
    try:
        # common exif format 'YYYY:MM:DD HH:MM:SS'
        if len(s) >= 19:
            cand = s[:19]
            return datetime.strptime(cand, '%Y:%m:%d %H:%M:%S')
    except Exception:
        pass

    return None


def captured_datetime(exif_data):
    """
    Returns best estimate of date-time when the image / video was captured.
    if available, from the provided
    exif_data (obtained through get_exif_data above)
    """
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


def captured_datetime_ffprobe(path):
    """
    Uses ffprobe to try to extract captured datetime.
    """
    result = {'datetime': None, 'unix': np.nan, 'source': None, 'raw': None}
    assert os.path.isfile(path), f'File not found: {path}'

    try:
        cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json',
               '-show_format', '-show_streams', path]
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        info = json.loads(out)

        candidates = []
        if isinstance(info, dict):
            fmt = info.get('format', {})
            tags = fmt.get('tags', {}) if isinstance(fmt, dict) else {}
            if isinstance(tags, dict):
                for k in ('creation_time', 'Creation_time', 'creatioN_time'):
                    if k in tags:
                        candidates.append(tags[k])

            streams = info.get('streams', [])
            for s in streams:
                if isinstance(s, dict):
                    stags = s.get('tags', {})
                    if isinstance(stags, dict) and 'creation_time' in stags:
                        candidates.append(stags['creation_time'])

        for s in candidates:
            dt = parse_datettime_str(s)
            if dt is not None:
                result['datetime'] = dt
                result['unix'] = (dt - datetime(1970, 1, 1, tzinfo=dt.tzinfo)).total_seconds() if isinstance(dt, datetime) else np.NaN
                result['source'] = 'ffprobe'
                result['raw'] = s

                return result  # return the first found candidate

    except Exception: # ffprobe not installed or failed - move to next method
        return result


def captured_datetime_exiftool(path):
    """
    """
    assert os.path.isfile(path), f'File not found: {path}'
    result = {'datetime': None, 'unix': np.nan, 'source': None, 'raw': None}
    keys = ['CreateDate', 'Create Date', 'MediaCreateDate', 'Media Create Date',
            'DateTimeOriginal', 'CreationDate', 'ModifyDate', 'FileModifyDate', 'Date/Time Original']

    cmd = ['exiftool', '-json', path]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        arr = json.loads(out)
        if isinstance(arr, list) and len(arr) > 0 and isinstance(arr[0], dict):
            info = arr[0]
            for k in keys:
                if k in info:
                    raw = info[k]
                    dt = parse_datettime_str(raw)
                    if dt is not None:
                        result['datetime'] = dt
                        result['unix'] = (dt - datetime(1970, 1, 1)).total_seconds() if isinstance(dt, datetime) else np.NaN
                        result['source'] = 'exiftool'
                        result['raw'] = raw
                        return result
    except Exception:
        return result


def captured_datetime_from_video(path):
    """
    Extract capture datetime for a video file.

    Strategy (in order):
      1. ffprobe (preferred) - looks for creation_time in format or stream tags
      2. exiftool (if installed) - checks common date/time tags
      3. file modification time (os.path.getmtime)

    Returns:
        dict with keys:
          - 'datetime': datetime.datetime object or None
          - 'unix': float unix timestamp or np.NaN
          - 'source': one of 'ffprobe', 'exiftool', 'file_mtime', or 'none'
          - 'raw': raw string that was parsed (if any)
    """


    # 2) try exiftool (if available)

    # 3) fallback to file modification time
    try:
        mtime = os.path.getmtime(path)
        dt = datetime.fromtimestamp(mtime)
        result['datetime'] = dt
        result['unix'] = mtime
        result['source'] = 'file_mtime'
        result['raw'] = None
        return result
    except Exception:
        pass

    return result
