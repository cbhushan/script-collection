#!/usr/bin/env python
#
# Copyright 2017 C Bhushan; Licensed under the Apache License v2.0.
# https://github.com/cbhushan/script-collection
#

from gimpfu import *

def scanned_document_cleanup_image(img, layer, thickness_val, GaussRadius, bright_val, contrast_val):
    ''' Cleans up a scanned image of a document to produce 1 bit per pixel image outputs for archiving purposes.
    
    Parameters:
    img : image The current image. 300 ppi for best results.
    layer : layer The layer of the image that is selected.
    small_text : True/False if the text is small.
    bright_val : Brighness value for final output.
    contrast_val : Contast value for final output.
    '''

    # setup progress bar and undo group
    gimp.progress_init("Cleaning up " + img.name + "...")
    pdb.gimp_image_undo_group_start(img)

    # Cleanup the image
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

    # Index image
    pdb.gimp_posterize(layer, 2)
    pdb.gimp_image_convert_indexed(img, 0, 3, 2, 1, 1, 'ignoredtext') # BW output
        
    # End progress and undo group
    pdb.gimp_image_undo_group_end(img)
    pdb.gimp_progress_end()

register(
    "python_fu_scanned_document_cleanup_image",
    "Cleanup a scanned document",
    "Cleanup a scanned image of a document to produce 1bpp image outputs.",
    "C. Bhushan",
    "MIT License",
    "2016",
    "<Image>/Filters/Scanned Document/Cleanup Image",
    "*",
    [
        (PF_RADIO, "thickness_val", "Font weight:", 1, (("Thin", 0),("Normal", 1),("Bold",2),("Bolder",3),("Define custom param. below",4))),
        (PF_SLIDER, "GaussRadius", "Gaussian radius:", 1, (0, 20, 0.5)),
        (PF_SLIDER, "bright_val", "Brightness:", -70, (-127, 127, 2)),
        (PF_SLIDER, "contrast_val", "Contrast:", 80, (-127, 127, 2))
    ],
    [],
    scanned_document_cleanup_image)

main()
