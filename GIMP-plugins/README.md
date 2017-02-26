# GIMP-Plugin
Set of my GIMP plugins to simplify life or just to play around!! :satisfied: :grinning: These plugins are written using [Script-Fu](https://docs.gimp.org/en/gimp-concepts-script-fu.html) and [Python-Fu](https://docs.gimp.org/en/gimp-filters-python-fu.html) (or [GIMP-Python](https://www.gimp.org/docs/python/)). 

### Installation
Script-Fu scripts (`*.scm` files) should be [easy to install](https://docs.gimp.org/en/install-script-fu.html) and get working on all operating systems. Similarly, Python-Fu scripts can be installed by copying `*.py` files to GIMP plug-ins directory. However Python-Fu scripts may be bit challeging to get working on Windows OS, as it requires working installation of [python](https://www.python.org/). Step to install Python-Fu on window can be found on a few websites, however I have not tested it: [gimpusers.com](http://www.gimpusers.com/tutorials/install-python-for-gimp-2-6-windows), [gimpbook.com](http://gimpbook.com/scripting/), [reddit.com](https://www.reddit.com/r/GIMP/comments/1hw9f0/using_pythonfu_in_windows/).

Linux users can simple execute the included `deploy-gimp-plugins.sh` script to install all the scripts in their home directory.


### Plugins/scripts

* [**otsu-threshold.scm**](otsu-threshold.scm) - Implements [Otsu's thresholding method](https://en.wikipedia.org/wiki/Otsu's_method) in Script-Fu to binarize the current image. On installation, this appears in menu Filters/Scanned Document. This has similar effect as the "Auto" button found in menu Colors/Threshold. It was implemented to expose the auto-thresholding functionality to the [Procedure Database](https://docs.gimp.org/en/glossary.html#glossary-pdb) so that it can be used in other scripts/plugins. In addition, `otsu-threshold.scm` also allows controling bin-width for internal histogram estimation and converts image to indexed image with 2-color mono-palette.

* [**optimize-scanned-document-batch.py**](deploy-gimp-plugins.sh) - Batch process

<img src="screenshot-optimize-scanned-documents-batch-dialog.png?raw=true" alt="Batch processing screenshot" title="Batch processing dialog" style="max-width:100%;" width="20%">

![Alt text](screenshot-optimize-scanned-documents-batch-dialog.png?raw=true "Batch processing dialog")


