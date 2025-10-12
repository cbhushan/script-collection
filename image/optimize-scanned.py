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
from PIL import Image, ImageFile, ImageEnhance
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

sys.path.append(os.path.realpath(__file__))
# import imghelper
from imghelper import image_arr, pil_image, rescale_to_8bit, crop, window_intensity, paper_size_inch


contrast_enhance_qunatiles = {
    'minmax': (0, 1),
    'auto': (0.006, 0.994),  # used to be gimp's default
}

# dict of output-format:saving kwargs; as they are format dependent
output_formats = {
    'png': {"optimize": True},
    'tiff': {"compression": "group4"},
}



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
        if n_class > 5:
            print(f"[WARN] Otsu multi-thresholding with more than 5 classes is very slow! Found {n_class=}")
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

    if len(file_in) == 0:
        logging.warning(f'No files found to process in {arg_in}.')
        return []

    return file_in


def process_file(
        fn, out_top, n_colors=2, dither=False, crop_size=None, median_kernel_size=None, contrast_adjust='auto',
        set_dpi=None, keep_original=False, out_format='png', overwrite_fn_okay=False):
    """
    Process one input image file.

    Parameters:
        fn (pathlib.Path): Input file path.
        out_top (pathlib.Path): Output directory path.
        n_colors (int): Number of colors in the output image. Use n_colors=2 for pure black & white image.
        dither (bool): Whether to apply dithering to the image. See note above.
        crop_size (str or None): Crop size like 'A4', 'letter, etc, or None.
        median_kernel_size (int or None): Kernel size for median filtering, or None.
                                          Only applicable to grayscale or B&W outputs.
        contrast_adjust (str): Contrast adjustment method ('auto', 'minmax').
                               Only applicable to grayscale or B&W outputs.
        set_dpi (float or None): DPI to set in output image metadata, or None. When none, tries to copy
                                 DPI from input image, when available.
        keep_original (bool or str): If True or "true", keeps a copy of the original file with suffix "orig_"
                                     in `out_top` folder.
        out_format (str): Output image format ('png', 'tiff').
        overwrite_fn_okay (bool): If True, allows overwriting the input file.

    ToDo:
     - add Blurring if required
    """
    assert n_colors > 1, 'Need atleast 2 colors!'
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

    if crop_size is not None:
        img = crop(img_orig, crop_size)
    else:
        img = img_orig

    # final output is grayscale or black & white
    if n_colors == 2 or not dither:  # mono-chrome; single channel OR black & white
        img = img.convert('L', dither=None)  # grayscale

        I, _ = image_arr(img)
        oimg = window_intensity(I, contrast_enhance_qunatiles[contrast_adjust])

        if median_kernel_size is not None:
            oimg = median_filter(oimg, kernel_size=median_kernel_size)

        if not dither:  # use otsu
            oimg = otsu(oimg, n_class=n_colors)

            if out_format == 'tiff' and n_colors == 2:
                oimg = oimg > 0  # make it 1-bit/sample
            else:  # pngs or grayscale
                oimg = rescale_to_8bit(oimg)

            out_img = pil_image(oimg, img)

        else:  # dither using PIL; must be n_color=2
            assert n_colors == 2
            oimg = rescale_to_8bit(oimg)
            oimg = pil_image(oimg, img)
            out_img = oimg.convert(
                mode='1',
                colors=n_colors,
                dither=Image.Dither.FLOYDSTEINBERG,
                palette=Image.Palette.ADAPTIVE,
                )

    else:  # RGB colored; n_colors > 2 and dither
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.30)  # 30% more contast
        out_img = img.convert(
            mode='P',
            colors=n_colors,
            dither=Image.Dither.FLOYDSTEINBERG,
            palette=Image.Palette.ADAPTIVE,
            )

    # adjust saving kwargs if needed
    if out_format == 'tiff':
        if n_colors == 2:
            save_kwargs["compression"] = "group4"
        else:
            save_kwargs["compression"] = "lzma"

    if set_dpi is not None:  # must be number; overrides input-image's dpi
        save_kwargs["dpi"] = (set_dpi, set_dpi)

    elif 'dpi' in img_orig.info:
        save_kwargs["dpi"] = img_orig.info['dpi']

    out_file = out_top / f'{fn.stem}.{out_format}'
    out_img.save(out_file, **save_kwargs)

    print(f'[INFO] Saved: {out_file}')
    return out_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Optimizes scanned documents for archival purposes.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    requiredNamed = parser.add_argument_group('Required named arguments')
    requiredNamed.add_argument(
        '-i', '--input', required=True,
        help='Path to input filename (or directory). It can also be the "save path" as returned by Gnome Simple-Scan. ' \
        'When directory, it process all valid files (png, jpeg, jpg, tiff) in this top level directory; NOT recursive.')

    requiredNamed.add_argument(
        '-o', '--output-dir',
        help='Path to output folder/directory', required=True)

    parser.add_argument(
        "--out-format", choices=list(output_formats.keys()),
        help="Set output image format.", default='tiff')

    parser.add_argument(
        "--num-colors", type=int,
        help="number of colors in final image.", default=2)

    parser.add_argument(
        "--dither", action='store_true', default=False,
        help="When specified uses pillow dithering. A colorful Palette is used only when "
        "--dither and --num-colors more than 2 (two) is used. "
        "Otherwise grayscale pallet is used.")

    parser.add_argument(
        "--crop-size",
        help="When set crops the input image to specified size.",
        choices=list(paper_size_inch.keys()))

    parser.add_argument(
        "--contrast-adjust",
        help="Stretch intensity to adjust contrast",
        choices=list(contrast_enhance_qunatiles.keys()), default='auto')

    parser.add_argument(
        "--median-kernel-size", type=int, default=None,
        help="Set kernel size for median filtering. When not specified, no median filtering is done.")

    parser.add_argument(
        "--set-dpi", type=float, default=None,
        help="Set DPI in image meta data.")


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
                dither=args.dither,
                crop_size=args.crop_size,
                contrast_adjust=args.contrast_adjust,
                median_kernel_size=args.median_kernel_size,
                set_dpi=args.set_dpi,
                out_format=args.out_format
            )
            logging.info(f'Saved {outfn}')

        except Exception:
            logging.error(f'Encoutered error while processing: {fn}:\n\n {traceback.format_exc()}')

