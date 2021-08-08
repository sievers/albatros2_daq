import casperfpga
import casperfpga.snapadc
import sys
import struct
import time
import math
import numpy

def str2ip(ip_str):
        octets=map(int, ip_str.split("."))
        ip=(octets[0]<<24)+(octets[1]<<16)+(octets[2]<<8)+(octets[3])
        return ip

def float2fixed(value, binary_point):
        return value*2**binary_point

def fixed2float(value, binary_point):
        return value/2.**binary_point

class AlbatrosDigitizer:
        def __init__(self, snap_ip, snap_port, logger):
                self.logger=logger
        	self.fpga=casperfpga.CasperFpga(host=snap_ip, port=snap_port, transport=casperfpga.KatcpTransport)
        	self.logger.info("Connected to SNAP Board at %s:%s"%(snap_ip, snap_port))
                if self.fpga.is_running():
        	        self.logger.info("Fpga is already programmed")
		        self.fpga.get_system_information()
        	else:
        	        self.logger.info("Fpga not programmed")

        def initialise(self, fpg_file, ref_clock, fftshift, acclen, bits, spec_per_packet, bytes_per_spectrum, dest_ip, dest_port, dest_mac, adc_digital_gain, prog_tries=3, adc_tries=3):
                self.logger.info("Initialising SNAP Board")
		for i in range(prog_tries):
        	        if self.fpga.upload_to_ram_and_program(fpg_file):
                                self.logger.info("Fpga programmed sucessfully after %d attempt/s"%(i+1))
			        break
		        elif i<prog_tries-1:
			        self.logger.error("Failed to program. Retrying!!!")
        	        else:
        	                self.logger.critical("Failed to program after "+str(prog_tries)+" tries.")
			        exit(1)
		snap_adc=casperfpga.snapadc.SNAPADC(self.fpga, ref=ref_clock)
		for i in range(adc_tries):
        	    	if snap_adc.init(samplingRate=250, numChannel=4, resolution=8)==0:
        	    	        for j in range(3):
		    	                snap_adc.selectADC(j)
		    	                snap_adc.adc.selectInput([1,2,3,4])
                                self.logger.info("ADC's initialised after %d attempts out of %d/s"%(i+1,adc_tries))
                                break
                        elif i<adc_tries-1:
                                self.logger.error("ADC initialisation failed. Retrying!!!")
		    	else:
        	    	        self.logger.critical("ADC initialisation failed after "+str(adc_tries)+" tries. Exiting!!!")
        	    	        exit(1)
                self.logger.info("FPGA clock: %f"%self.fpga.estimate_fpga_clock())
		self.logger.info("Setting FFT shift")
		self.fpga.registers.pfb_fft_shift.write_int(fftshift)
		self.logger.info("Setting accumulation length")
		self.fpga.registers.acc_len.write_int(acclen)
		self.logger.info("Setting ouput bits")
		self.fpga.registers.output_mux_sel.write_int(int(math.log(bits,2)))
        	self.logger.info("Reseting packetiser")
		self.fpga.registers.output_rst.write_int(1)
		self.fpga.registers.gbe_output_en.write_int(0)
		self.logger.info("Setting spectra per packet")
		self.fpga.registers.output_ctrl_spec_per_pkt.write_int(spec_per_packet)
		self.logger.info("Setting bytes per spectra")
		self.fpga.registers.output_ctrl_bytes_per_spec.write_int(bytes_per_spectrum)
		self.logger.info("Setting destination IP address and port")
		self.fpga.registers.gbe_output_dest_ip.write_int(str2ip(dest_ip))
		self.fpga.registers.gbe_output_dest_port.write_int(dest_port)
		self.logger.info("Setting destination mac address")
		mac=int(dest_mac, 16)
        	for i in range(256):
        	        self.fpga.write("gbe_output_one_gbe", struct.pack(">Q", mac), offset=0x3000+8*i)
		self.logger.info("Resetting counters and syncing")
		self.fpga.registers.cnt_rst.write_int(0)
		self.fpga.registers.sw_sync.write_int(0)
		self.fpga.registers.sw_sync.write_int(1)
		self.fpga.registers.sw_sync.write_int(0)
		self.fpga.registers.cnt_rst.write_int(1)
		self.fpga.registers.cnt_rst.write_int(0)
		time.sleep(0.5)
		pfb_fft_of=0
		for i in range(3):
		        pfb_fft_of = pfb_fft_of or self.fpga.registers.pfb_fft_of.read_uint()
		if (pfb_fft_of):
        	        self.logger.warning("FFT overflowing")
		else:
        	        self.logger.info("No FFT overflows detected")
        	self.logger.info("Enabling 1 GbE output")
		self.fpga.registers.gbe_output_en.write_int(1)
		self.fpga.registers.output_rst.write_int(0)
        	time.sleep(0.5)
		gbe_overflow=0
		for i in range(3):
        	        gbe_overflow=gbe_overflow or self.fpga.registers.gbe_output_tx_of_cnt.read_uint()
		if (gbe_overflow):
		        logger.warning("GbE transmit overflowing")
		else:
		        self.logger.info("No Gbe overflows detected")
		self.logger.info("Initialisation complete")
		return True

    	def set_channel_order(self, channels, bits):
    	    	channel_map=""
    	    	if (bits==1):
    	    	        channel_map="reorder_4_to_8_reorder_map1"
    	    	elif (bits==2):
    	    	        channel_map="reorder_8_to_8_reorder1_map1"
    	    	else:
                        print("setting 4 bit channels")
    	    	        channel_map="reorder_16_to_8_reorder2_map1"
    	    	self.fpga.write(channel_map, channels.astype(">H").tostring(), offset=0)
    	    	return True

        def set_channel_coeffs(self, coeffs, bits):
                if (bits==1):
                        self.logger.info("In one bit mode. No need to write coeffs")
                        return True
                coeffs_bram_name=""
                if (bits==2):
                        coeffs_bram_name="two_bit_quant_coeffs"
                        self.logger.info("Setting two bit coeffs")
                if (bits==4):
                        coeffs_bram_name="four_bit_quant_coeffs"
                        self.logger.info("Setting four bit coeffs")
                self.fpga.write(coeffs_bram_name, coeffs.tostring(), offset=0)
	        return True 

        def get_adc_stats(self):
                adc_stats={}
                for i in [0, 3]:
                        data=self.fpga.snapshots["snapshot_adc%d"%(i)].read(man_valid=True, man_trig=True)["data"]["data"]
                        data=numpy.asarray(data)
                        data[data>2**7]=data[data>2**7]-2**8
                        mean=numpy.mean(data)
                        rms=numpy.sqrt(numpy.mean(data**2))
                        bits_used=numpy.log2(rms)
                        adc_stats["adc%d"%(i)]={"raw":data, "mean":mean, "rms":rms, "bits_used":bits_used}
                return adc_stats
        
        def read_register(self, reg):
                return self.fpga.registers[reg].read_uint()

        def read_bram(self, bram, nbytes):
                return self.fpga.read(bram, nbytes)

        def read_pols(self, pols, struct_format):
                pols_dict = {}
                for pol in pols:
	                pols_dict[pol] = numpy.array(struct.unpack(struct_format, self.fpga.read(pol, 2048*8)), dtype="int64")
                return pols_dict

        def read_registers(self, regs):
                reg_dict = {}
                for r in regs:
	                reg_dict[r] = numpy.array(self.fpga.registers[r].read_uint())
                return reg_dict
        
        def get_fpga_temperature(self):
        	TEMP_OFFSET = 0x0
		x = self.fpga.read_int("xadc", TEMP_OFFSET)
		return (x >> 4)*503.975/4096.00-273.15
