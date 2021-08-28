import casperfpga
import casperfpga.snapadc
import argparse
import logging
import struct
import datetime
import time
import numpy
import socket
import scio
import albatros_daq_utils
import sys

def init_snap(args, logger):
	logger.info("Initialising SNAP Board")
	ip_port=args.ip.split(":")
	snap=casperfpga.CasperFpga(host=ip_port[0], port=ip_port[1], transport=casperfpga.KatcpTransport)
	if snap.is_connected():
		logger.info("Connected to SNAP Board at %s:%s"%(ip_port[0], ip_port[1]))
	else:
		logger.critical("Failed to connect")
		exit(0)
	if snap.upload_to_ram_and_program(args.firmware):
		logger.info("SNAP Board programmed sucessfully")
	else:
		logger.critical("Failed to program")
	snap_adc=casperfpga.snapadc.SNAPADC(snap, ref=10)
	for i in range(3):
                print 'setting snap frequency to ',args.rate
#		if snap_adc.init(samplingRate=250, numChannel=4, resolution=8)==0:
                if snap_adc.init(samplingRate=args.rate, numChannel=4, resolution=8)==0:
                        
			for j in range(3):
				snap_adc.selectADC(j)
				snap_adc.adc.selectInput([1,2,3,4])
			logger.info("ADC's initised after %d atempts/s"%(i+1))
			break
		elif i<(2):
			logger.error("ADC initisation failed. Retrying!!!")
		else:
			logger.critical("ADC initialisation failed. Exiting!!!")
                        exit(0)
	logger.info("FPGA clock: %f"%snap.estimate_fpga_clock())
	logger.info("Setting FFT shift")
	snap.registers.pfb_fft_shift.write_int(args.fftshift)
	#snap.registers.pfb1_fft_shift.write_int(args.fftshift)
	logger.info("Setting accumulation length")
	snap.registers.acc_len.write_int(args.acclen)
	logger.info("Setting ouput bits")
	snap.registers.output_mux_sel.write_int(args.bits)
	logger.info("Reseting packetiser")
	snap.registers.output_rst.write_int(1)
	snap.registers.gbe_output_en.write_int(0)
	logger.info("Setting spectra per packet")
	snap.registers.output_ctrl_spec_per_pkt.write_int(args.spec_per_packet)
	logger.info("Setting bytes per spectra")
	snap.registers.output_ctrl_bytes_per_spec.write_int(args.bytes_per_spectra)
	logger.info("Setting destination IP address and port")
	dest_ip_port=args.dest_ip.split(":")
	snap.registers.gbe_output_dest_ip.write_int(str2ip(dest_ip_port[0]))
	snap.registers.gbe_output_dest_port.write_int(int(dest_ip_port[1]))
	logger.info("Setting destination mac address")
	mac=int(args.dest_mac, 16)
	for i in range(256):
		snap.write("gbe_output_one_gbe", struct.pack(">Q", mac), offset=0x3000+8*i)
	logger.info("Resetting counters and syncing")	
	snap.registers.cnt_rst.write_int(0)
	snap.registers.sw_sync.write_int(0)
	snap.registers.sw_sync.write_int(1)
	snap.registers.sw_sync.write_int(0)
	snap.registers.cnt_rst.write_int(1)
	snap.registers.cnt_rst.write_int(0)
	time.sleep(2.5)
	pfb_fft_of=0
	#pfb1_fft_of=0
	for i in range(3):
		pfb_fft_of = pfb_fft_of or snap.registers.pfb_fft_of.read_uint()
		#pfb1_fft_of = pfb1_fft_of or snap.registers.pfb1_fft_of.read_int()
        if (pfb_fft_of):# or pfb1_fft_of):
            	logger.warning("FFT overflowing")
	else:
		logger.info("No FFT overflows detected")
        logger.info("Enabling 1 GbE output")
	snap.registers.gbe_output_en.write_int(1)
	snap.registers.output_rst.write_int(0)
	gbe_overflow=0
	for i in range(3):
		gbe_overflow=gbe_overflow or snap.registers.gbe_output_tx_of_cnt.read_uint()
		time.sleep(2.5)
	if (gbe_overflow):
		logger.warning("GbE transmit overflowing")
	else:
		logger.info("No Gbe overflows detected")
	logger.info("Initialisation complete")
	return snap

def str2ip(ip_str):
	octets=map(int, ip_str.split("."))
	ip=(octets[0]<<24)+(octets[1]<<16)+(octets[2]<<8)+(octets[3])
	return ip

def tvg_enable(snap):
        snap.registers.tvg0_en.write_int(1)

def set_tvg(snap, tvg_values):
	tvg_string=tvg_values.astype(">Q").tostring()
	snap.write("tvg0_tvg", tvg_string, offset=0)
	return None

def select_channels(args, snap, channels):
	channel_map=""
	if (args.bits==0):
		channel_map="reorder_4_to_8_reorder_map1"
	elif (args.bits==1):
		channel_map="reorder_8_to_8_reorder1_map1"
	else:
		channel_map="reorder_16_to_8_reorder2_map1"
	snap.write(channel_map, channels.astype(">H").tostring(), offset=0)
	return None

def set_channel_coeffs(args, snap, coeffs):
	coeffs_map=""
	if (args.bits==1):
		coeffs_map="two_bit_coeffs"
	else:
		if (arg.bits==2):
			coeffs_map="four_bit_coeffs"
	snap.write(coeffs_map, coeffs.astype(">H").tostring(), offset=0)
	return None 

def unpack_packets(socket, struct_fmt):
        data, addr=socket.recvfrom(2048)
        unpacked_data=numpy.array(struct.unpack(struct_fmt, data), dtype="uint32")
        return unpacked_data, addr

