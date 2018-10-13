#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This script optimizes photo size for digital photo frames

Copyright 2018 C Bhushan; Licensed under the Apache License v2.0.
https://github.com/cbhushan/script-collection

@author: C Bhushan
"""
from __future__ import absolute_import, division, print_function, unicode_literals
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
import imghelper


def _get_orientation(width, height):
    if width >= height:
        return 'landscape'
    else:
        return 'portrait'


def reduce_size_for_photo_frame(img_file, out_file, photo_frame_size, reference_scale=1.3):
    """reference_scale is the scale-factor by which the resulting images are larger than photo_frame_size. """
    frame_width, frame_height = photo_frame_size
    frame_orientation = _get_orientation(frame_width, frame_height)
    ref_width, ref_height = frame_width * reference_scale, frame_height * reference_scale

    im = Image.open(img_file)
    img_width, img_height = imghelper.display_size(im)
    img_orientation = _get_orientation(img_width, img_height)

    # resize image
    if frame_orientation == img_orientation:
        rescale_factor = min(1.0, max(ref_width / img_width, ref_height / img_height))

    elif frame_orientation == 'landscape':
        rescale_factor = min(1.0, frame_width / img_width)

    else:  # frame_orientation == 'portrait'
        rescale_factor = min(1.0, frame_height / img_height)

    im_out = imghelper.rescale_img(im, rescale_factor)

    # add exif to preserve orientation
    exif_dict = imghelper.get_exif_dict(im)
    if piexif.ImageIFD.Orientation in exif_dict["0th"]:
        orientation = exif_dict["0th"][piexif.ImageIFD.Orientation]
    else:
        orientation = 1
    out_exif_dict = {"0th": {piexif.ImageIFD.Orientation:orientation}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
    out_exif_bytes = piexif.dump(out_exif_dict)

    im_out.save(out_file, exif=out_exif_bytes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Reduce size of images to optimize to that digital-photo-frame. '
                                                 'All exif information except orientation is also stripped!',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-i', '--input', metavar='/path/to/file-or-folder', required=True,
                        help='File or folder name')

    parser.add_argument('-o', '--output-dir', metavar='/path/to/folder', required=True,
                        help='Folder name')

    parser.add_argument('-f', '--frame-size', metavar='xx', nargs=2, type=int,
                        required=False, default=(1280, 800),
                        help='Pixel resolution of digital frame')

    parser.add_argument('-s', '--ref-scale', metavar='xx.xx', type=float, required=False, default=1.3,
                        help='Scale factor by which frame-size should be increased to obtain the reference size.')

    if len(sys.argv) < 2:
        parser.print_usage()
        sys.exit(1)

    args = parser.parse_args()

    if not os.path.isdir(args.output_dir):
        raise ValueError('--output-dir must be an existing directory!')
    output_dir = os.path.abspath(args.output_dir)

    if os.path.isfile(args.input):
        img_file = os.path.abspath(args.input)
        hd, fn = os.path.split(img_file)
        input_dir = os.path.abspath(hd)
        files = [fn]

    elif os.path.isdir(args.input):
        input_dir = os.path.abspath(args.input)
        files = os.walk(input_dir).next()[2]
        files.sort()

    else:
        raise ValueError('File/folder not found: %s' % args.input)

    if input_dir == output_dir:
        raise ValueError('--output-dir must be a different directory from source-image directory!')

    failed_processing = []
    for fn in files:
        rt, ext = os.path.splitext(fn)
        ext = ext.lower()
        if ext in ['.jpg', '.jpeg']:
            print('%s...' % fn)
            sys.stdout.flush()
            img_file = os.path.join(input_dir, fn)
            out_file = os.path.join(output_dir, fn)
            try:
                reduce_size_for_photo_frame(img_file, out_file, args.frame_size, reference_scale=args.ref_scale)
            except:
                failed_processing.append(fn)
                print('Error while processing: %s' % fn)
                print(traceback.format_exc())
                print('\n')

    if len(failed_processing) > 0:
        print('Following files failed processing: ')
        print('\n'.join(failed_processing))
