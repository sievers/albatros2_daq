import argparse
import logging
import datetime
import casperfpga
import casperfpga.snapadc
import struct
import time
import numpy

def initialize(args, logger):
	logger.info("Initializing SNAP Board")
	ip_port=args.ip.split(":")
	snap=casperfpga.CasperFpga(host=ip_port[0], port=ip_port[1], transport=casperfpga.KatcpTransport)
	if snap.is_connected():
		logger.info("Connected at %s:%s"%(ip_port[0], ip_port[1]))
	else:
		logger.critical("Failed to connect")
		exit(0)
        if snap.upload_to_ram_and_program(args.fpg):
		logger.info("Firmware programmed successfully")
	else:
		logger.critical("Failed to program")	
		exit(0)
        ref=None
        if args.clock=="internal":
            ref=10
	snap_adc=casperfpga.snapadc.SNAPADC(snap, ref=ref)
	adc_done=False
	for i in range(3):
		if snap_adc.init(samplingRate=250, numChannel=4, resolution=8)==0:
			for j in range(3):
				snap_adc.selectADC(j)
				snap_adc.adc.selectInput([1, 2, 3, 4])
			adc_done=True
			break
        if adc_done:
		logger.info("ADC successfully initailized")
	else:
		logger.critical("Failed to initialize ADC")
		exit(0)
	logger.info("FPGA clock: %f"%snap.estimate_fpga_clock())
	logger.info("Setting FFT shift")
	snap.registers.pfb0_fft_shift.write_int(args.fftshift)			
	snap.registers.pfb1_fft_shift.write_int(args.fftshift)
	logger.info("Setting quantizer")
	bit_sel=0
	if args.bits==1:
		bit_sel=0
	elif args.bits==2:
		bit_sels=1
	else:
		bit_sel==2
	snap.registers.output_mux_sel.write_int(bit_sel)
	logger.info("Setting accumulation length")
	snap.registers.acc_len.write_int(args.acclen)
	logger.info("Resetting Packetizer")
	snap.registers.output_rst.write_int(1)
	snap.registers.gbe_output_en.write_int(0)
	logger.info("Setting bytes per spectra")
	snap.registers.output_ctrl_bytes_per_spec.write_int(args.bytes_per_spectrum)
	logger.info("Setting spectra per packet")	
	snap.registers.output_ctrl_spec_per_pkt.write_int(args.spectra_per_packet)
	logger.info("Setting destination IP address and Port")
	dest_ip_port=args.dest_ip.split(":")
	snap.registers.gbe_output_dest_ip.write_int(str2ip(dest_ip_port[0]))
	snap.registers.gbe_output_dest_port.write_int(int(dest_ip_port[1]))
	logger.info("Setting destination MAC address")
	mac=struct.pack(">Q", int(args.dest_mac, 16))
	for i in range(256):
		snap.write("gbe_output_one_gbe", mac, offset=0x3000+8*i)
	logger.info("Resetting counters and sync logic")
	snap.registers.cnt_rst.write_int(0)
	snap.registers.sw_sync.write_int(0)
	snap.registers.sw_sync.write_int(1)
	snap.registers.sw_sync.write_int(0)
	snap.registers.cnt_rst.write_int(1)
	snap.registers.cnt_rst.write_int(0)
	time.sleep(2.5)
	pfb0_fft_of=0
	pfb1_fft_of=0
	for i in range(3):
		pfb0_fft_of=pfb0_fft_of or snap.registers.pfb0_fft_of.read_int()
		pfb1_fft_of=pfb0_fft_of or snap.registers.pfb1_fft_of.read_int()
	if (pfb0_fft_of or pfb1_fft_of):
		logger.warning("FFT overflowing")
	else:
		logger.info("No FFT overflows")
	logger.info("Enabling 1 GbE output")
	snap.registers.gbe_output_en.write_int(1)
	snap.registers.output_rst.write_int(0)
	gbe_overflow=0
	for i in range(3):
	    gbe_overflow=gbe_overflow or snap.registers.gbe_output_tx_of_cnt.read_int()
	time.sleep(2.5)
	if (gbe_overflow):
		logger.warning("GbE transmit overflowing")
	else:
		logger.info("No Gbe overflows detected")
	logger.info("Initialization complete")
	return snap
	
def str2ip(ip_str):
	octets=map(int, ip_str.split("."))
	ip=(octets[0]<<24)+(octets[1]<<16)+(octets[2]<<8)+(octets[3])
	return ip

