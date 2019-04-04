#!/usr/bin/python
import argparse
import ConfigParser
import socket
import logging
import time
import os
import albatros_daq_utils
import datetime
import math
import trimble_utils
import numpy
import subprocess

def write_header(file_object, chans, spec_per_packet, bytes_per_packet, bits, have_trimble):
    header_bytes=8*10+8*len(chans)
    file_header=numpy.asarray([header_bytes, bytes_per_packet, len(chans), spec_per_packet, bits, have_trimble], dtype='>Q')
    file_header.tofile(file_object)
    numpy.asarray(chans, dtype=">Q").tofile(file_object)
    if have_trimble:
        gps_time=trimble_utils.get_gps_time_trimble()
        if gps_time is None:
            gps_time={}
            gps_time['week']=0
            gps_time['seconds']=0
        else:
            print 'ps time is now ',gps_time['week'],gps_time['seconds']
        gps_time=numpy.asarray([gps_time['week'],gps_time['seconds']],dtype='>Q')
        gps_time.tofile(file_object)
        latlon=trimble_utils.get_latlon_trimble()
        if latlon is None:
            latlon={}
            latlon['lat']=0
            latlon['lon']=0
            latlon['elev']=0
        else:
            print 'lat/lon/elev are ',latlon['lat'],latlon['lon'],latlon['elev']
        latlon=numpy.asarray([latlon['lat'],latlon['lon'],latlon['elev']],dtype='>q')
        latlon.tofile(file_object)
    else:
        gps_time={"week":0, "seconds":0}
        gps_time=numpy.asarray([gps_time['week'],gps_time['seconds']],dtype='>Q')
        gps_time.tofile(file_object)
        latlon={"lat":0, "lon":0, "elev":0}
        latlon=numpy.asarray([latlon['lat'],latlon['lon'],latlon['elev']],dtype='>q')
        latlon.tofile(file_object)
    return None

def spin_down_drive(drive_block, mount_point):
    pass

def spin_up_drive(drive_block, partition, mount_point):
    pass

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="Script to save baseband")
    parser.add_argument("-c", "--configfile", type=str, default="config.ini", help="Config file with all the parameters")
    args=parser.parse_args()

    config_file=ConfigParser.SafeConfigParser()
    config_file.read(args.configfile)

    logger=logging.getLogger("albatros2_dump_baseband")
    logger.setLevel(logging.INFO)
    baseband_log_dir=config_file.get("albatros2", "baseband_log_directory")
    if not os.path.isdir(baseband_log_dir):
        os.mkdir(baseband_log_dir)
    baseband_log_name=config_file.get("albatros2", "baseband_log_name")
    file_logger=logging.FileHandler(baseband_log_dir+baseband_log_name+"_"+datetime.datetime.now().strftime("%d%m%Y_%H%M%S")+".log")
    file_format=logging.Formatter("%(asctime)s %(name)s %(message)s", "%d-%m-%Y %H:%M:%S")
    file_logger.setFormatter(file_format)
    file_logger.setLevel(logging.INFO)
    logger.addHandler(file_logger)
    logger.info("########################################################################################")
    dest_ip=config_file.get("albatros2", "destination_ip")
    logger.info("# (1) Destination ip: %s"%(dest_ip))
    dest_port=int(config_file.get("albatros2", "destination_port"))
    logger.info("# (2) Destination port: %d"%(dest_port))
    channels=config_file.get("albatros2", "channels")
    logger.info("# (3) Channels: %s"%(channels))
    bits=int(config_file.get("albatros2", "bits"))
    logger.info("# (4) Baseband bits: %d"%(bits))
    max_bytes_per_packet=int(config_file.get("albatros2", "max_bytes_per_packet"))
    logger.info("# (5) Max bytes per packet: %d"%(max_bytes_per_packet))
    drive_safety=int(config_file.get("albatros2", "drive_safety"))
    logger.info("# (6) Drive safety percentage: %d"%(drive_safety))
    file_size=float(config_file.get("albatros2", "file_size"))
    logger.info("# (7) File size: %f"%(file_size))
    baseband_directory_name=config_file.get("albatros2", "baseband_directory_name")
    logger.info("# (8) Baseband directory name: %s"%(baseband_directory_name))
    logger.info("# (9) Log file name: %s"%(baseband_log_name+"_%d%m%Y%_%H%M%S"))
    logger.info("# (10) Log directory: %s"%(baseband_log_dir))
    logger.info("########################################################################################")

    sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  
    try:
        sock.bind((dest_ip, dest_port))
        logger.info("Connected to %s:%d"%(dest_ip, dest_port))
    except:
        logger.error("Cannot bind to %s:%d"%(dest_ip, dest_port))

    have_trimble=False
    if trimble_utils.set_clock_trimble():
        print 'Successfully updated system clock to gps time from trimble.'
        have_trimble=True
    else:
        print 'Unable to read time from trimble.'
    if have_trimble:
        print "Trimble GPS clock successfully detected."
    else:
        print "Trimble GPS clock not found.  Timestamps will come from system clock."

    chans=albatros_daq_utils.get_channels_from_str(channels, bits)
    spec_per_packet=albatros_daq_utils.get_nspec(chans, max_nbyte=max_bytes_per_packet)
    bytes_per_spectrum=chans.shape[0]
    bytes_per_packet=bytes_per_spectrum*spec_per_packet+4 #the 4 extra bytes is for the spectrum number
    packet=bytearray(bytes_per_packet)
    num_of_packets_per_file=int(math.floor(file_size*1.0e9/bytes_per_packet))
    
    drives=albatros_daq_utils.list_drives_to_write_too()
    logger.info("Found these drive/s: ")
    print(drives)
    
    reads_for_many_packets=50000
    time_for_many_packets=(2048*2/250e6)*spec_per_packet*reads_for_many_packets

    drives_full=False
    
    while not drives_full:
        for drive in drives:
            drive_path=drive["Mounted on"]
            number_of_files=albatros_daq_utils.num_files_can_write(drive_path, drive_safety/100., file_size)
            write_path=drive_path+"/"+baseband_directory_name
            if not os.path.isdir(write_path):
                os.mkdir(write_path)
            for i in range(number_of_files):
                directory_time=str(int(time.time()))[:5]
                if not os.path.isdir(write_path+"/"+directory_time):
                    os.mkdir(write_path+"/"+directory_time)
                file_time=int(time.time())
                file_path=write_path+"/"+directory_time+"/"+str(file_time)+".raw"
                baseband_file=open(file_path, "w")
                write_header(baseband_file, chans, spec_per_packet, bytes_per_packet, bits, have_trimble)
                logger.info("Writing file "+str(i+1)+" of "+str(number_of_files)+" to "+file_path)
                time_for_many_reads=time.time()
                num_of_reads=0
                for j in range(num_of_packets_per_file):
                    sock.recvfrom_into(packet, bytes_per_packet)
                    baseband_file.write(packet)
                    num_of_reads=num_of_reads+1
                    if num_of_reads==reads_for_many_packets:
                        time_after_many_reads=time.time()
                        print("Data size is ", len(packet), type(packet), time_after_many_reads-time_for_many_reads, time_for_many_packets)
                        time_for_many_reads=time_after_many_reads
                        num_of_reads=0
                baseband_file.close()
        drives_full=True
                    
    logger.info("All drives full. Not saving baseband")

    while True:
        pass
