#!/bin/bash
# Installs GIMP plugins to user's gimp plugin directory


srcDir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
targetDir="$HOME"/".gimp-2.8/plug-ins"

if [ -d "$targetDir" ]; then
    cp -p -f "$srcDir"/*.py "$targetDir"/
else
    echo "Gimp directory not found: $targetDir"
fi

