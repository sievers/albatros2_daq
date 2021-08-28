import casperfpga
import casperfpga.snapadc
import sys
import struct
import time
import math
import numpy
import logging

logger=logging.getLogger(__name__)

def str2ip(ip_str):
    octets=map(int, ip_str.split("."))
    ip=(octets[0]<<24)+(octets[1]<<16)+(octets[2]<<8)+(octets[3])
    return ip

class AlbatrosDigitizer:
    def __init__(self, snap_ip, snap_port):
        self.fpga=casperfpga.CasperFpga(host=snap_ip, port=snap_port, transport=casperfpga.KatcpTransport)
        if self.fpga.is_running():
            logger.info("Fpga is already programmed")
	    self.fpga.get_system_information()
        else:
            logger.info("Fpga not programmed")

    def initialise_fpga(self, fpg_file):
        logger.info("Programming FPGA")
        if self.fpga.upload_to_ram_and_program(fpg_file):
            return True
        else:
            return False

    def initialise_adcs(self, ref_clock, adc_digital_gain, powerdown):
        snap_adc=casperfpga.snapadc.SNAPADC(self.fpga, ref=ref_clock, resolution=8, cs=0xff)
        logger.info("Setting up ADC's")
        if snap_adc.init(samplingRate=250, numChannel=4)==0:
            for j in range(3):
                snap_adc.selectADC(j)
                snap_adc.adc.selectInput([1,2,3,4])
            logger.info("FPGA clock: %.2f"%(self.fpga.estimate_fpga_clock()))
            logger.info("Setting ADC digital gain")
            snap_adc.adc.cGain([adc_digital_gain, adc_digital_gain, adc_digital_gain, adc_digital_gain])
            if powerdown:
                logger.info("Powering down ADC's 2 and 3")
                snap_adc_pd=casperfpga.snapadc.SNAPADC(self.fpga, ref=ref_clock, resolution=8, cs=0x06)
                snap_adc_pd.adc.powerDown()
            return True
        else:
            return None

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
    
    def initialise_pfb(self, fft_shift):
        self.fpga.registers.fft_shift.write_int(fft_shift)
        return None

    def initialise_xcorr(self, acc_len):
        self.fpga.registers.xcorr_acc_len.write_int(acc_len)
        return None

    def initialise_output_control(self, bits, chans, coeffs):
        self.fpga.registers.output_control_select.write_int(int(numpy.log2(bits)))
        self._set_channel_order(chans, bits)
        self._set_channel_coeffs(coeffs, bits)
        return None

    def _set_channel_order(self, channels, bits):
        channel_map=""
        if (bits==1):
            channel_map="output_control_one_bit_reorder_map1"
        elif (bits==2):
            channel_map="output_control_two_bit_reorder_map1"
        else:
            channel_map="output_control_four_bit_reorder_map1"
        self.fpga.write(channel_map, channels.astype(">H").tostring(), offset=0)
        return True

    def _set_channel_coeffs(self, coeffs, bits):
        if (bits==1):
            logger.info("In one bit mode. No need to write coeffs")
            return None
        coeffs_bram_name=""
        if (bits==2):
            coeffs_bram_name="two_bit_quant_coeffs"
            logger.info("Setting two bit coeffs")
        if (bits==4):
            coeffs_bram_name="four_bit_quant_coeffs"
            logger.info("Setting four bit coeffs")
        self.fpga.write(coeffs_bram_name, coeffs.tostring(), offset=0)
        return None
    
    def initialise_packetiser(self, spec_per_packet, bytes_per_spectrum):
        self.fpga.registers.packetiser_spectra_per_packet.write_int(spec_per_packet)
        self.fpga.registers.packetiser_bytes_per_spectrum.write_int(bytes_per_spectrum)
        return None
    
    def initialise_gbe(self, dest_ip, dest_port, dest_mac):
        logger.info("Setting destination IP address and port")
        self.fpga.registers.destination_ip.write_int(str2ip(dest_ip))
        self.fpga.registers.destination_port.write_int(dest_port)
        logger.info("Setting destination mac address")
        self.fpga.gbes.one_gbe.set_arp_table([dest_mac]*256)
        return None

    def gbe_enable(self):
        self.fpga.registers.control.write(gbe_en=1)

    def gbe_disable(self):
        self.fpga.registers.control.write(gbe_en=0)
    
    def sync(self):
        logger.info("Resetting counters and syncing")
        self.fpga.registers.control.write(cnt_rst=0)
        self.fpga.registers.control.write(sw_sync=0)
        self.fpga.registers.control.write(sw_sync=1)
        self.fpga.registers.control.write(sw_sync=0)
        self.fpga.registers.control.write(cnt_rst=1)
        self.fpga.registers.control.write(cnt_rst=0)
        return None

    def check_pfb_overflow(self):
        return self.fpga.registers.pfb_fft_of.read_uint()

    def check_gbe_overflow(self):
        return self.fpga.registers.tx_of_cnt.read_uint()
                              
    def read_register(self, reg):
        return self.fpga.registers[reg].read_uint()

    def read_bram(self, bram):
        return self.fpga.sbrams[bram].read_raw()

    def get_fpga_temperature(self):
        TEMP_OFFSET = 0x0
        x = self.fpga.read_int("xadc", TEMP_OFFSET)
        return (x >> 4)*503.975/4096.00-273.15
