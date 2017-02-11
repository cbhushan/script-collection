#!/bin/bash
# 
# This script sleeps for a random time before executing the passed command with
# arguments. It is useful for running cronjobs with same periodicity while
# avoiding a thundering herd problem.
#
# Copyright 2017 C Bhushan; Licensed under the Apache License v2.0.
# https://github.com/cbhushan/script-collection
#

if [ $# -lt 2 ] ; then
    echo "$0 <Max-wait-sec> <Command> [<arg1> <arg2> ... <argN>]" >&2
    exit 1
fi

MAXWAIT=$1
shift

rand_sec=$((RANDOM % MAXWAIT))
echo $(date +%d-%b-%Y-%T)" - Sleeping (randomly) for $rand_sec seconds before executing $1 ..."
/bin/sleep $rand_sec

exec $*
