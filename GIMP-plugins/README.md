# GIMP-Plugin
My GIMP plugins to simplify life or just to play around!! :satisfied: :grinning: Most of these plugins are written in
[Python-Fu](https://docs.gimp.org/en/gimp-filters-python-fu.html) or more formally with [GIMP-Python](https://www.gimp.org/docs/python/).

**Installation:** Simply copy the `*.py` files to GIMP plug-ins directory and restart GIMP. The GIMP plug-ins directory 
would be typically something like `~/.gimp-2.8/plug-ins/` on Linux systems. Make sure `*.py` have executable bit set.

Each plugin is briefly described below.

### scanned-document-cleanup-image.py
This plugin (& its batch version) aims to produce legible outputs from scanned images while keeping the image size to minimum for archiving purposes. The scanned images are "cleaned" to produce 1bpp (1 bit per pixel) outputs, which should be exported in TIFF format with CCITT Group 4 fax compression for minimum file size. This is tested with images scanned with 300 PPI.
