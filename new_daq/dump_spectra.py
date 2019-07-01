#!/usr/bin/python
import argparse
import ConfigParser
import logging
import os
import datetime
import scio
import struct
import albatrosdigitizer
import time
import numpy

def get_rpi_temperature():
    x = open("/sys/class/thermal/thermal_zone0/temp", "r")
    temp = numpy.float32(x.readline())/1000
    print(temp)
    x.close()
    return temp

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("-c", "--configfile", type=str, default="config.ini", help="Config file with all the paramenters")
    args=parser.parse_args()

    config_file=ConfigParser.SafeConfigParser()
    config_file.read(args.configfile)

    logger=logging.getLogger("dump_spectra")
    logger.setLevel(logging.INFO)
    log_dir=config_file.get("albatros2", "spectra_log_directory")
    if not os.path.isdir(log_dir):
        os.mkdir(log_dir)
    file_logger=logging.FileHandler(log_dir+"albatros_spectra_"+datetime.datetime.now().strftime("%d%m%Y_%H%M%S")+".log")
    file_format=logging.Formatter("%(asctime)s %(name)s %(message)s", "%d-%m-%Y %H:%M:%S")
    file_logger.setFormatter(file_format)
    file_logger.setLevel(logging.INFO)
    logger.addHandler(file_logger)
    logger.info("########################################################################################")
    snap_ip=config_file.get("albatros2", "snap_ip")
    logger.info("# (1) SNAP Board IP address: %s"%(snap_ip))
    snap_port=int(config_file.get("albatros2", "snap_port"))
    logger.info("# (2) SNAP Board port: %d"%(snap_port))
    acclen=int(config_file.get("albatros2", "accumulation_length"))
    logger.info("# (3) Accumulation length: %d"%(acclen))
    spectra_output_dir=config_file.get("albatros2", "spectra_output_directory")
    logger.info("# (4) Spectra output directory: %s"%(spectra_output_dir))
    pols=config_file.get("albatros2", "pols")
    logger.info("# (5) Pols: %s"%(pols))
    registers=config_file.get("albatros2", "registers")
    logger.info("# (6) Registers: %s"%(registers))
    logger.info("# (7) Log directory: %s"%(log_dir))
    logger.info("########################################################################################")
    try:
        digitizer=albatrosdigitizer.AlbatrosDigitizer(snap_ip, snap_port, logger=logger)
        pols=pols.split()
        registers=registers.split()
        while True:
            start_time = time.time()
            if start_time>1e5:
		time_frag = str(start_time)[:5]
	    else:
		print("Start time in acquire data seems to be near zero")
	    outsubdir = "%s/%s/%s"%(spectra_output_dir, time_frag, str(numpy.int64(start_time)))
	    os.makedirs(outsubdir)
	    print("Writing current data to %s"%outsubdir)
	    start_raw_files = {}
	    end_raw_files = {}
	    scio_files = {}
	    file_sys_timestamp1 = open("%s/time_gps_start.raw"%outsubdir, "w")
	    file_sys_timestamp2 = open("%s/time_gps_stop.raw"%outsubdir, "w")
	    file_fpga_temp = open("%s/fpga_temp.raw"%outsubdir, "w")
	    file_pi_temp = open("%s/pi_temp.raw"%outsubdir, "w")
	    for register in registers:
		start_raw_files[register] = open("%s/%s1.raw"%(outsubdir, register), "w")
		end_raw_files[register] = open("%s/%s2.raw"%(outsubdir, register), "w")
	    for pol in pols:
		scio_files[pol] = scio.scio("%s/%s.scio"%(outsubdir, pol))
	    acc_cnt = 0 
            while time.time()-start_time < 60*60:
		new_acc_cnt = digitizer.read_registers(["acc_cnt"])
		if new_acc_cnt > acc_cnt:
		    print("new_acc_cnt", new_acc_cnt)
		    print("ctime" ,time.ctime())
		    acc_cnt = new_acc_cnt
		    start_sys_timestamp = time.time()
		    start_reg_data = digitizer.read_registers(registers)
		    pol_data = digitizer.read_pols(pols, ">2048q")
                    end_reg_data = digitizer.read_registers(registers)
		    end_sys_timestamp = time.time()
		    read_time = end_sys_timestamp-start_sys_timestamp
		    print("Read took: "+str(read_time))
		    if start_reg_data["acc_cnt"] != end_reg_data["acc_cnt"]:
			print("Accumulation length changed during read")
		    for register in registers:
			numpy.array(start_reg_data[register]).tofile(start_raw_files[register])
			start_raw_files[register].flush()
			numpy.array(end_reg_data[register]).tofile(end_raw_files[register])
			end_raw_files[register].flush()
                    for pol in pols:
			scio_files[pol].append(pol_data[pol])
			numpy.array(start_sys_timestamp).tofile(file_sys_timestamp1)
			numpy.array(digitizer.get_fpga_temperature()).tofile(file_fpga_temp)
			numpy.array(get_rpi_temperature()).tofile(file_pi_temp)
			numpy.array(end_sys_timestamp).tofile(file_sys_timestamp2)
			file_sys_timestamp1.flush()
			file_fpga_temp.flush()
			file_pi_temp.flush()
			file_sys_timestamp2.flush()
            for pol in pols:
	        scio_files[pol].close()
	    for register in registers:
	        start_raw_files[register].close()
	        end_raw_files[register].close()
	    file_sys_timestamp1.close()
	    file_fpga_temp.close()
	    file_pi_temp.close()
	    file_sys_timestamp2.close()
    finally:
	logger.info("Terminating DAQ at %s"%datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
