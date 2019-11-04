#!/bin/bash

casperfpga="https://github.com/nivekg/casperfpga.git"

echo "Downloading casperfpga from "
echo $casperfpga

git clone $casperfpga

echo "Moving to casperfpga"
cd casperfpga
git checkout devel 

echo "Installing casperfpga prerequists"
pip install -r requirements.txt

echo "Installing casperfpga"
sudo python setup.py install

trimble=https://github.com/mjuenema/python-TSIP.git
echo "Downloading python-TSIP"
git clone $trimble

echo "Installing python-TSIP"
cd python-TSIP
sudo python setup.py install
