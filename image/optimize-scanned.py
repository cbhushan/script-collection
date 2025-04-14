#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This script optimizes scanned documents to produce small-sized binary images.

Copyright 2024 C Bhushan; Licensed under the Apache License v2.0.
https://github.com/cbhushan/script-collection

@author: C Bhushan
"""

from __future__ import absolute_import, division, print_function, unicode_literals
import os
import shutil
import sys
import math
from PIL import Image, ImageFile
import traceback
import tempfile
import copy
import logging
import argparse
import numpy as np
from scipy import signal
from skimage.filters import threshold_otsu, threshold_multiotsu
import pathlib

# Load pngs saved by GIMP with color profile https://gitlab.gnome.org/GNOME/gimp/-/issues/2111
ImageFile.LOAD_TRUNCATED_IMAGES = True  

# sys.path.append(os.path.realpath(__file__))
# import imghelper


paper_size_inch = {  # (x-inch, y-inch)
    'A4': (8.3, 11.7),
    'Half-A4': (8.3, 5.85),
    'Letter': (8.5, 11.0),
    'Half-Letter': (8.5, 5.5),
}

contrast_enhance_qunatiles = {
    'minmax': (0, 1),
    'auto': (0.006, 0.994),  # used to be gimp's default
}

output_formats = {
    'png': {"optimize": True},
    'tiff': {"compression": "group4"},
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
        raise ValueError('Unknown format')
    
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


def rescale_to_8bit(arr):
    """Rescale min-max to 8-bit range [0, 255]"""
    arr = np.asarray(arr)
    i_min, i_max = arr.min(), arr.max()
    out_img = 255 * (arr - i_min) / (i_max - i_min)
    out_img = np.uint8(out_img)
    return out_img


def otsu(image, n_class=2, nbins=256):
    """
    Perform Otsu's thresholding
    """
    I, input_is_image = image_arr(image)
    assert I.ndim == 2, 'input image must be single channel (grayscale image)'

    if n_class == 2:
        thresh = threshold_otsu(I, nbins=nbins)
        out_img = np.uint8(I > thresh)
    
    elif n_class > 2:
        thresholds = threshold_multiotsu(I, classes=n_class, nbins=nbins)
        out_img = np.digitize(I, bins=thresholds)  # generate multiple regions.

    else:
        raise ValueError('n_classes must be greater than 1')

    if input_is_image:
        out_img = rescale_to_8bit(out_img)
        return pil_image(out_img, image)
    else:
        return out_img


def median_filter(image, kernel_size=3):
    """
    Median filter image. kernel_size must be odd.
    """
    I, input_is_image = image_arr(image)
    assert I.ndim == 2, 'input image must be single channel (grayscale image)'

    out_img = signal.medfilt2d(I, kernel_size=kernel_size)

    if input_is_image:
        return pil_image(out_img, image)
    else:
        return out_img


def stretch_intensity(image, quantile=[0.006, 0.994]):
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


def input_file_list(arg_in):
    """
    Returns list of pathlib file-names to operate on. 
    arg_in can be the "save path" as returned by Gnome Simple Document scanner.
    """
    # find all files saved by Simple Docment scanner
    arg_in = pathlib.Path(arg_in)
    src_dir = arg_in.parent

    if arg_in.is_dir():  # input is directory - process all valid files in this top level directory; NOT recursive
        file_in = []
        for ext in ('.png', '.tiff', '.jpg', '.jpeg'):
            file_in = file_in + sorted(arg_in.glob('*' + ext))

    # input should be file
    elif arg_in.suffix not in ('.png', '.tiff', '.jpg', '.jpeg'):
        logging.warning(f'Unsupported file extension: {arg_in.suffix}. Inputs will NOT be processed.')
        file_in = []

    elif os.path.exists(arg_in):  # single file
        file_in = [arg_in]

    else:  # May be multiple files (as saved by Gnome Simple Document scanner)
        f_pattern = arg_in.stem + '-*' + arg_in.suffix  # file_in-*.ext
        file_in = sorted(src_dir.glob(f_pattern))  # file_in-*.ext

    return file_in


def process_file(fn, out_top, n_colors=2, crop_size=None, median_kernel_size=None, contrast_adjust='auto', 
                 set_dpi=None, keep_original=False, out_format='png', overwrite_fn_okay=False):
    """
    Process one file.
    ToDo: 
     - add Blurring if required
     - gray-scale dithering
    """
    out_file = out_top / f'{fn.stem}.{out_format}'
    if (out_file == fn) and not overwrite_fn_okay:
        msg = (f'[ERR] Input file and output file are same!\nInput: {fn}\nOutput: {out_file}.\n'
               f'\nEither change output directory or set overwrite_fn_okay to True')
        raise ValueError(msg)

    if keep_original == "true":
        orig_file = out_top /  f'orig_{fn.name}'
        shutil.copy2(fn, orig_file)

    save_kwargs = copy.deepcopy(output_formats[out_format])
    img_orig = Image.open(fn)
    img = img_orig.convert('L', dither=None)  # grayscale

    if crop_size is not None:
        img = crop(img, crop_size)

    I, _ = image_arr(img)

    oimg = stretch_intensity(I, contrast_enhance_qunatiles[contrast_adjust])

    if median_kernel_size is not None:
        oimg = median_filter(oimg, kernel_size=median_kernel_size)    

    oimg = otsu(oimg, n_class=n_colors)

    if out_format == 'tiff':
        if n_colors == 2:
            oimg = oimg > 0  # make it 1-bit/sample
            save_kwargs["compression"] = "group4"
        else:
            oimg = rescale_to_8bit(oimg)
            save_kwargs["compression"] = "lzma"
    else:  # pngs
        oimg = rescale_to_8bit(oimg)

    out_img = pil_image(oimg, img)

    if 'dpi' in img_orig.info:
        dpi_out = img_orig.info['dpi']
    elif set_dpi is not None:  # must be number
        dpi_out = (set_dpi, set_dpi)
    else:
        dpi_out = None

    out_file = out_top / f'{fn.stem}.{out_format}'

    if dpi_out is None:
        out_img.save(out_file, **save_kwargs)
    else:
        out_img.save(out_file, dpi=dpi_out, **save_kwargs)
    
    print(f'[INFO] Saved: {out_file}')
    return out_file


## === Main ====

parser = argparse.ArgumentParser(
    description='Optimizes scanned documents for archival purposes.',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
requiredNamed = parser.add_argument_group('Required named arguments')
requiredNamed.add_argument(
    '-i', '--input', required=True,
    help='Path to input filename (or directory). It can also be the "save path" as returned by Gnome Simple-Scan.')

requiredNamed.add_argument('-o', '--output-dir', help='Path to output folder/directory', required=True)

parser.add_argument("--out-format", choices=list(output_formats.keys()), 
                    help="Set output image format.", default='tiff')
parser.add_argument("--num-colors", type=int, help="number of colors in final image", default=2)
parser.add_argument("--crop-size", help="When set crops the input image to specified size.",
                    choices=list(paper_size_inch.keys()))
parser.add_argument("--contrast-adjust", help="Stretch intensity to adjust contrast",
                    choices=list(contrast_enhance_qunatiles.keys()), default='auto')
parser.add_argument("--median-kernel-size", help="Set kernel size for median filtering. When not specified, no median filtering is done.", 
                    type=int, default=None)
parser.add_argument("--set-dpi", help="Set DPI in image meta data.", type=float, default=None)


if len(sys.argv) == 1:
    parser.print_help(sys.stderr)
    sys.exit(1)

args = parser.parse_args()


file_in_list = input_file_list(args.input)
out_top = pathlib.Path(args.output_dir)
os.makedirs(out_top, exist_ok=True)


for fn in file_in_list:
    try:
        outfn = process_file(
            fn, out_top, 
            n_colors=args.num_colors, 
            crop_size=args.crop_size,
            contrast_adjust=args.contrast_adjust,
            median_kernel_size=args.median_kernel_size,
            set_dpi=args.set_dpi,
            out_format=args.out_format
        )
        logging.info(f'Saved {outfn}')
        
    except Exception:
        logging.error(f'Encoutered error while processing: {fn}:\n\n {traceback.format_exc()}')

