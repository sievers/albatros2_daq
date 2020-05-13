import casperfpga
import numpy

fpga=casperfpga.CasperFpga("127.0.0.1", 7147)
fpga.get_system_information()
adc0_snap=fpga.snapshots.adc0_snapshot.read(man_valid=True, man_trig=True)
adc3_snap=fpga.snapshots.adc3_snapshot.read(man_valid=True, man_trig=True)
numpy.save("adc_snapshots", [adc0_snap["data"]["data"], adc3_snap["data"]["data"]])