def set_channels(snap, args, logger):
	reorder_map=""
        chan_order=numpy.empty(0, dtype=">H")
        split_channels=args.channels.split(" ")
        channels=numpy.empty(0, dtype=">H")
        for many_channels in split_channels:
                chan_list=many_channels.split(":")
                channels=numpy.append(channels, numpy.arange(int(chan_list[0]), int(chan_list[1]), dtype=">H"))
        print(channels)
        if (args.bits==1):
		reorder_map="reorder_4_to_8_reorder_map1"
                chan_order=channels[::2]  
	        print(chan_order)
        elif (args.bits==2):
		reorder_map="reorder_8_to_8_reorder_map1"
                chan_order=channels
                print(chan_order)
        elif (args.bits==4):
		reorder_map="reorder_16_to_8_reorder_map1"
                chan_order=numpy.ravel(numpy.column_stack((channels, channels)))
                print(chan_order)
        else:
                logger.error("Invalid value for bits")
	snap.write(reorder_map, chan_order.tostring(), offset=0)
	return None

def set_channel_coeff(snap, coeffs, args):
        coeff_map=""
        if (args.bits==4):
                coeff_map="four_bit_coeff"
        snap.write(coeff_map, coeff.tostring())
	return None

if __name__=="__main__":
	parser=argparse.ArgumentParser()
	parser.add_argument("ip", type=str, default="127.0.0.1:7147", help="SNAP board IP address and Port. (Default: %default)")
	parser.add_argument("-f", "--fpg", type=str, help="fpg file to be programmed")
        parser.add_argument("-c", "--clock", type=str, help="Select clock source. 'external': provide clock to SMA 4, 'internal': provide 10MHz to SMA 3")
	parser.add_argument("-F", "--fftshift", type=int, default=0xFFFF, help="Sets the FFT shift of pfb0 and pfb1")
	parser.add_argument("-b", "--bits", type=int, default=1, help="Sets the number of bits per channel")
	parser.add_argument("-a", "--acclen", type=int, default=39000, help="Sets the number of spectra to accumulate")
	parser.add_argument("-B", "--bytes_per_spectrum", type=int, default=246)
	parser.add_argument("-s", "--spectra_per_packet", type=int, default=5, help="Sets the number of spectra per packet")
	parser.add_argument("-d", "--dest_ip", type=str, default="192.168.1.190:4321", help="Destination IP address and port")
	parser.add_argument("-m", "--dest_mac", type=str, help="Sets destination MAC address")
	parser.add_argument("-C", "--channels", type=str, help="Sets the channels to output")
        parser.add_argument("-l", "--logs", type=str, default="./logs", help="Directory to save log files. (Default: %default)")
	args=parser.parse_args()
	
	logger=logging.getLogger("")
	logger.setLevel(logging.INFO)
	file_logger=logging.FileHandler(args.logs+"/albatros_"+datetime.datetime.now().strftime("%d%m%Y_%H%M%S")+".log")
	file_format=logging.Formatter("%(asctime)s %(name)-12s %(message)s", "%d-%m-%Y %H:%M:%S")
	file_logger.setFormatter(file_format)
	file_logger.setLevel(logging.DEBUG)
	logger.addHandler(file_logger)
	logger.info("###############################################")
	logger.info("(1) SNAP Board IP address/Port: %s"%(args.ip))
	logger.info("(2) FPG file: %s"%(args.fpg))
        logger.info("(3) Clock source: %s"%(args.clock))
        logger.info("(4) FFT shift: %d"%(args.fftshift))
	logger.info("(5) Bits: %d"%(args.bits))
	logger.info("(6) Accumulation length: %d"%(args.acclen))
	logger.info("(7) Bytes per spectrum: %d"%(args.bytes_per_spectrum))
	logger.info("(8) Spectra per packet: %d"%(args.spectra_per_packet))
	logger.info("(9) Destination IP address/port: %s"%(args.dest_ip))
	logger.info("(10) Destination MAC Address: %s"%(args.dest_mac))
        logger.info("(11) Channels: %s"%(args.channels))
        logger.info("(12) Log directory: %s"%(args.logs))
	logger.info("###############################################")
	
	try:
		snap=initialize(args, logger)
                set_channels(snap, args, logger)
        finally:
		logger.info("Terminating DAQ at %s"%datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
	
