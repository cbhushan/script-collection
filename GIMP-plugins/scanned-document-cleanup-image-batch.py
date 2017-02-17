#!/usr/bin/env python
#
# Copyright 2017 C Bhushan; Licensed under the Apache License v2.0.
# https://github.com/cbhushan/script-collection
#

import os
import math
from gimpfu import *

def batch_scanned_document_cleanup_image(img, layer, inputFolder, outputFolder, thickness_val, GaussRadius, bright_val, contrast_val, num_colors, set_DPI, DPI_input, crop_img):
    ''' Cleans up a scanned image of a document to produce 1 bit per pixel image outputs for archiving purposes.
    
    Parameters:
    img : image The current image. 300 ppi for best results (unused).
    layer : layer The layer of the image that is selected (unused).
    inputFolder : string Source folder containing the images that would be processed.
    outputFolder : string The output folder that will save the processed images.
    small_text : True/False if the text is small.
    bright_val : Brighness value for final output.
    contrast_val : Contast value for final output.
    '''

    # Iterate the folder
    for file in os.listdir(inputFolder):
        filename, file_extension = os.path.splitext(file)
        try:
            # try to load an image
            inputPath = inputFolder + "/" + file
            img = pdb.gimp_file_load(inputPath, inputPath)
            
            layer = pdb.gimp_image_flatten(img)
            pdb.gimp_layer_flatten(layer)
            
            if not pdb.gimp_drawable_is_gray(layer):
                pdb.gimp_image_convert_grayscale(img)
                
            if thickness_val == 0 : # thin font weight
                pdb.gimp_brightness_contrast(layer, -22, 20)

            else:
                pdb.gimp_brightness_contrast(layer, -20, 8)

                if thickness_val == 1 : # normal weight
                    GaussRadius = 2
                    bright_val = -40
                    contrast_val = 60

                elif thickness_val == 2 : # bold weight
                    GaussRadius = 4
                    bright_val = -70
                    contrast_val = 80

                elif thickness_val == 3 : # bolder
                    GaussRadius = 6.5
                    bright_val = -80
                    contrast_val = 80
                    
                if GaussRadius>0:
                    pdb.plug_in_gauss(img, layer, GaussRadius, GaussRadius, 1)
                    
                pdb.gimp_brightness_contrast(layer, bright_val, contrast_val)
                
            # set resolution
            if set_DPI:
                pdb.gimp_image_set_resolution(img, DPI_input, DPI_input)
                
            # crop if required
            if crop_img > 0:
                xres, yres = pdb.gimp_image_get_resolution(img)                
                if xres > 0:
                    if crop_img == 1: # Letter size
                        xinch = 8.5
                        yinch = 11.0
                    elif crop_img == 2: # A4 size
                        xinch = 8.3
                        yinch = 11.7

                    imgW = int(math.ceil(xres*xinch))
                    imgH = int(math.ceil(yres*yinch))
                    pdb.gimp_image_crop(img, imgW, imgH, 0, 0)

                else: # can't read resolution?
                    gimp.message("Could not read resolution. Will skip the image croping.")

            
            # Index image
            if num_colors == 2:
                pdb.gimp_posterize(layer, 2)
                pdb.gimp_image_convert_indexed(img, 0, 3, 2, 1, 1, 'ignoredtext') # BW output
                
                # save as tiff
                outputPath = outputFolder + "/" + filename + ".tiff"
                pdb.file_tiff_save(img, layer, outputPath, outputPath, 6)

            else: # more than 2 colors, save as png
                pdb.gimp_posterize(layer, num_colors)
                pdb.gimp_image_convert_indexed(img, 0, 0, num_colors, 1, 1, 'ignoredtext') # Optimal palette for num_colors
                
                # save as png
                outputPath = outputFolder + "/" + filename + ".png"
                pdb.file_png_save(img, layer, outputPath, outputPath, 0, 9, 0, 0, 0, 0, 1)
                

            # remove from memory
            pdb.gimp_image_delete(img)

        except Exception as err:
            gimp.message("Something went wrong while processing: %s \n\nError message: %s" %(file, str(err)))


    gimp.progress_update(1)


register(
    "python_fu_batch_scanned_document_cleanup_image",
    "Batch cleanup of scanned documents.",
    "Batch cleanup of scanned image (of documents) to produce 1bpp image outputs.",
    "C. Bhushan",
    "MIT License",
    "2016",
    "<Image>/Filters/Scanned Document/Cleanup Image - Batch",
    "", # Be active even when no image is loaded in gimp
    [
        (PF_DIRNAME, "inputFolder", "Image source folder", ""),
        (PF_DIRNAME, "outputFolder", "Output folder", ""),
        (PF_RADIO, "thickness_val", "Font weight:", 1, (("Thin", 0),("Normal", 1),("Bold",2),("Bolder",3),("Define custom param. below",4))),
        (PF_SLIDER, "GaussRadius", "Gaussian radius:", 1, (0, 20, 0.5)),
        (PF_SLIDER, "bright_val", "Brightness:", -70, (-127, 127, 2)),
        (PF_SLIDER, "contrast_val", "Contrast:", 80, (-127, 127, 2)),
        (PF_SPINNER, "num_colors", "Number of colors:", 2, (2, 255, 1)),
        (PF_TOGGLE, "set_DPI", "Set resolution?", 0),
        (PF_INT, "DPI_input", "Resolution (in DPI):", 0),
        (PF_OPTION,"crop_img", "Crop image to:", 0, ["Don't crop","Letter size","A4 size"])
    ],
    [],
    batch_scanned_document_cleanup_image)

main()
