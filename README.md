# albatros2_telescope


Wish list items:

Check drive permissions so that if a new non-read/writeable drive is plugged in, the DAQ has 
suitable permissions.

Check reported Trimble time to see if it's sensible.  If not, don't try to update system clock.
-> Related, should the system pause until the Trimble reports a sensbile time?

Nice to have - checking of various USB ports in case the Trimble does not go onto /dev/ttyUSB0

# Raspberry Pi SD Card

Here are the instructions for making a sd card for Raspberry Pi 4 or any RPi version:

(1) Download lastest RPi raspbian image from (I use the lite desktop version, but any one can be used):

    https://www.raspberrypi.org/downloads/raspbian/

(2) Write image to sd card using etcher (linux dd command should work but sometimes the sd card can be unbootable. Etcher always 
    makes a bootable card)

(3) Enable ssh by creating a blank file with the name "ssh" in the boot partition of the sd card:

    touch ssh

(4) Enable SPI (thats how the RPi talks to the FPGA):

    In boot partition, remove comment from line #dtparam=spi=on in config.txt 

(5) Setup static IP addresses for ssh-ing and baseband reading. Get the get from albatros2_daq/scripts/set_ip_addresses.py and
    run it with the following options:
    
    ./set_ip_addresses.py <path to sd card dhcpcd.conf file> -s <ip address for ssh-ing> -b <ip address for baseband>

(6) Update all system packages with:

    sudo apt update
    sudo apt upgrade

(7) (Not needed anymore, so you can skip it) Install the raspberry kernel headers:

    sudo apt-get install libraspberrypi-dev raspberrypi-kernel-headers

    This is because I edited the firmware programming code to get the peripheral address for the RPi automatically instead of it 
    being hardcoded in. Which means the same sd card can be used on any RPi version. For reference the peripheral address of the 
    RPi are:
    
    RPi 2B:        0x20000000
    RPi 3B/3B+:    0x3F000000
    RPi 4B:        0xFE000000

(8) Get the firmware programming code from my github and install:

    git clone https://github.com/nivekg/katcp_devel.git
    git checkout rpi-devel-casperfpga
    make all
    sudo cp ./fpg/kcpfpg /bin/
    sudo cp ./tcpborphserver3/tcpborphserver3 /bin/

(9) Make tcpborphserver run at startup. Make a file at /etc/systemd/system/ called tcpborphserver3.service with the contents,

    [Unit]
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
    WantedBy=multi-user.target
 
(10) Then enable it at startup by running:

    sudo systemctl daemon-reload
    sudo systemctl enable tcpborphserver3
    sudo systemctl start tcpborphserver3
    sudo systemctl status tcpborphserver3

(11) RPi should now be SNAP board ready.
