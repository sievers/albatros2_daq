#!/usr/bin/python
import argparse
import yaml
import socket
import logging
import time
import os
import utils
import datetime
import math
import trimble_utils
import numpy
import subprocess
import smbus
import ds3231
import sys
import traceback
import psutil

def write_header(file_object, chans, spec_per_packet, bytes_per_packet, bits, logger):
    header_bytes=8*10+8*len(chans)
    have_trimble=False
    gps_time=trimble_utils.get_gps_time_trimble()
    if gps_time is None:
        logger.info("File timestamp coming for RPi Clock. This is unrealiable")
        gps_time_rpi=utils.gps_time_from_rtc()
        print(gps_time_rpi)
        gps_time={}
        gps_time['week']=gps_time_rpi["week"]
        gps_time['seconds']=gps_time_rpi["seconds"]
    else:
        logger.debug('ps time is now; week: %d, seconds: %d'%(gps_time['week'],gps_time['seconds']))
        have_trimble=True
    file_header=numpy.asarray([header_bytes, bytes_per_packet, len(chans), spec_per_packet, bits, have_trimble], dtype='>Q')
    file_header.tofile(file_object)
    numpy.asarray(chans, dtype=">Q").tofile(file_object)
    gps_time=numpy.asarray([gps_time['week'],gps_time['seconds']],dtype='>Q')
    gps_time.tofile(file_object)
    latlon=trimble_utils.get_latlon_trimble()
    if latlon is None:
        logger.info("Can't speak to trimble, so no position information")
        latlon={}
        latlon['lat']=0
        latlon['lon']=0
        latlon['elev']=0
    else:
        logger.debug('lat/lon/elev are %f/%f/%f'%(latlon['lat'],latlon['lon'],latlon['elev']))
    latlon=numpy.asarray([latlon['lat'],latlon['lon'],latlon['elev']],dtype='>d')
    latlon.tofile(file_object)
    return None

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("-c", "--configfile", type=str, default="config.yaml", help="yaml file with parameters for dump baseband")
    args=parser.parse_args()

    parameters=None
    with open(args.configfile, "r") as cf:
        parameters=yaml.load(cf.read(), yaml.FullLoader)

    log_level=parameters["log_level"]
    log_directory=parameters["log_directory"]

    if not os.path.isdir(log_directory):
        os.makedirs(log_directory)

    logging.basicConfig(level=log_level,
                        format='%(asctime)s %(name)-20s %(levelname)-8s %(message)s',
                        datefmt="%d-%m-%Y %H:%M:%S",
                        filename=log_directory+"/dump_baseband_"+datetime.datetime.now().strftime("%d%m%Y_%H%M%S")+".log",
                        filemode='w')

    logger=logging.getLogger("dump_baseband")

    i2c_bus=smbus.SMBus(1)
    rtc=ds3231.DS3231(i2c_bus, 0x68)

    snap_board=parameters["snap-board"]
    firmware=parameters["firmware"]
    synthesizer=parameters["synthesizer"]
    adcs=parameters["adcs"]
    pfb=parameters["pfb"]
    test_vector_generator=parameters["test-vector-generator"]
    xcorr=parameters["xcorr"]
    output_control=parameters["output-control"]
    packetiser=parameters["packetiser"]
    baseband=parameters["baseband"]
    harddrives=parameters["hard-drives"]
    spectra=parameters["spectra"]
    ethernet=parameters["ethernet"]

    chans=utils.get_channels_from_str(output_control["channels"], output_control["bits"])
    spectra_per_packet=utils.get_nspec(chans, max_nbyte=packetiser["max_bytes_per_packet"])
    bytes_per_spectrum=chans.shape[0]
    bytes_per_packet=spectra_per_packet*bytes_per_spectrum+4
    coeffs=utils.get_coeffs_from_str(output_control["channel_coeffs"])

    logger.info("############### config-parameters ###############")
    logger.info("SNAP-BOARD:")
    logger.info("\tip: %s"%(snap_board["ip"]))
    logger.info("\tport: %d"%(snap_board["port"]))
    logger.info("FIRMWARE:")
    logger.info("\tfpg_file: %s"%(firmware["fpg_file"]))
    logger.info("SYNTHESIZER:")
    logger.info("\tinput: %s"%(synthesizer["input"]))
    logger.info("\tfrequency: %d"%(synthesizer["frequency"]))
    logger.info("ADCS:")
    logger.info("\tadc digital gain: %d"%(adcs["adc_digital_gain"]))
    logger.info("\tpowerdown unused adcs: %s"%(adcs["powerdown_unused_adcs"]))
    logger.info("PFB:")
    logger.info("\tfft shift: %s"%(hex(pfb["fftshift"])[:-1]))
    logger.info("TEST-VECTOR-GENERATOR:")
    logger.info("\tenable: %s"%(str(test_vector_generator["enable"])))
    logger.info("\tdata: %s"%(test_vector_generator["data"]))
    logger.info("XCORR:")
    logger.info("\taccumulation length: %d"%(xcorr["accumulation_length"]))
    logger.info("OUTPUT CONTROL:")
    logger.info("\tbits: %d"%(output_control["bits"]))
    logger.info("\tchannels: %s"%(output_control["channels"]))
    logger.info("\tchannel coeffs: %s"%(output_control["channel_coeffs"]))
    logger.info("PACKETISER:")
    logger.info("\tmax bytes per packet: %d"%(packetiser["max_bytes_per_packet"]))
    logger.info("ETHERNET:")
    logger.info("\tlocal ip: %s"%(ethernet["local_ip"]))
    logger.info("\tlocal port: %d"%(ethernet["local_port"]))
    logger.info("\tlocal mac: %s"%(hex(ethernet["local_mac"])[:-1]))
    logger.info("\tdestination ip: %s"%(ethernet["destination_ip"]))
    logger.info("\tdestination port: %d"%(ethernet["destination_port"]))
    destination_mac=None
    eth0=psutil.net_if_addrs()["eth0"]
    for link in eth0:
        if link.family == psutil.AF_LINK:
            destination_mac=int("0x"+link.address.replace(":", ""), 16)
    logger.info("\tdestination mac: %s"%(hex(destination_mac)[:-1]))
    logger.info("BASEBAND:")
    logger.info("\tdrive safety: %.2f"%(baseband["drive_safety"]))
    logger.info("\tfile size: %.2f"%(baseband["file_size"]))
    logger.info("\tdirectory name: %s"%(baseband["directory_name"]))
    logger.info("\tmount directory: %s"%(baseband["mount_directory"]))
    logger.info("HARD-DRIVES:")
    for drive in harddrives:
        drive_tag=drive.keys()[0]
        logger.info("\t%s:"%(drive_tag))
        logger.info("\t\tlabel: %s"%(drive[drive_tag]["label"]))
        logger.info("\t\tpm: %s"%(drive[drive_tag]["pm"]))
    logger.info("SPECTRA:")
    logger.info("\tdiff: %s"%(spectra["diff"]))
    logger.info("\tcompress: %s"%(spectra["compress"]))
    logger.info("\tfile size: %d"%(spectra["file_size"]))
    logger.info("\tdirectory name: %s"%(spectra["directory_name"]))
    logger.info("\tdata directory: %s"%(spectra["data_directory"]))
    logger.info("CALCULATED PARAMETERS:")
    logger.info("\tspectra per packet: %d"%(spectra_per_packet))
    logger.info("\tbytes per spectrum: %d"%(bytes_per_spectrum))
    logger.info("\tbytes per packet: %d"%(bytes_per_packet))
    logger.info("###################### end ######################")
    
    sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.bind((ethernet["destination_ip"], ethernet["destination_port"]))
        ip, port=sock.getsockname()
        logger.info("Connected to %s:%d"%(ip, port))
        logger.info("Setting socket timeout to 10 seconds")
        sock.settimeout(10.0)
    except:
        logger.fatal("Cannot bind to %s:%d"%(ethernet["destination_ip"], ethernet["destination_port"]))
        exit(1)

    packet=bytearray(bytes_per_packet)

    num_of_packets_per_file=int(math.floor(baseband["file_size"]*1.024e6/bytes_per_packet))

    reads_for_many_packets=50000
    time_for_many_packets=(2048*2/250e6)*spectra_per_packet*reads_for_many_packets

    try:
        print(harddrives)
        for drive in harddrives:
            print(drive)
            drive_tag=drive.keys()[0]
            number_of_files=utils.num_files_can_write(baseband["mount_directory"]+drive[drive_tag]["label"], 
                                                      baseband["drive_safety"], 
                                                      baseband["file_size"])
            logger.debug("Number of files: %d"%(number_of_files))
            if number_of_files>0:
                write_path=baseband["mount_directory"]+drive[drive_tag]["label"]+"/"+baseband["directory_name"]
                for i in range(number_of_files):
                    directory_time=str(int(time.time()))[:5]
                    if not os.path.isdir(write_path+"/"+directory_time):
                        os.makedirs(write_path+"/"+directory_time)
                    file_time=int(time.time())
                    file_path=write_path+"/"+directory_time+"/"+str(file_time)+".raw"
                    baseband_file=open(file_path, "w")
                    write_header(baseband_file, chans, spectra_per_packet, bytes_per_packet,
                                 output_control["bits"], logger)
                    logger.info("Writing file "+str(i+1)+" of "+str(number_of_files)+" to "+file_path)
                    time_for_many_reads=time.time()
                    num_of_reads=0
                    for j in range(num_of_packets_per_file):
                        sock.recvfrom_into(packet, bytes_per_packet)
                        baseband_file.write(packet)
                        num_of_reads=num_of_reads+1
                        if num_of_reads==reads_for_many_packets:
                            time_after_many_reads=time.time()
                            logger.debug("Data size is %s, %s, %d, %.4f"%(len(packet),
                                                                          type(packet),
                                                                          time_after_many_reads-time_for_many_reads,
                                                                          time_for_many_packets))
                            time_for_many_reads=time_after_many_reads
                            num_of_reads=0
                    baseband_file.close()
    except:
        logger.info("Something went wrong!!!. This is the error:")
        exc_type, exc_value, exc_traceback=sys.exc_info()
        logger.error("%s"%(traceback.format_exc()))
    finally:
        sock.close()
        logger.info("Terminated at %s"%(datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")))
