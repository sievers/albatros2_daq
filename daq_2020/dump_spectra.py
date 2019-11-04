#!/usr/bin/python
import argparse
import yaml
import logging
import os
import datetime
import scio
import struct
import albatrosdigitizer
import time
import numpy
import traceback
import utils
import smbus
import ds3231
import csv
import sys
import psutil

def get_rpi_temperature():
    x = open("/sys/class/thermal/thermal_zone0/temp", "r")
    temp = numpy.float32(x.readline())/1000
    x.close()
    return temp

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("-c", "--configfile", type=str, default="config.yaml", help="yaml file with parameters for dump spectra")
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
                        filename=log_directory+"/dump_spectra_"+datetime.datetime.now().strftime("%d%m%Y_%H%M%S")+".log",
                        filemode='w')

    logger=logging.getLogger("dump_spectra")

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
    mount_directory=parameters["mount_directory"]
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
    logger.info("MOUNT-DIRECTORY:")
    logger.info("\tmount directory: %s"%(mount_directory))
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

    try:

        albatros_snap=albatrosdigitizer.AlbatrosDigitizer(snap_board["ip"], snap_board["port"])
        acc_cnt=2 # So we don't save the messy first spectra
        file_size_bytes=spectra["file_size"]*1.0e6

        while True:
            tstart=rtc.time()
            outsubdir="%s/%s/%s"%(spectra["data_directory"], str(tstart)[:5], str(numpy.int64(tstart)))
            os.makedirs(outsubdir)
            logger.info('Writing current data to %s' %(outsubdir))

            f_housekeeping=open(outsubdir+'/housekeeping.csv','w')
            f_housekeeping.write("sys_time1; sys_time2; rtc_time1; rtc_time2; fft_of;"\
                                 "acc_cnt1; acc_cnt2; sync_cnt; pi_temp; fpga_temp\n")
            f_housekeeping_csv=csv.writer(f_housekeeping, delimiter=";")

            f_pol00=scio.scio(outsubdir+"/pol00.scio", diff=spectra["diff"], compress=spectra["compress"])
            f_pol11=scio.scio(outsubdir+"/pol11.scio", diff=spectra["diff"], compress=spectra["compress"])
            f_pol01r=scio.scio(outsubdir+"/pol01r.scio", diff=spectra["diff"], compress=spectra["compress"])
            f_pol01i=scio.scio(outsubdir+"/pol01i.scio", diff=spectra["diff"], compress=spectra["compress"])

            file_bytes=0.0
            while file_bytes<=file_size_bytes:
                acc_cnt_start=albatros_snap.read_register("acc_cnt")
                if acc_cnt_start>acc_cnt:
                    # Time stamp at beginning of read commands.
                    # Reading takes a long time (and there are
                    # sometimes timeouts), so keep track of time
                    # stamps for both start and end of reads.
                    logger.debug("acc_cnt: %d"%(acc_cnt_start))
                    logger.debug("file bytes: %.5f"%(file_bytes))
                    t1_sys=time.time()
                    t1_rtc=rtc.time()
                    fft_of=albatros_snap.read_register("pfb_fft_of")
                    sync_cnt=albatros_snap.read_register("sync_cnt")
                    # Forcing type casting to int64 because numpy tries to be
                    # "smart" about casting to int32 if there are no explicit long
                    # ints.
                    pol00=numpy.frombuffer(albatros_snap.read_bram("xcorr_pol00")[0], dtype=">Q").astype("uint64")
                    pol11=numpy.frombuffer(albatros_snap.read_bram("xcorr_pol11")[0], dtype=">Q").astype("uint64")
                    pol01r=numpy.frombuffer(albatros_snap.read_bram("xcorr_pol01r")[0], dtype=">q").astype("int64")
                    pol01i=numpy.frombuffer(albatros_snap.read_bram("xcorr_pol01i")[0], dtype=">q").astype("int64")
                    acc_cnt_end=albatros_snap.read_register("acc_cnt")
                    pi_temp=get_rpi_temperature()
                    fpga_temp=albatros_snap.get_fpga_temperature() 
                    t2_sys=time.time()
                    t2_rtc=rtc.time()
                    logger.debug("elapsed system time is %.5f"%(t2_sys-t1_sys))
                    if acc_cnt_start != acc_cnt_end:
                        logging.warning('Accumulation changed during data read')
                    f_pol00.append(pol00)
                    f_pol11.append(pol11)
                    f_pol01r.append(pol01r)
                    f_pol01i.append(pol01i)
                    data=[t1_sys, t2_sys, t1_rtc, t2_rtc, fft_of, acc_cnt_start, acc_cnt_end,
                          sync_cnt, pi_temp, fpga_temp]
                    f_housekeeping_csv.writerow(data)
                    f_housekeeping.flush()
                    acc_cnt=acc_cnt_end
                    file_bytes=os.path.getsize(outsubdir+"/pol00.scio")
            f_pol00.close()
            f_pol11.close()
            f_pol01r.close()
            f_pol01i.close()
            f_housekeeping.close()
    except:
        logger.fatal("Something went wrong!!!. This is the error:")
        exc_type, exc_value, exc_traceback=sys.exc_info()
        logger.error("%s"%(traceback.format_exc()))
    finally:
	logger.info("Terminating DAQ at %s"%datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
