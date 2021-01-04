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
import trimble_utils
import datetime

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

    use_trimble = True

    logger=logging.getLogger("dump_spectra")
    logger.setLevel(logging.INFO)
    log_dir=config_file.get("albatros2", "dump_spectra_log_directory")
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
    spectra_output_dir=config_file.get("albatros2", "dump_spectra_output_directory")
    logger.info("# (4) Spectra output directory: %s"%(spectra_output_dir))
    pols=config_file.get("albatros2", "pols")
    logger.info("# (5) Pols: %s"%(pols))
    registers=config_file.get("albatros2", "registers")
    logger.info("# (6) Registers: %s"%(registers))
    compress_scio_files=config_file.get("albatros2", "compress_scio_files")
    if compress_scio_files=="None":
        compress_scio_files=None
    logger.info("# (7) Compress scio files: %s"%(compress_scio_files))
    diff_scio_files=config_file.getboolean("albatros2", "diff_scio_files")
    logger.info("# (8) Diff scio files: %r"%(diff_scio_files))
    logger.info("# (9) Log directory: %s"%(log_dir))
    logger.info("########################################################################################")
    try:
        digitizer=albatrosdigitizer.AlbatrosDigitizer(snap_ip, snap_port, logger=logger)
        pols=pols.split()
        registers=registers.split()
	if use_trimble:
		if trimble_utils.get_report_trimble() is None:
                	print("Trying to using GPS clock but Trimble not detected.")
		else:
			print("Trimble GPS clock successfully detected.")
	else:
                print("Not using Trimble GPS clock. Timestamps will come from system clock.")
        # Shift between GPS and Linux system zero times
        gps_to_sys = (datetime.datetime(year=1980,month=1,day=6) - datetime.datetime(year=1970,month=1,day=1)).total_seconds()
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
            if use_trimble:
	    	file_gps_timestamp1 = open("%s/time_gps_start.raw"%outsubdir, "w")
            	file_gps_timestamp2 = open("%s/time_gps_stop.raw"%outsubdir, "w")
            file_sys_timestamp1 = open("%s/time_sys_start.raw"%outsubdir, "w")
	    file_sys_timestamp2 = open("%s/time_sys_stop.raw"%outsubdir, "w")
	    file_fpga_temp = open("%s/fpga_temp.raw"%outsubdir, "w")
	    file_pi_temp = open("%s/pi_temp.raw"%outsubdir, "w")
	    for register in registers:
		start_raw_files[register] = open("%s/%s1.raw"%(outsubdir, register), "w")
		end_raw_files[register] = open("%s/%s2.raw"%(outsubdir, register), "w")
	    for pol in pols:
		scio_files[pol] = scio.scio("%s/%s.scio"%(outsubdir, pol), diff=diff_scio_files, compress=compress_scio_files)
	    acc_cnt = 0 
            while time.time()-start_time < 60*60: # Hardcoded maximum run time of 1 hour (!!!) 
		new_acc_cnt = digitizer.read_registers(["acc_cnt"])
		if new_acc_cnt > acc_cnt:
		    print("new_acc_cnt", new_acc_cnt)
		    print("ctime" ,time.ctime())
		    acc_cnt = new_acc_cnt
                    if use_trimble:
			start_gps_time = trimble_utils.get_gps_time_trimble(maxtime=2,maxiter=1)
		    start_sys_timestamp = time.time()
		    start_reg_data = digitizer.read_registers(registers)
		    pol_data = digitizer.read_pols(pols, ">2048q")
                    end_reg_data = digitizer.read_registers(registers)
                    end_sys_timestamp = time.time()
                    if use_trimble:
			end_gps_time = trimble_utils.get_gps_time_trimble(maxtime=2,maxiter=1)
		    read_time = end_sys_timestamp-start_sys_timestamp
		    print("Read took: "+str(read_time))
                    if use_trimble:
			if start_gps_time is None:
                        	start_gps_timestamp = 0
                    	else:
                        	start_gps_timestamp = start_gps_time["week"]*7*24*3600 + start_gps_time["seconds"] + gps_to_sys
                    	if end_gps_time is None:
                        	end_gps_timestamp = 0
                    	else:
                        	end_gps_timestamp = end_gps_time["week"]*7*24*3600 + end_gps_time["seconds"] + gps_to_sys
		    if start_reg_data["acc_cnt"] != end_reg_data["acc_cnt"]:
			print("Accumulation length changed during read")
		    for register in registers:
			numpy.array(start_reg_data[register]).tofile(start_raw_files[register])
			start_raw_files[register].flush()
			numpy.array(end_reg_data[register]).tofile(end_raw_files[register])
			end_raw_files[register].flush()
		    numpy.array(start_sys_timestamp).tofile(file_sys_timestamp1)
		    numpy.array(digitizer.get_fpga_temperature()).tofile(file_fpga_temp)
		    numpy.array(get_rpi_temperature()).tofile(file_pi_temp)
		    numpy.array(end_sys_timestamp).tofile(file_sys_timestamp2)
                    if use_trimble:
			numpy.array(start_gps_timestamp).tofile(file_gps_timestamp1)
			numpy.array(end_gps_timestamp).tofile(file_gps_timestamp2)
		    file_sys_timestamp1.flush()
		    file_fpga_temp.flush()
		    file_pi_temp.flush()
		    file_sys_timestamp2.flush()
                    if use_trimble:
                    	file_gps_timestamp1.flush()
			file_gps_timestamp2.flush()
                    for pol in pols:
			scio_files[pol].append(pol_data[pol])
            for pol in pols:
	        scio_files[pol].close()
	    for register in registers:
	        start_raw_files[register].close()
	        end_raw_files[register].close()
	    file_sys_timestamp1.close()
	    file_fpga_temp.close()
	    file_pi_temp.close()
            file_sys_timestamp2.close()
            if use_trimble:
            	file_gps_timestamp1.close()
		file_gps_timestamp2.close()
    finally:
	logger.info("Terminating DAQ at %s"%datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
