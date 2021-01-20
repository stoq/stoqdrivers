#!/bin/bash

version=$1

regex="([0-9]+)\.([0-9]+)\.?([0-9]*)?(~([a-z]*[0-9]*))?"
if [[ $version =~ $regex ]]
then
    major=${BASH_REMATCH[1]}
    minor=${BASH_REMATCH[2]}
    micro=${BASH_REMATCH[3]:-0}
else
    echo "Version doesn't match expected regex"
    exit 1
fi

debchange -v $1 "Release $version" -D xenial
year=`date +%Y`
month=`date +%m | sed "s/^0//"`
day=`date +%d`

sed -i "s/version = .*/version = \"$major.$minor.$micro\"/" stoqdrivers/__init__.py
