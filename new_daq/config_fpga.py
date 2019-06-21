#!/usr/bin/python
import argparse
import ConfigParser
import logging
import os
import datetime
import albatrosdigitizer
import albatros_daq_utils
import numpy

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="Script to initialise SNAP Board")
    parser.add_argument("-c", "--configfile", type=str, default="config.ini", help=".ini file with parameters to configure firmware")
    args=parser.parse_args()

    config_file=ConfigParser.SafeConfigParser()
    config_file.read(args.configfile)

    logger=logging.getLogger("albatros2_config_fpga")
    logger.setLevel(logging.INFO)

    log_dir=config_file.get("albatros2", "init_log_directory")
    if not os.path.isdir(log_dir):
        os.mkdir(log_dir)
    log_name=config_file.get("albatros2", "init_log_name")
    file_logger=logging.FileHandler(log_dir+log_name+"_"+datetime.datetime.now().strftime("%d%m%Y_%H%M%S")+".log")
    file_format=logging.Formatter("%(asctime)s %(name)-12s %(message)s", "%d-%m-%Y %H:%M:%S")
    file_logger.setFormatter(file_format)
    file_logger.setLevel(logging.INFO)
    logger.addHandler(file_logger)
    logger.info("########################################################################################")
    snap_ip=config_file.get("albatros2", "snap_ip")
    logger.info("# (1) SNAP Board IP address: %s"%(snap_ip))
    snap_port=int(config_file.get("albatros2", "snap_port"))
    logger.info("# (2) SNAP Board port: %d"%(snap_port))
    fpg_file=config_file.get("albatros2", "fpg_file")
    logger.info("# (3) fpg file: %s"%(fpg_file))
    fftshift=int(config_file.get("albatros2", "fftshift"), 16)
    logger.info("# (4) fftshift: %d"%(fftshift))
    acclen=int(config_file.get("albatros2", "accumulation_length"))
    logger.info("# (5) Accumulation length: %d"%(acclen))
    bits=int(config_file.get("albatros2", "bits"))
    logger.info("# (6) Baseband bits: %d"%(bits))
    max_bytes_per_packet=int(config_file.get("albatros2", "max_bytes_per_packet"))
    logger.info("# (7) Max bytes per packet: %d"%(max_bytes_per_packet))
    dest_ip=config_file.get("albatros2", "destination_ip")
    logger.info("# (8) Destination IP address: %s"%(dest_ip))
    dest_port=int(config_file.get("albatros2", "destination_port"))
    logger.info("# (9) Destination port: %d"%(dest_port))
    dest_mac=config_file.get("albatros2", "destination_mac_address")
    logger.info("# (10) Destination MAC address: %s"%(dest_mac))
    ref_clock=config_file.get("albatros2", "synthesizer_clock_ref")
    if ref_clock=="none":
        logger.info("# (11) Clock source: External/250 Mhz")
        ref_clock=None
    else:
        logger.info("# (11) Clock source: Internal/%s Mhz"%(ref_clock))
        ref_clock=int(ref_clock)
    channels=config_file.get("albatros2", "channels")
    logger.info("# (12) Channels: %s"%(channels))
    channels_coeffs=config_file.get("albatros2", "channel_coeffs")
    logger.info("# (13) Channel coeffs: %s"%(channels_coeffs))
    logger.info("# (14) Start of log file name: %s"%(log_name+"_%d%m%Y%_%H%M%S"))
    logger.info("# (15) Log directory: %s"%(log_dir))
    logger.info("########################################################################################")
    drives_full=config_file.get("albatros2", "drives_full")
    if drives_full=="true":
        logger.info("All drives are full. Holding here!!!")
        while True:
            pass
        
    try:
        chans=albatros_daq_utils.get_channels_from_str(channels, bits)
        print(chans)
        spec_per_packet=albatros_daq_utils.get_nspec(chans, max_nbyte=max_bytes_per_packet)
        print(spec_per_packet)
        bytes_per_spectrum=chans.shape[0]
        print(bytes_per_spectrum)
        albatros_snap=albatrosdigitizer.AlbatrosDigitizer(snap_ip, snap_port, logger=logger)
    	albatros_snap.initialise(fpg_file, ref_clock, fftshift, acclen, bits,
                                 spec_per_packet, bytes_per_spectrum, dest_ip, dest_port, dest_mac)
        albatros_snap.set_channel_order(chans, bits)
        if bits==2:
            albatros_snap.set_two_bit_threshold(281)
        if bits==4:
            albatros_snap.set_channel_coeffs(channels_coeffs)
    finally:
        logger.info("Finished initialising at %s"%datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
