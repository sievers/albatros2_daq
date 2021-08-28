#!/usr/bin/python
import argparse
import ConfigParser
import logging
import os
import socket
import datetime
import scio
import struct
import albatrosdigitizer
import albatros_daq_utils
import time
import numpy
import math
#import trimble_utils
import lbtools_l
from matplotlib import pyplot as plt


def get_rpi_temperature():
    x = open("/sys/class/thermal/thermal_zone0/temp", "r")
    temp = numpy.float32(x.readline())/1000
    #print(temp)
    x.close()
    return temp

if __name__=="__main__":
    plt.ion()
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
    

    ntemp=100
    fpga_temps=numpy.zeros(ntemp)
    rpi_temps=numpy.zeros(ntemp)
    rpi_temps[:]=get_rpi_temperature()
    freq=numpy.arange(2048)/2048*125
    fig, axs = plt.subplots(2, 1)
    ax0 = axs[0]
    ax1 = axs[1]

    iter=0
    try:
        digitizer=albatrosdigitizer.AlbatrosDigitizer(snap_ip, snap_port, logger=logger)
        pols=pols.split()
        while True:
            start_time = time.time()
	    pol_data = digitizer.read_pols(pols, ">2048q")
            fpga_temp=digitizer.get_fpga_temperature()
            rpi_temp=get_rpi_temperature()
            if iter<ntemp:
                fpga_temps[iter]=fpga_temp
                rpi_temps[iter]=rpi_temp
            else:
                fpga_temps[:-1]=fpga_temps[1:]
                fpga_temps[-1]=fpga_temp
                rpi_temps[:-1]=rpi_temps[1:]
                rpi_temps[-1]=rpi_temp
            print('got pol data at time ',start_time,type(pol_data),fpga_temp,rpi_temp)


            #plt.figure(1)
            #plt.clf()
            if iter==0:
                fpga_temps[:]=fpga_temp
                line0,=ax0.semilogy(pol_data['pol00'])
                line1,=ax0.semilogy(pol_data['pol11'])
                line_temp,=ax1.plot(fpga_temps)
                line_rpi,=ax1.plot(rpi_temps)
            else:
                line0.set_ydata(pol_data['pol00'])
                line1.set_ydata(pol_data['pol11'])
                line_temp.set_ydata(fpga_temps)
                line_rpi.set_ydata(rpi_temps)
                #ax1.set_ylim(min(numpy.min(fpga_temps),numpy.min(rpi_temps))-1, max(numpy.max(fpga_temps), numpy.max(rpi_temps))+1)
                ax0.relim()
                ax0.autoscale_view()
                ax1.relim()
                ax1.autoscale_view()
            #plt.clf()
            #plt.semilogy(pol_data['pol00'])
            #plt.show()
            #plt.pause(0.01)
            #plt.show(block=False)            
            #plt.pause(0.1)
            fig.canvas.flush_events()
            iter=iter+1
    finally:
	logger.info("Terminating DAQ at %s"%datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
