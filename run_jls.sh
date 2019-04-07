#!/bin/bash
freq="95 97"
bytes=2
fsize=0.5

max_fpga_attempts=10
attempts=0
success=0

mac=`./find_mac.py`


while [ $attempts -lt $max_fpga_attempts -a  $success -eq 0 ]
do
    echo "hello"
    ((attempts++))
    
    #python albatros2_daq_jls.py 127.0.0.1:7147 -f /home/pi/firmware/quad_input_poco_gbe_2019-03-23_1523.fpg -c internal -a 393216 -F 65535 -b $bytes -d "192.168.2.200:4321" -m 0xb827eb6091e5  -l /home/pi/logs/ -Q "$freq"
    #python albatros2_daq_jls.py 127.0.0.1:7147 -f /home/pi/firmware/quad_input_poco_gbe_2019-03-23_1523.fpg -c internal -a 393216 -F 65535 -b $bytes -d "192.168.2.200:4321" -m 0xb827eb8e5bcd  -l /home/pi/logs/ -Q "$freq"

    python albatros2_daq_jls.py 127.0.0.1:7147 -f /home/pi/firmware/quad_input_poco_gbe_2019-03-23_1523.fpg -c internal -a 393216 -F 65535 -b $bytes -d "192.168.2.200:4321" -m $mac  -l /home/pi/logs/ -Q "$freq" 
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
    max_daq_runs=4
    runs=0
    while [ $runs -lt $max_daq_runs ]
    do
	python packet_rec_jls.py -Q "$freq" -b $bytes -g $fsize
	retval=$?
	((runs++))
	if [ $retval -eq 0 ]; then
	    echo Successfully completed daq baseband writing run $runs
	else
	    echo Failed daq baseband writing run with code $retval on run $runs
	fi
    done

fi
