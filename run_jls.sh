#!/bin/bash
freq="95 97"  #frequency range to write out - multiple intervals are allowed.  A sensible argument here would be "2 20 136 138", with orbcomm to be tweaked
bits=2  #log2 of the # of bits to write, so 0 is 1 bit, 1 is 2 bits, 2 is 4 bits.
fsize=0.5  #file size in gigabytes
max_daq_runs=1 #number of times to try to run the daq.  This number should probably >= # of drives that are mounted.

max_fpga_attempts=10 #how many times to try to boot the FPGA
attempts=0  #internal variables
success=0

mac=`./find_mac.py`  #try to find the MAC address automatically.  If this fails, the ethernet connection to the SNAP is down.


#try to boot the FPGA
while [ $attempts -lt $max_fpga_attempts -a  $success -eq 0 ]
do
    echo "hello"
    ((attempts++))
    
    #python albatros2_daq_jls.py 127.0.0.1:7147 -f /home/pi/firmware/quad_input_poco_gbe_2019-03-23_1523.fpg -c internal -a 393216 -F 65535 -b $bytes -d "192.168.2.200:4321" -m 0xb827eb6091e5  -l /home/pi/logs/ -Q "$freq"
    #python albatros2_daq_jls.py 127.0.0.1:7147 -f /home/pi/firmware/quad_input_poco_gbe_2019-03-23_1523.fpg -c internal -a 393216 -F 65535 -b $bytes -d "192.168.2.200:4321" -m 0xb827eb8e5bcd  -l /home/pi/logs/ -Q "$freq"

    python albatros2_daq_jls.py 127.0.0.1:7147 -f /home/pi/firmware/quad_input_poco_gbe_2019-03-23_1523.fpg -c internal -a 393216 -F 65535 -b $bits -d "192.168.2.200:4321" -m $mac  -l /home/pi/logs/ -Q "$freq" 
    #check the return value from the python script, returned via sys.exit()
    retval=$?  
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

if [ $success -eq 1 ]; then
    runs=0
    while [ $runs -lt $max_daq_runs ]
    do
	python packet_rec_jls.py -Q "$freq" -b $bits -g $fsize
	retval=$?
	((runs++))
	if [ $retval -eq 0 ]; then
	    echo Successfully completed daq baseband writing run $runs
	else
	    echo Failed daq baseband writing run with code $retval on run $runs
	fi
    done

fi
