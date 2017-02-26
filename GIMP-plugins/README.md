# GIMP-Plugin
Set of my GIMP plugins to simplify life or just to play around!! :satisfied: :grinning: These plugins are written using [Script-Fu](https://docs.gimp.org/en/gimp-concepts-script-fu.html) and [Python-Fu](https://docs.gimp.org/en/gimp-filters-python-fu.html) (or [GIMP-Python](https://www.gimp.org/docs/python/)). 

### Installation
Script-Fu scripts (`*.scm` files) should be [easy to install](https://docs.gimp.org/en/install-script-fu.html) and get working on all operating systems. Similarly, Python-Fu scripts can be installed by copying `*.py` files to GIMP plug-ins directory. However Python-Fu scripts may be bit challeging to get working on Windows OS, as it requires working installation of [python](https://www.python.org/). Step to install Python-Fu on window can be found on a few websites, however I have not tested it: [gimpusers.com](http://www.gimpusers.com/tutorials/install-python-for-gimp-2-6-windows), [gimpbook.com](http://gimpbook.com/scripting/), [reddit.com](https://www.reddit.com/r/GIMP/comments/1hw9f0/using_pythonfu_in_windows/).

Linux users can simple execute the included `deploy-gimp-plugins.sh` script to install all the scripts in their home directory.


### Plugins/scripts

* [**otsu-threshold.scm**](otsu-threshold.scm) - Implements [Otsu's thresholding method](https://en.wikipedia.org/wiki/Otsu's_method) in Script-Fu to binarize the current image. On installation, this appears in menu: _Filters/Scanned Document/Otsu threshold - binarize Image_. This has similar effect as the "Auto" button found in menu _Colors/Threshold_. It was implemented to expose the auto-thresholding functionality to the [Procedure Database](https://docs.gimp.org/en/glossary.html#glossary-pdb) so that it can be used in other scripts/plugins. In addition, `otsu-threshold.scm` also allows controling bin-width for internal histogram estimation and converts image to indexed image with 2-color mono-palette.

* [**optimize-scanned-document-batch.py**](deploy-gimp-plugins.sh) - <img align="right" src="screenshot-optimize-scanned-documents-batch-dialog.png?raw=true" alt="Batch processing screenshot" title="Batch processing dialog" style="max-width:100%;" width="25%"> Python-Fu script for batch processing of scanned documents (**not** natural images) to achieve substantially small sized files without loosing the relevant content. This is desirable for archiving of lots of paper documents electronically. On installation, this script appears in menu: _Filters/Scanned Document/Optimize document - Batch_. It is a wrapper around `otsu-threshold.scm` and adds few more features for batch processing (see screenshot on right; click to enlarge). Output images are saved in tiff format with [CCITT Group 4 compression](https://en.wikipedia.org/wiki/Group_4_compression) (png format is used when Number-of-colors is more than 2). Default values should work reasonably well with scanned image with 300 DPI (for best results disable all [image correcting features](http://ugp01.c-ij.com/ij/webmanual/ScanGear/M/MFP/19.1/EN/SG/Sg-909.html) in the scanner software specially _Unsharp Mask_). For images with very little content (mostly blank), contrast stretching should be changed to "Min-Max". Smoothing can also be applied for noisy input images.



