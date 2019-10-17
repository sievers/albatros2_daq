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
import ds3231

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="Script to initialise SNAP Board")
    parser.add_argument("-c", "--configfile", type=str, default="config.yaml", help=".ini file with parameters to configure firmware")
    args=parser.parse_args()

    parameters=None
    config_file_data=None
    with open(args.configfile) as cf:
        config_file_data=cf.read()
        parameters=yaml.load(config_file_data, yaml.FullLoader)

    log_level=parameters["log_level"]
    log_directory=parameters["log_directory"]
        
    logger=logging.getLogger("config_fpga")
    logger.setLevel(log_level)

    if not os.path.isdir(log_directory):
        os.makedirs(log_dir)

    if trimble_utils.set_clock_trimble():
        logger.info("Trimble GPS clock successfully detected.")
        logger.info("Successfully updated system clock to gps time from trimble.")
    else:
        logger.info("Unable to read time from trimble. Using RPi system clock which is unrealiable")

    file_logger=logging.FileHandler(log_directory+"/config_fpga_"+datetime.datetime.now().strftime("%d%m%Y_%H%M%S")+".log")
    file_format=logging.Formatter("%(asctime)s %(name)-12s %(message)s", "%d-%m-%Y %H:%M:%S")
    file_logger.setFormatter(file_format)
    file_logger.setLevel(log_level)
    logger.addHandler(file_logger)

    snap_board=parameters["snap-board"]
    firmware=parameters["firmware"]
    synthesizer=parameters["synthesizer"]
    adcs=parameters["adcs"]
    pfb=parameters["pfb"]
    test_vector_generator=parameters["test-vector-generator"]
    xcorr=parameters["xcorr"]
    packetiser=parameters["packetiser"]
    baseband=parameters["baseband"]
    ethernet=parameters["ethernet"]

    chans=utils.get_channels_from_str(packetiser["channels"], packetiser["bits"])
    spectra_per_packet=utils.get_nspec(chans, max_nbyte=packetiser["max_bytes_per_packet"])
    bytes_per_spectrum=chans.shape[0]
    coeffs=utils.get_coeffs_from_str(packetiser["channel_coeffs"])
    
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
    logger.info("\tadc_digital_gain: %d"%(adcs["adc_digital_gain"]))
    logger.info("\tadc_2_off: %s"%(adcs["adc_2_off"]))
    logger.info("\tadc_3_off: %s"%(adcs["adc_3_off"]))
    logger.info("PFB:")
    logger.info("\tfft shift: %s"%(hex(pfb["fftshift"])[:-1]))
    logger.info("TEST-VECTOR-GENERATOR:")
    logger.info("\tenable: %s"%(str(test_vector_generator["enable"])))
    logger.info("\tdata: %s"%(test_vector_generator["data"]))
    logger.info("XCORR:")
    logger.info("\taccumulation length: %d"%(xcorr["accumulation_length"]))
    logger.info("\tdiff: %s"%(xcorr["diff"]))
    logger.info("\tcompress: %s"%(xcorr["compress"]))
    logger.info("\tdata directory: %s"%(xcorr["data_directory"]))
    logger.info("PACKETISER:")
    logger.info("\tbits: %d"%(packetiser["bits"]))
    logger.info("\tmax bytes per packet: %d"%(packetiser["max_bytes_per_packet"]))
    logger.info("\tchannels: %s"%(packetiser["channels"]))
    logger.info("\tchannel coeffs: %s"%(packetiser["channel_coeffs"]))
    logger.info("BASEBAND:")
    logger.info("\tdrive safety: %.2f"%(baseband["drive_safety"]))
    logger.info("\tfile size: %.2f"%(baseband["file_size"]))
    logger.info("\tdirectory name: %s"%(baseband["directory_name"]))
    logger.info("ETHERNET:")
    logger.info("\tdestination ip: %s"%(ethernet["destination_ip"]))
    logger.info("\tdestination port: %d"%(ethernet["destination_port"]))
    logger.info("\tdestination mac: %s"%(hex(ethernet["destination_mac"])[:-1]))
    logger.info("CALCULATED PARAMETERS:")
    logger.info("\tspectra per packet: %d"%(spectra_per_packet))
    logger.info("\tbytes per spectrum: %d"%(bytes_per_spectrum))
    logger.info("\tbytes per packet: %d"%(spectra_per_packet*bytes_per_spectrum))
    logger.info("###################### end ######################")

    try:
        albatros_snap=albatrosdigitizer.AlbatrosDigitizer(snap_board["ip"], snap_board["port"], logger=logger)
    #     init_ok=albatros_snap.initialise_fpga(fpg_file, fftshift, acclen, bits, spec_per_packet, bytes_per_spectrum)
    #     if init_ok:
    #         albatros_snap.initialise_adcs(ref_clock, adc_digital_gain)
    #         albatros_snap.initialise_gbe(dest_ip, dest_port, dest_mac)
    #         adc_stats=albatros_snap.get_adc_stats()
    #         logger.info("ADC bits used: (adc0, %.2f) (adc3, %.2f)"%(adc_stats["adc0"]["bits_used"], adc_stats["adc3"]["bits_used"]))
    #         albatros_snap.set_channel_order(chans, bits)
    #         albatros_snap.set_channel_coeffs(coeffs, bits)
    except:
        logger.info("Something went wrong!!!. This is the error:")
        exc_type, exc_value, exc_traceback=sys.exc_info()
        logger.error("%s"%(traceback.format_exc()))
    finally:
    #     if init_ok:
    #         logger.info("Finished initialising at %s"%datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
    #     else:
    #         logger.critical("SNAP board failed to initialise. Exiting with status 1")
    #         exit(1)
        pass
