#!/bin/bash
# Install a virtualenv and requirements for ape

if [ -f venv ] ; then 
	echo "venv" directory already exists. aborting.
	exit -1
fi
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