def read_pol(snap, pol):
	bram_data=snap.sbrams[pol].read_raw()
	return numpy.array(numpy.tostring(bram_data, dtype=">Q"), dtype="uint64")

def read_register(snap, reg):
	return snap.registers[reg].read_int()

def get_fpga_temperature(snap):
	TEMP_OFFSET=0x0
	x=snap.read_int("xadc", TEMP_OFFSET)
	return (X>>4)*503.975/4096-273.15

def get_rpi_temperature():
	x=open("sys/class/thermal/thermal_zone0/temp", "r")
	temp=numpy.int2(x.readline())/1000
	x.close()
	return temp

if __name__=="__main__":
	parser=argparse.ArgumentParser()
	parser.add_argument("ip", type=str, default="127.0.0.1:7147", help="SNAP board ip address and port. (default: %default)") 
	parser.add_argument("-f", "--firmware", type=str, help="fpg file to be programmed")
	parser.add_argument("-F", "--fftshift", type=int, help="Sets the FFT shift of pfb0 and pfb1")
	parser.add_argument("-a", "--acclen", type=int, help="Sets the accumulation length")
        parser.add_argument("-b", "--bits", type=int, default=0, help="Sets the output number of bits (0=1bit, 1=2bit, 3=4bit)")
	parser.add_argument("-s", "--spec_per_packet", type=int, default=8, help="Sets the spectra per packet")
	parser.add_argument("-B", "--bytes_per_spectra", type=int, default=128, help="Sets the bytes per spectra")
	parser.add_argument("-d", "--dest_ip", type=str, help="Sets the destination ip address and port")
	parser.add_argument("-m", "--dest_mac", type=str, help="Sets destination mac address. Must be in hexadecimal.")
	parser.add_argument("-c", "--channels", type=str, help="Sets the channels to be output. Can be either a group of channels or individual or both.")
        parser.add_argument("-Q","--freqs",type=str,default="0 20",help="Frequency range to dump baseband.")
        
        parser.add_argument("-r","--rate",type=int,default=250,help="FPGA Sampling rate.")
        parser.add_argument("-n","--nchan",type=int,default=2048,help="FPGA number of channels.  This cannot be changed at script level.")
	parser.add_argument("-l", "--logdir", type=str, default="./logs/", help="Sets directory for saving log files")
	args=parser.parse_args()

 	logger=logging.getLogger("albatros2_daq")
	logger.setLevel(logging.DEBUG)
	file_logger=logging.FileHandler(args.logdir+"/albatros_"+datetime.datetime.now().strftime("%d%m%Y_%H%M%S")+".log")
	file_format=logging.Formatter("%(asctime)s %(name)-12s %(message)s", "%d-%m-%Y %H:%M:%S")
	file_logger.setFormatter(file_format)
	file_logger.setLevel(logging.DEBUG)
	logger.addHandler(file_logger)
	logger.info("##############################################")
	logger.info("(1) SNAP Board ip address/port: %s"%(args.ip))
	logger.info("(2) FPG file: %s"%args.firmware)
	logger.info("(3) FFT shift: %s"%args.fftshift)
	logger.info("(4) Accumulation length: %s"%args.acclen)
	logger.info("(5) Output bits: %s"%args.bits)
        logger.info("(6) Frequency range: %s"%args.freqs)
	#logger.info("(6) Spectra per packet: %s"%args.spec_per_packet)
	#logger.info("(7) Bytes per spectra: %s"%args.bytes_per_spectra)
	logger.info("(8) Destination ip address/port: %s"%(args.dest_ip))
	logger.info("(9) Destination MAC address: %s"%(args.dest_mac))
	logger.info("(10) Channels: %s"%(args.channels))
	logger.info("(11) Log directory: %s"%(args.logdir))
	logger.info("##############################################")
        retval=1
	try:

		#channels=[]
		#for i in args.channels.split(" "):
		#	chan=i.split(":")
		#	if chan>1:
		#		channels.extend(range(int(chan[0]),int(chan[1])))	
		#	else:
		#		channels.extend(chan)
        	#channels=numpy.asarray(channels)[::2]
                #chan=numpy.column_stack((numpy.arange(428, 560), numpy.arange(82, 214)))
                #chan=numpy.ravel(chan)
                freq=numpy.fromstring(args.freqs,sep=' ')
                print 'freq is ',freq
                chan=albatros_daq_utils.get_channels_from_freq(freq,args.bits,args.rate/2.0,args.nchan)
                print(chan)
                nspec=albatros_daq_utils.get_nspec(chan)
                args.spec_per_packet=nspec
                header_len=4 #we also read spec# from the fpga
                nbytes=len(chan)*nspec+header_len
                args.bytes_per_spectra=len(chan)
	        logger.info("(-1) Spectra per packet: %s"%args.spec_per_packet)
	        logger.info("(-2) Bytes per spectra: %s"%args.bytes_per_spectra)
                
		snap=init_snap(args, logger)
                select_channels(args, snap, chan)
                coeff=(2**4*numpy.append(numpy.zeros(1, dtype=">I"), numpy.ones(2047, dtype=">I"))).tostring()
                snap.write("four_bit_coeffs", coeff, offset=0)
                #file_auto=scio.scio("/media/pi/ssd1tb/autospectra3.scio")
                #while True:
                #        file_auto.append(read_pol(snap, "pol00"))
                #chan=numpy.arange(1531, 1549)
                #select_channels(args, snap, chan)
                retval=0
        finally:
	        logger.info("Terminating DAQ at %s"%datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
                sys.exit(retval)
