#!/bin/bash

# Basic init variables
app_dir=./app
db_dir=./db

if [[ "$(whoami)" != "root" ]] ; then
    echo "Run me as root"
    exit 1
fi

# Init checks
if [ $# -lt 1 ] || [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]] ; then
    echo "Usage: $0 <racktables version>"
    exit 1
fi

if ! [ -d $app_dir ] || ! [ -d $db_dir ] ; then
    echo "Run me from the tests/docker directory"
    exit 1
fi

# Variables
rt_version=$1
repository="https://github.com/RackTables/racktables.git"
original_dir=$PWD

set -e
echo ">> Preparing GIT data"
if ! [ -d $app_dir/racktables ] ; then 
    git clone $repository $app_dir/racktables 
fi

cd $app_dir/racktables
git fetch


if [[ $rt_version =~ ^RackTables-[0-9.]+$ ]] ; then
    git_version=$rt_version
else
    git_version="RackTables-$rt_version"
fi

git checkout $git_version && echo "GIT is ready" || exit 1
cd $original_dir

echo ">> Preparing DB data"
if ! [ -d $db_dir/data ] ; then
    cd $db_dir
    mkdir data
    chown -R 999:999 data
    echo "DB dir is ready"
else
    echo "DB dir already exists, skipping"
fi

echo "Now you are ready to run 'docker-compose --build up'"

