#!/bin/bash

echo "Moving to home directory"
cd ~

echo "Making direcory software"
mkdir software

echo "Entering software directory"
cd software

echo "Downloading katcp_devel"
git clone https://github.com/nivekg/katcp_devel.git

echo "Entering katcp_devel"
cd katcp_devel

echo "Checking out rpi-devel-casperfpga"
git checkout rpi-devel-casperfpga

echo "Running: make all"
make all

echo "Copying ./fpg/kcpfpg to /bin/"
sudo cp ./fpg/kcpfpg /bin/

echo "Copying ./tcpborphserver3/tcpborphserver3 to /bin/"
sudo cp ./tcpborphserver3/tcpborphserver3 /bin/

echo "Setting up tcpborphserver3 to run at startup"
echo "[Unit]
Description=TCPBorphServer allows programming and communication with the FPGA
Wants=network.target
After=syslog.target network-online.target

[Service]
Type=simple
ExecStart=/bin/tcpborphserver3 -f -l /dev/null
Restart=on-failure
RestartSec=10
KillMode=process

[Install]
WantedBy=multi-user.target" | sudo tee /etc/systemd/system/tcpborphserver3.service

sudo systemctl daemon-reload
sudo systemctl enable tcpborphserver3
sudo systemctl start tcpborphserver3

echo "Checking tcpborphserver3 status"
sudo systemctl status tcpborphserver3

echo "Exiting katcp_devel"
cd ..

echo "Downloading casperfpga"
git clone https://github.com/nivekg/casperfpga.git

echo "Entering casperfpga"
cd casperfpga

echo "Making casperfpga_dep"
mkdir ../casperfpga_dep

echo "Downloading casperfpga dependencies"
pip download -r requirements.txt --no-binary :all: -d ../casperfpga_dep

echo "Installing casperfpga dependencies"
pip install -r requirements.txt --no-index --find-links ../casperfpga_dep

echo "Switching to devel branch"
git checkout devel

echo "Installing casperfpga"
sudo python setup.py install

echo "Exiting casperfpga"
cd ..

echo "Downloading pyaml"
pip download pyaml --no-binary :all: -d .

echo "Installing pyaml"
pip install pyaml --no-index --find-link .

echo "Downloading psutil"
git clone https://github.com/giampaolo/psutil.git

echo "Entering psutil"
cd psutil

echo "Installing psutil"
sudo python setup.py install

echo "Exiting psutil"
cd ..

echo "Downloading python-TSIP"
git clone https://github.com/mjuenema/python-TSIP.git

echo "Entering python-TSIP"
cd python-TSIP

echo "Installing python-TSIP"
sudo python setup.py install

echo "Exiting python-TSIP"
cd ..

echo "Exiting software"
cd ~

echo "Increasing network buffer size to 512Mb"
bytes=$((512 * 1024000))
echo "sysctl net.core.rmem_default="$bytes"
sysctl net.core.rmem_max="$bytes"" | sudo tee -a /etc/sysctl.conf

echo "All done. Please reboot"
