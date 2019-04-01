#!/bin/bash
freq="95 97"
bytes=2

max_fpga_attempts=3
attempts=0
success=0

while [ $attempts -lt $max_fpga_attempts -a  $success -eq 0 ]
do
    echo "hello"
    ((attempts++))
    
    python albatros2_daq_jls.py 127.0.0.1:7147 -f /home/pi/firmware/quad_input_poco_gbe_2019-03-23_1523.fpg -c internal -a 393216 -F 65535 -b $bytes -d "192.168.2.200:4321" -m 0xb827eb6091e5  -l /home/pi/logs/ -Q "$freq" 
    retval=$?
    echo "retval is " $retval
    if [ $retval -eq 0 ]; then
	success=1
    fi
done

if [ $success -eq 1 ]; then
    echo Succeeded in programming FPGA on attempt number $attempts
else
    echo Failed in programming FPGA after $attempts attempts.
fi
	  

#echo "retval is " $?
#export retval

sleep 2

#python packet_rec_jls.py -Q "$freq" -b $bytes
