#!/usr/bin/env python
#
# Batch optimization of scanned documents - See register() below for more details.
#
# Copyright 2017 C Bhushan; Licensed under the Apache License v2.0.
# https://github.com/cbhushan/script-collection
#

import os
import math
from gimpfu import *

def optimize_scanned_document_batch(inputFolder, outputFolder, crop_img, intensity_stretch, pre_blur, blur_radius, blur_max_delta, num_colors, set_DPI, DPI_input):
  
  # Iterate the folder; not recursively!
  file_list = os.walk(inputFolder).next()[2]
  cnt = 0.0
  for file in file_list:
    cnt += 1.0
    filename, file_extension = os.path.splitext(file)
    try:
      inputPath = os.path.join(inputFolder, file)
      img = pdb.gimp_file_load(inputPath, inputPath)
      
      layer = pdb.gimp_image_flatten(img)
      pdb.gimp_layer_flatten(layer)
      
      if not pdb.gimp_drawable_is_gray(layer):
        pdb.gimp_image_convert_grayscale(img)

      
      # crop if required
      if crop_img > 0:
        xres, yres = pdb.gimp_image_get_resolution(img)
        if xres > 0:
          if crop_img == 1: # Letter size
            xinch = 8.5
            yinch = 11.0
          elif crop_img == 2: # Half Letter
            xinch = 8.5
            yinch = 5.5
          elif crop_img == 3: # A4 size
            xinch = 8.3
            yinch = 11.7
              
          imgW = int(math.ceil(xres*xinch))
          imgH = int(math.ceil(yres*yinch))
          curr_imgW = pdb.gimp_image_width(img)
          curr_imgH = pdb.gimp_image_height(img)
          pdb.gimp_image_crop(img, min(imgW, curr_imgW), min(imgH, curr_imgH), 0, 0)
          
        else: # can't read resolution?
          gimp.message("Could not read resolution. Will skip the image croping.")


      # Stretch contrast (should slightly improve performance of otsu_threshold below, as it is not run at full bin resolution)
      if intensity_stretch == 1: # Rescale intensity from low 0.6 %tile to high 0.6 %tile; see gimp_levels_config_stretch_channel() in gimplevelsconfig.c
        pdb.gimp_levels_stretch(layer)  # This will fail with images with very little content!
        
      elif intensity_stretch == 2:
        pdb.plug_in_c_astretch(img, layer) # Rescale intesity from min-max intensity

        
      # Blurring if required      
      if blur_radius>0:
        if pre_blur == 1: # Selective Gaussian
          pdb.plug_in_sel_gauss(img, layer, blur_radius, round(blur_max_delta))
        
        elif pre_blur == 2: # Regular Gaussian blurring
          pdb.plug_in_gauss(img, layer, blur_radius, blur_radius, 1)
  

      # Otsu thresholding / posterize
      if num_colors == 2: # binary, otsu thresholding
        pdb.script_fu_otsu_threshold(img, layer, 4)
        layer = pdb.gimp_image_get_active_layer(img)

      else: # more than 2 colors, saved as png
        pdb.gimp_posterize(layer, num_colors)
        pdb.gimp_image_convert_indexed(img, 0, 0, num_colors, 1, 1, 'ignoredtext') # Optimal palette for num_colors

        
      # set resolution
      if set_DPI:
        pdb.gimp_image_set_resolution(img, DPI_input, DPI_input)
              

      # Save output image
      if num_colors == 2: # save as tiff with CCITT G4 Fax compression
        outputPath = os.path.join(outputFolder, filename + ".tiff")
        pdb.file_tiff_save(img, layer, outputPath, outputPath, 6) 

      else: # more than 2 colors, save as png
        outputPath = os.path.join(outputFolder, filename + ".png")
        pdb.file_png_save(img, layer, outputPath, outputPath, 0, 9, 0, 0, 0, 0, 1)
                
      
      # remove from memory
      pdb.gimp_image_delete(img)
      
    except Exception as err:
      gimp.message("Something went wrong while processing: %s \n\nError message: %s" %(file, str(err)))

    gimp.progress_update(cnt/float(len(file_list)))


register(
  "optimize-scanned-document-batch",
  "Batch optimization of scanned documents.",
  "Batch cleanup of scanned images (of documents) to produce output images that substancially smaller in size. When Number-of-colors is 2 Otsu thresholding is used, otherwise gimp's posterization is used. Output images can optionally be cropped to Letter size(1), Half Letter(2), or A4 size(3). Contrast stretching can optionally be applied using 0.6 prcentile (low and high) intensities(1) or min-max intensities(2). Input images can optionally be first blurred with Selective Gaussian(1) or regular Gaussian(2) method.",
  "C Bhushan - https://github.com/cbhushan/script-collection/",
  "C Bhushan - Apache License v2.0",
  "2017",
  "<Toolbox>/Filters/Scanned Document/Optimize document - Batch",
  "", # Be active even when no image is loaded in gimp
  [
    (PF_DIRNAME, "inputFolder", "Image source folder", ""),
    (PF_DIRNAME, "outputFolder", "Output folder", ""),
    (PF_OPTION,  "crop_img", "Crop image to", 0, ["Don't crop", "Letter size", "Half Letter", "A4 size"]),
    (PF_OPTION,  "intensity_stretch", "Stretch contrast with", 1, ["No stretching", "0.6% Low-High", "Min - Max"]),
    (PF_OPTION,  "pre_blur", "First blur with", 0, ["No blurring", "Selective Gaussian", "Gaussian (isotropic)"]),
    (PF_SPINNER, "blur_radius", "Blur radius", 4, (1, 20, 1)),
    (PF_SLIDER,  "blur_max_delta", "Blur max delta", 50, (0, 255, 1)),
    (PF_SPINNER, "num_colors", "Number of colors", 2, (2, 255, 1)),
    (PF_TOGGLE,  "set_DPI", "Set resolution", 0),
    (PF_INT,     "DPI_input", "Resolution (in DPI)", 0)
  ],
  [],
  optimize_scanned_document_batch)

main()
