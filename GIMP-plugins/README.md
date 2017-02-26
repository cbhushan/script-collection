# GIMP-Plugin
Set of my GIMP plugins to simplify life or just to play around!! :satisfied: :grinning: These plugins are written using [Script-Fu](https://docs.gimp.org/en/gimp-concepts-script-fu.html) and [Python-Fu](https://docs.gimp.org/en/gimp-filters-python-fu.html) (or [GIMP-Python](https://www.gimp.org/docs/python/)). 

**Installation:** Script-Fu scripts (`*.scm` files) should be [easy to install](https://docs.gimp.org/en/install-script-fu.html) and get working on all operating systems. Similarly, Python-Fu scripts can be installed by copying `*.py` files to GIMP plug-ins directory. However Python-Fu scripts may be bit challeging to get working on Windows OS, as it requires working installation of [python](https://www.python.org/). Step to install Python-Fu on window can be found on a few websites, however I have not tested it: [gimpusers.com](http://www.gimpusers.com/tutorials/install-python-for-gimp-2-6-windows), [gimpbook.com](http://gimpbook.com/scripting/), [reddit.com](https://www.reddit.com/r/GIMP/comments/1hw9f0/using_pythonfu_in_windows/).

Linux users can simple execute the included `deploy-gimp-plugins.sh` script to install all the scripts in their home directory.

Each plugin is briefly described below.

### scanned-document-cleanup-image.py
This plugin (& its batch version) aims to produce legible outputs from scanned images while keeping the image size to minimum for archiving purposes. The scanned images are "cleaned" to produce 1bpp (1 bit per pixel) outputs, which should be exported in TIFF format with CCITT Group 4 fax compression for minimum file size. This is tested with images scanned with 300 PPI.
