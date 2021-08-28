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
import lbtools_l
import albatrosdigitizer
import supertools


def unpack_4bit(buf):
    raw=numpy.frombuffer(buf,'int8')
    #print('raw[:4]=',raw[:4])
    re=numpy.asarray(numpy.right_shift(numpy.bitwise_and(raw, 0xf0), 4), dtype="int8")
    re[re>8]=re[re>8]-16
    im=numpy.asarray(numpy.bitwise_and(raw, 0x0f), dtype="int8")
    im[im>8]=im[im>8]-16
    #print('extrema are ',re.max(),re.min(),im.max(),im.min())
    vec=1J*im+re    
    #print('inside unpack, answers are ',re[0],im[0],vec.dtype)
    return vec
def unpack_packet(packet,bits,spec_per_packet):
    specno=numpy.frombuffer(packet,'>I',1)
    if bits==4:
        vec=unpack_4bit(packet[4:])
        nchan=len(vec)//spec_per_packet//2
        pol0=numpy.reshape(vec[::2],[spec_per_packet,nchan])
        pol1=numpy.reshape(vec[1::2],[spec_per_packet,nchan])
        return pol0,pol1

def write_header(file_object, chans, spec_per_packet, bytes_per_packet, bits):
    have_trimble = True
    header_bytes = 8*10 + 8*len(chans) # 8 bytes per element in the header
    gpsread = lbtools_l.lb_read()
    gps_time = gpsread[0]
#    gps_time = trimble_utils.get_gps_timestamp_trimble(maxtime=2, maxiter=1)
    if gps_time is None:
	logger.info('File timestamp coming from RPi clock. This is unreliable.')
        have_trimble = False
        gps_time = time.time()
    print('GPS time is now ', gps_time)
    file_header=numpy.asarray([header_bytes, bytes_per_packet, len(chans), spec_per_packet, bits, have_trimble], dtype='>Q')
    file_header.tofile(file_object)
    numpy.asarray(chans, dtype=">Q").tofile(file_object)
    gps_time=numpy.asarray([0, gps_time], dtype='>Q') # setting gps_week = 0 to flag the new header format with GPS ctime timestamp
    gps_time.tofile(file_object)
    lat_lon = gpsread[1]
#    latlon=trimble_utils.get_latlon_trimble(maxtime=2, maxiter=1)
    if lat_lon is None:
        logger.info("Can't speak to LB, so no position information")
        latlon={}
        latlon['lat']=0
        latlon['lon']=0
        latlon['elev']=0
    else:
        latlon={}
        latlon['lat']=lat_lon[3]
        latlon['lon']=lat_lon[2]
        latlon['elev']=lat_lon[4]
        print 'lat/lon/elev are ',latlon['lat'],latlon['lon'],latlon['elev']    

