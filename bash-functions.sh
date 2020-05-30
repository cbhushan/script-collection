# Library of commonly used operations. 
# This should be reusable in other bash scripts by sourcing this script:
#    source bash-functions.sh
#
# Note that boolean bash functions return 0 for True! Because bash interprets it as error code.
#
# Other similar bash function libs:
#  - https://github.com/javier-lopez/learn/blob/master/sh/lib
#  - https://github.com/martinburger/bash-common-helpers
#
# Copyright (c) C Bhushan; Licensed under the Apache License v2.0.
# https://github.com/cbhushan/script-collection
#
# bashmenot: Copyright (c) 2014-2015, Mietek Bak; Released under BSD 3-Clause License
# https://github.com/mietek/bashmenot

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd -P )"
source "${SCRIPT_DIR}/bashmenot/src.sh"


#######################################
# Checks if the given directory is empty.
# Usage: 
#     is_empty_directory </path/to/folder>
# Returns:
#     true when folder exists and is empty. Otherwise returns false
# Example:
#     is_empty_directory /blah && echo "Empty!" || echo "Not-empty or Non-existent!"
#
is_empty_directory() {
    if [ ! -e "${1}" ]; then
        false
    elif [ -z "$(ls -A "${1}")" ]; then
        true
    else
        false
    fi
}


#######################################
# Checks if the program/command is available (on current PATH).
# Usage: 
#     program_is_available <command>
# Returns:
#     true if program/command is found, else returns false
# Example:
#     program_is_available ffmpeg && echo "ffmpeg found!" || echo "ffmpeg is not available"
#
program_is_available() {
    local cmd
    expect_args cmd -- "$@"
    type "${cmd}" &> /dev/null
}


#######################################
# Asserts if the program/command is available (on current PATH). Dies otherwise.
# Usage: 
#     assert_program_is_available <command>
# Returns:
#     true if program/command is found, else dies (exits with exit status of 1)
# Example:
#     assert_program_is_available ffmpeg
#
assert_program_is_available() {
    local cmd
    expect_args cmd -- "$@" 
    program_is_available "${cmd}" || die "${cmd} is not available!"
}


#######################################
# Generates random string using pure bash of specified length (default length is 32). 
# random_string() should be preferred over this function.
# This is a fall-back when /dev/urandom is not available.
# Usage: 
#     bash_random_string [<length>]
# Returns:
#     Random string of requested length
# Example:
#     echo "$(bash_random_string)"
#
bash_random_string()
{
    local N B len
    expect_args len -- "$@" 32
    for (( N=0; N < $len; ++N ))
    do
        B=$(( $RANDOM%16 ))
        printf '%x' $B
    done
}


#######################################
# Returns random string of specified length (default length is 32).
# Note: Do NOT use for passwords. Use `pwgen -s` for passwords
# Similar to https://gist.github.com/earthgecko/3089509
# Usage: 
#     random_string [<length>]
# Returns:
#     Random string of requested length
# Example:
#     echo "$(random_string)"
#
function random_string {
    local len
    expect_args len -- "$@" 32
    if [ -e /dev/urandom ]; then
        </dev/urandom tr -dc 'a-zA-Z0-9' | head -c $len

    elif program_is_available uuidgen ; then
        # this may be slow !
        local N S
        N=$(( 1 + $len/32 ))
        for (( N=0; N < $len; ++N ))
        do
            S+=$(uuidgen | tr -dc 'a-zA-Z0-9' | head -c $len)
        done
        echo "$S" | head -c $len
    else
        bash_random_string $len
    fi
}


#######################################
# Copy file/folder to destination, preserving the original path structure after /.
# This is intended for backup purposes. Eg: 
#   /etc/fstab        -->   $BACKUPDIR/etc/fstab
#   $HOME/.filezilla  -->   $BACKUPDIR/$HOME/.filezilla
# Usage: 
#     backup_to_destination </path/to/file> </path/to/backup/folder> 
# Returns:
#     NA
# Example:
#     backup_to_destination ~/.ssh /mnt/backup-folder
#
backup_to_destination () {
    local FNAME BACKUPDIR
    expect_args FNAME BACKUPDIR -- "$@"
    expect_existing "${FNAME}" "${BACKUPDIR}"

    BACKUPDIR="$(realpath "${BACKUPDIR}")"
    FNAME="$(realpath "${FNAME}")"

    if [ -f "${BACKUPDIR}" ]; then
        echo "[ERROR] Backup-folder must be a folder. Regular file found: ${BACKUPDIR}"
        return 1
    fi

    TARGET_DIR="${BACKUPDIR}$(dirname "${FNAME}")"
    mkdir -p "${TARGET_DIR}"
    
    if [ -d "${FNAME}" ]; then
        # cp -R --preserve=timestamps "$FNAME" "$TARGET_DIR"/
        DIR_NAME="$(cd "${FNAME}" && pwd)"  # make sure does not end in slash
        rsync --recursive --links --perms --times --quiet --delete --delete-after "${DIR_NAME}" "${TARGET_DIR}"/
    elif [ -f "${FNAME}" ]; then          
        cp --preserve=timestamps "${FNAME}" "${TARGET_DIR}"/
    else
        echo "[WARNING] Skipping as the file/folder is neither a regular file or directory: ${FNAME} "
    fi
}

