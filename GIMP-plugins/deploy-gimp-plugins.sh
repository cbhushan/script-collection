#!/bin/bash
# Installs GIMP plugins to user's gimp plugin directory

srcDir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
targetDir="$HOME"/".gimp-2.8"

if [ -d "$targetDir" ]; then
    echo "Copying scripts to $targetDir"
    
    pluginDir="$targetDir"/"plug-ins"
    mkdir -p "$pluginDir"
    cp -p -f "$srcDir"/*.py "$pluginDir"/

    scriptDir="$targetDir"/"scripts"
    mkdir -p "$scriptDir"
    cp -p -f "$srcDir"/*.scm "$scriptDir"/
else
    echo "Gimp directory not found: $targetDir"
    exit 1
fi

