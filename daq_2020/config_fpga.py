#!/usr/bin/python
import argparse
import yaml
import logging
import os
import datetime
import albatrosdigitizer
import utils
import numpy
import trimble_utils
import sys
import traceback
import subprocess
import smbus
import ds3231
import time
import psutil

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("-c", "--configfile", type=str, default="config.yaml", help="yaml file with parameters for config fpga")
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
                        filename=log_directory+"/config_fpga_"+datetime.datetime.now().strftime("%d%m%Y_%H%M%S")+".log",
                        filemode='w')

    logger=logging.getLogger("config_fpga")

    if trimble_utils.set_clock_trimble():
        logger.info("Trimble GPS clock successfully detected.")
        logger.info("Successfully updated system clock to gps time from trimble.")
    else:
        logger.info("Unable to read time from trimble. Using RPi system clock which is unrealiable")

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

    ready=False
    try:
        albatros_snap=albatrosdigitizer.AlbatrosDigitizer(snap_board["ip"], snap_board["port"])
        logger.info("Initialising FPGA")
        fpga_tries=3
        for i in range(fpga_tries):
            fpga_success=albatros_snap.initialise_fpga(firmware["fpg_file"])
            if fpga_success:
                logger.info("FPGA initialised after %d attempts"%(i+1))
                break
            elif i<(adc_tries-1):
                logger.error("FPGA initialisation failed. Retrying!!!")
                time.sleep(5)
            else:
                logger.fatal("FPGA initialisation failed after %d tries. Exiting!!!"%(i+1))
                raise
        if synthesizer["input"].lower()=="internal":
            ref_clock=synthesizer["frequency"]
        else:
            ref_clock=None
        logger.info("Initialising ADC's")
        adc_tries=3
        for i in range(adc_tries):
            adc_success=albatros_snap.initialise_adcs(ref_clock, adcs["adc_digital_gain"], adcs["powerdown_unused_adcs"])
            if adc_success:
                logger.info("ADC's initialised after %d attempts"%(i+1))
                break
            elif i<(adc_tries-1):
                logger.error("ADC initialisation failed. Retrying!!!")
                time.sleep(5)
            else:
                logger.fatal("ADC initialisation failed after %d tries. Exiting!!!"%(i+1))
                raise
        adc_stats=albatros_snap.get_adc_stats()
        logger.info("ADC bits used: (adc0, %.2f) (adc3, %.2f)"%(adc_stats["adc0"]["bits_used"], adc_stats["adc3"]["bits_used"]))
        logger.info("Initialising PFB")
        albatros_snap.initialise_pfb(pfb["fftshift"])
        logger.info("Initialising XCORR")
        albatros_snap.initialise_xcorr(xcorr["accumulation_length"])        
        logger.info("Initialising OUTPUT CONTROL")
        albatros_snap.initialise_output_control(output_control["bits"], chans, coeffs)
        logger.info("Initialising PACKETISER")
        albatros_snap.initialise_packetiser(spectra_per_packet, bytes_per_spectrum)
        logger.info("Initialising GbE")
        albatros_snap.initialise_gbe(ethernet["destination_ip"], ethernet["destination_port"], destination_mac)
        logger.info("Initialising sync")
        albatros_snap.sync()
        time.sleep(2.5)
        logger.info("Enabling GbE")
        albatros_snap.gbe_enable()
        time.sleep(2.5)
        pfb_overflow=0
        for i in range(3):
            if albatros_snap.check_pfb_overflow():
                pfb_overflow=1
                time.sleep(1)
        if pfb_overflow:
            logger.critical("PFB overflowing")
        else:
            logger.info("PFB not overflowing")
        gbe_overflow=0
        for j in range(3):
            if albatros_snap.check_gbe_overflow():
                gbe_overflow=1
                time.sleep(1)
        if gbe_overflow:
            logger.critical("GbE overflowing")
        else:
            logger.info("GbE not overflowing")
        if not(pfb_overflow) or not(gbe_overflow):
            ready=True
    except:
        logger.info("Something went wrong!!!. This is the error:")
        exc_type, exc_value, exc_traceback=sys.exc_info()
        logger.error("%s"%(traceback.format_exc()))
    finally:
        if ready:
            logger.info("Finished initialising at %s"%datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
        else:
            logger.info("Failed to intialise. Look at logs.")
            exit(1)