#    if latlon is None:
#        logger.info("Can't speak to trimble, so no position information")
#        latlon={}
#        latlon['lat']=0
#        latlon['lon']=0
#        latlon['elev']=0
#    else:
#        print 'lat/lon/elev are ',latlon['lat'],latlon['lon'],latlon['elev']
        
    latlon=numpy.asarray([latlon['lat'],latlon['lon'],latlon['elev']],dtype='>d')
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
    baseband_log_dir=config_file.get("albatros2", "dump_baseband_log_directory")
    if not os.path.isdir(baseband_log_dir):
        os.mkdir(baseband_log_dir)
    file_logger=logging.FileHandler(baseband_log_dir+"albatros_dump_baseband_"+datetime.datetime.now().strftime("%d%m%Y_%H%M%S")+".log")
    file_format=logging.Formatter("%(asctime)s %(name)s %(message)s", "%d-%m-%Y %H:%M:%S")
    file_logger.setFormatter(file_format)
    file_logger.setLevel(logging.INFO)
    logger.addHandler(file_logger)
    logger.info("########################################################################################")
    dest_ip=config_file.get("albatros2", "destination_ip")
    logger.info("# (1) Destination ip: %s"%(dest_ip))
    dest_port=config_file.getint("albatros2", "destination_port")
    logger.info("# (2) Destination port: %d"%(dest_port))
    snap_ip=config_file.get("albatros2","snap_ip")
    snap_port=config_file.get("albatros2","snap_port")
    channels=config_file.get("albatros2", "channels")
    logger.info("# (3) Channels: %s"%(channels))
    channel_coeffs=config_file.get("albatros2", "channel_coeffs")
    logger.info("# (3b) Channel coeffs: %s"%(channel_coeffs))
    try:
        autotune=config_file.get("albatros2","autotune")
    except:
        autotune='0'
    autotune=int(autotune)
    logger.info("# (3c) Autotune is %d"%(autotune))
    bits=config_file.getint("albatros2", "bits")
    logger.info("# (4) Baseband bits: %d"%(bits))
    max_bytes_per_packet=config_file.getint("albatros2", "max_bytes_per_packet")
    logger.info("# (5) Max bytes per packet: %d"%(max_bytes_per_packet))
    drives_full=config_file.getboolean("albatros2", "drives_full")
    logger.info("# (6) Drives full: %r"%(drives_full))
    drive_safety=config_file.getfloat("albatros2", "drive_safety")
    logger.info("# (7) Drive safety percentage: %.2f"%(drive_safety))
    file_size=config_file.getfloat("albatros2", "file_size")
    logger.info("# (8) File size: %f"%(file_size))
    dump_baseband_directory_name=config_file.get("albatros2", "dump_baseband_directory_name")
    logger.info("# (9) Baseband directory name: %s"%(dump_baseband_directory_name))
    logger.info("# (10) Log directory: %s"%(baseband_log_dir))
    try:
        reboot_when_full=config_file.get("albatros2","reboot_when_full")
    except:
        reboot_when_full='0'
    reboot_when_full=int(reboot_when_full)
    if reboot_when_full:
        logger.info("# (11) Will reboot when first drive fills up.")
    else:
        logger.info("# (11) Will not reboot when first drive fills up.")
    
    try:
        have_mux=config_file.get("albatros2","have_mux")
    except:
        have_mux='0'
    have_mux=int(have_mux)
    if have_mux:
        logger.info("# (12) Expecting to be hooked up to mux box.")
    else:
        logger.info("# (12) Not expecting to be hooked up to mux box.")
    

    logger.info("########################################################################################")

    sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  
    try:
        sock.bind((dest_ip, dest_port))
        logger.info("Connected to %s:%d"%(dest_ip, dest_port))
    except:
        logger.error("Cannot bind to %s:%d"%(dest_ip, dest_port))

    chans=albatros_daq_utils.get_channels_from_str(channels, bits)
    spec_per_packet=albatros_daq_utils.get_nspec(chans, max_nbyte=max_bytes_per_packet)
    bytes_per_spectrum=chans.shape[0]
    bytes_per_packet=bytes_per_spectrum*spec_per_packet+4 #the 4 extra bytes is for the spectrum number
    packet=bytearray(bytes_per_packet)
    num_of_packets_per_file=int(math.floor(file_size*1.0e9/bytes_per_packet))


    if (autotune) and (bits==4):
        logger.info("auto-tuning baseband coefficients")
        print("Going to tune channel levels")
        #print("chans is ",chans)
        #print("expected size is ",spec_per_packet,bytes_per_spectrum,bytes_per_packet,bits)
        #print('ports are ',snap_ip,snap_port)
        albatros_snap=albatrosdigitizer.AlbatrosDigitizer(snap_ip, snap_port, logger=logger)
        packets_to_average=3000//spec_per_packet
        #packets_to_average=50
        print('going to average ',packets_to_average,' packets')
        pol0=[None]*packets_to_average
        pol1=[None]*packets_to_average
        isok=False
        npass=20
        ipass=0
        coeffs=albatros_daq_utils.get_coeffs_from_str(channel_coeffs)
        #print('starting coeffs types is ',coeffs.dtype)
        #set the levels to the currently specified ones, as otherwise this script may be
        #adjusting levels thinking the levels are set to the file when they could be
        #something else based on previous runs.
        albatros_snap.set_channel_coeffs(coeffs, bits)

        while isok==False:
            for i in range(packets_to_average):
                sock.recvfrom_into(packet, bytes_per_packet)
                #ii=numpy.frombuffer(packet,'>I',1)
                pol0[i],pol1[i]=unpack_packet(packet,bits,spec_per_packet)
                #print('first entry is ',ii,tmp[0])
                #print('stds are ',numpy.std(pol0),numpy.std(pol1))
            pp0=numpy.vstack(pol0)
            pp1=numpy.vstack(pol1)
            #print('shapes are ',pol0.shape,pol1.shape)
            #print('stds are ',numpy.std(pp0,axis=0),numpy.std(pp1,axis=0))
            railed=[numpy.mean(numpy.abs(numpy.real(pp0))==7),numpy.mean(numpy.abs(numpy.real(pp1))==7)]
            max_std=numpy.max([numpy.max(numpy.std(pp0,axis=0)),numpy.max(numpy.std(pp1,axis=0))])
            #print('max_std is ',max_std,bits,railed)
            #print('coeffs max is ',coeffs.max(),coeffs.dtype)
            if max_std>7:
                print('shrinking coeffs')
                coeffs=coeffs//2
                coeffs=numpy.asarray(coeffs,dtype=">I")
                albatros_snap.set_channel_coeffs(coeffs, bits)
            elif max_std<3.5:
                print('increasing coeffs')
                coeffs=coeffs*2
                coeffs=numpy.asarray(coeffs,dtype=">I")
                albatros_snap.set_channel_coeffs(coeffs, bits)
            else:
                print('max_std is ',max_std,' with ',railed,' railed fraction')
                logger.info("Tuned levels with coefficient %d, max std %.3f, and railed percents %.2f %.2f"%(coeffs.max(),max_std,railed[0]*100,railed[1]*100))
                isok=True
            ipass=ipass+1
            if ipass==npass:
                print('failed to converge after ',npass,' tuning steps')
                isok=True

    drives=albatros_daq_utils.list_drives_to_write_too("MARS")
    logger.info("Found these drive/s")
    logger.info("%-17s %-17s %-17s %-17s %-5s%% %-s"%("Device", "Total", "Used", "Free", "Use ", "Mount"))
    for drive in drives:
        logger.info("%-17s %-17s %-17s %-17s %-5s%% %-s"%(drive["Device"], drive["Blocks"], drive["Used"], drive["Available"], drive["Use%"], drive["Mounted on"]))
    
    reads_for_many_packets=50000
    time_for_many_packets=(2048*2/250e6)*spec_per_packet*reads_for_many_packets
    
    while not drives_full:
        if len(drives)==0:
            logger.info("No drives found. Check if drives are connected and mounted")
	    print("NO DRIVES FOUND! NOT SAVING BASEBAND!")
    	else:
            for drive in drives:
                drive_path=drive["Mounted on"]
                number_of_files=albatros_daq_utils.num_files_can_write(drive_path, drive_safety, file_size)
                if number_of_files>0:
                    write_path=drive_path+"/"+dump_baseband_directory_name
                    if not os.path.isdir(write_path):
                        os.mkdir(write_path)
                    for i in range(number_of_files):
                        directory_time=str(int(time.time()))[:5]
                        if not os.path.isdir(write_path+"/"+directory_time):
                            os.mkdir(write_path+"/"+directory_time)
                        file_time=int(time.time())
                        file_path=write_path+"/"+directory_time+"/"+str(file_time)+".raw"
                        baseband_file=open(file_path, "w")
                        write_header(baseband_file, chans, spec_per_packet, bytes_per_packet, bits)
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
                else:
                    logger.info("Drive " + repr(drive_path)+" full at start of run.")
                    if have_mux:
                        supertools.mark_drive_full()
                number_of_files=albatros_daq_utils.num_files_can_write(drive_path, drive_safety, file_size)
                if number_of_files<1:
                    logger.info("Drive "+repr(drive_path)+" has been filled.")
                    if have_mux:
                        supertools.mark_drive_full()
                    if reboot_when_full:
                        os.system("sudo reboot")
                    
            drives_full=True
        
    logger.info("All drives full. Not saving baseband. Pausing here!!!")
    while True:
        pass
