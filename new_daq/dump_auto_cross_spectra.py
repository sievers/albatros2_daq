#!/usr/bin/python

import casperfpga
import argparse
import scio
import time
import numpy
import struct
import datetime
import os
import trimble_utils
try:
        import trimble_utils
        imported_trimble=True
except:
        imported_trimble=False

def read_pols(snap, pols, struct_format):
	pols_dict = {}
	for pol in pols:
		pols_dict[pol] = numpy.array(struct.unpack(struct_format, snap.read(pol, 2048*8)), dtype="int64")
	return pols_dict

def read_registers(snap, regs):
	reg_dict = {}
	for r in regs:
		reg_dict[r] = numpy.array(snap.registers[r].read_uint())
	return reg_dict

def get_fpga_temperature(snap):
	TEMP_OFFSET = 0x0
	x = snap.read_int("xadc", TEMP_OFFSET)
	return (x >> 4)*503.975/4096.00-273.15

def get_rpi_temperature():
	x = open("/sys/class/thermal/thermal_zone0/temp", "r")
	temp = numpy.float32(x.readline())/1000
        print(temp)
        x.close()
	return temp

if __name__=="__main__":
	parser=argparse.ArgumentParser()
	parser.add_argument("-ip", type=str, default="127.0.0.1:7147", help="SNAP board ip address and port. (default=: %default)")
	parser.add_argument("-p", "--pol", type=str, default="pol00 pol11 pol01r pol01i", help="Pols to dump (pol00, pol11, pol01)")
	parser.add_argument("-o", "--outdir", type=str, default="/media/pi/ALBATROS_2TB_1/data_auto_cross_1", help="directory to store pols")
	parser.add_argument("-t", "--time_frag_length", type=int, default=5, help="Time fragment length for directory")
	parser.add_argument("-T", "--tfile", type=int, default=5, help="time in minutes for file")
        parser.add_argument("-d","--dir", type=str, default='albatros_baseband',help="Set output directory to this.")
        parser.add_argument("-D","--drive", type=str, default='',help="Force output drive to this (otherwise use drive with most empty space)")
        args=parser.parse_args()

	use_trimble = True

        try:
		ip_port=args.ip.split(":")
		snap=casperfpga.CasperFpga(host=ip_port[0], port=ip_port[1], transport=casperfpga.KatcpTransport)
		if snap.is_running():
			print("SNAP board is up and programmmed")
			snap.get_system_information()
			print(snap.listdev())
		else:
			print("SNAP board not programmed")
		pols=args.pol.split(" ")
		print(pols)
		regs=["sync_cnt", "pfb_fft_of", "acc_cnt", "sys_clkcounter"]
		if use_trimble:
			if trimble_utils.get_report_trimble() is None:
				print("Trying to use GPS clock but Trimble not detected.")
			else:
				print("Trimble GPS clock successfully detected.")
		else:
			print("Not using Trimble. Timestamps will come from system clock.")
		while True:
                        start_time = time.time()
			if start_time>1e5:
				time_frag = str(start_time)[:args.time_frag_length]
			else:
				print("Start time in acquire data seems to be near zero")
			outsubdir = "%s/%s/%s"%(args.outdir, time_frag, str(numpy.int64(start_time)))
			os.makedirs(outsubdir)
			print("Writing current data to %s"%outsubdir)
			start_raw_files = {}
			end_raw_files = {}
			scio_files = {}
			if use_trimble:
				file_gps_timestamp1 = open("%s/time_gps_start.raw"%outsubdir, "w")
				file_gps_timestamp2 = open("%s/time_gps_stop.raw"%outsubdir, "w")
			file_sys_timestamp1 = open("%s/time_sys_start.raw"%outsubdir, "w")
			file_sys_timestamp2 = open("%s/time_sys_stop.raw"%outsubdir, "w")
			file_fpga_temp = open("%s/fpga_temp.raw"%outsubdir, "w")
			file_pi_temp = open("%s/pi_temp.raw"%outsubdir, "w")
			for reg in regs:
				start_raw_files[reg] = open("%s/%s1.raw"%(outsubdir, reg), "w")
			        end_raw_files[reg] = open("%s/%s2.raw"%(outsubdir, reg), "w")
			for pol in pols:
				scio_files[pol] = scio.scio("%s/%s.scio"%(outsubdir, pol))
			acc_cnt = 0 
			while time.time()-start_time < args.tfile*60:
				new_acc_cnt = read_registers(snap, ["acc_cnt"])
				if new_acc_cnt > acc_cnt:
					print(new_acc_cnt)
					print(time.ctime())
					acc_cnt = new_acc_cnt
					if use_trimble:
						start_gps_timestamp = trimble_utils.get_gps_timestamp_trimble(maxtime=2, maxiter=1)
					start_sys_timestamp = time.time()
					start_reg_data = read_registers(snap, regs)
					pol_data = read_pols(snap, pols, ">2048q")
					end_reg_data = read_registers(snap, regs)
					end_sys_timestamp = time.time()
					if use_trimble:
						end_gps_timestamp = trimble_utils.get_gps_timestamp_trimble(maxtime=2, maxiter=1)
					read_time = end_sys_timestamp-start_sys_timestamp
					print("Read took: "+str(read_time))
					if use_trimble:
						if start_gps_timestamp is None:
							start_gps_timestamp = 0
						if end_gps_timestamp is None:
							end_gps_timestamp = 0
					if start_reg_data["acc_cnt"] != end_reg_data["acc_cnt"]:
						print("Accumulation length changed during read")
					for reg in regs:
						numpy.array(start_reg_data[reg]).tofile(start_raw_files[reg])
						start_raw_files[reg].flush()
						numpy.array(end_reg_data[reg]).tofile(end_raw_files[reg])
						end_raw_files[reg].flush()
					for pol in pols:
						scio_files[pol].append(pol_data[pol])
					numpy.array(start_sys_timestamp).tofile(file_sys_timestamp1)
					numpy.array(get_fpga_temperature(snap)).tofile(file_fpga_temp)
					numpy.array(get_rpi_temperature()).tofile(file_pi_temp)
					numpy.array(end_sys_timestamp).tofile(file_sys_timestamp2)
					if use_trimble:
						numpy.array(start_gps_timestamp, dtype=numpy.utin32).tofile(file_gps_timestamp1)
						numpy.array(end_gps_timestamp, dtype=numpy.uint32).tofile(file_gps_timestamp2)
						file_gps_timestamp1.flush()
						file_gps_timestamp2.flush()
					file_sys_timestamp1.flush()
					file_fpga_temp.flush()
					file_pi_temp.flush()
					file_sys_timestamp2.flush()
			for pol in pols:
				scio_files[pol].close()
			for reg in regs:
				start_raw_files[reg].close()
				end_raw_files[reg].close()
			file_sys_timestamp1.close()
			file_fpga_temp.close()
			file_pi_temp.close()
			file_sys_timestamp2.close()
			if use_trimble:
				file_gps_timestamp1.close()
				file_gps_timestamp2.close()
	finally:
		print("Terminating DAQ at %s"%datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
