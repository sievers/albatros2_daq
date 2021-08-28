#!/bin/bash
python albatros2_daq.py 127.0.0.1:7147 -f /home/pi/firmware/quad_input_poco_gbe_2019-03-23_1523.fpg -c internal -a 393216 -F 65535 -b 2 -s 5 -B 264 -d "192.168.2.200:4321" -m 0xb827eb6091e5  -l /home/pi/logs/
