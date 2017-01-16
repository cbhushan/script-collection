#!/bin/sh
#
# This script removes duplicate entries from ~/.bash_history while preserving their order 
# and retaining the last entry for duplicate commands. 
#
# It can be executed repeated as cronjob at an appropriate interval. 
#
# More solutions: http://unix.stackexchange.com/q/48713
#


TEMP_HISTORY=$(mktemp)
TEMP_HISTORY_SORTED=$(mktemp)

# remove multiple spaces and trailing spaces
cat $HOME/.bash_history | tr -s \  | sed -e 's/^ *//g' -e 's/ *$//g' > "$TEMP_HISTORY"

# first reverse the file; uniq without loosing order.
# (awk command below retains the first occurance, hence first reverse the file)
tac "$TEMP_HISTORY" | awk '{ if (!h[$0]) { print $0; h[$0]=1 } }' > "$TEMP_HISTORY_SORTED"
tac "$TEMP_HISTORY_SORTED" > $HOME/.bash_history

rm -f "$TEMP_HISTORY"
rm -f "$TEMP_HISTORY_SORTED"

