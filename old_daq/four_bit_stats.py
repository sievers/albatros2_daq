import casperfpga
import argparse
from matplotlib import pyplot
import numpy
import time

if __name__=="__main__":
    snap=casperfpga.CasperFpga("127.0.0.1", port=7147)
    snap.get_system_information()
    print(snap.snapshots)
    four_bit=numpy.array(snap.snapshots.rms_4b.read()["data"]["data"])
    print(four_bit) 
    for i in range(7):
        time.sleep(1)
        four_bit+=numpy.array(snap.snapshots.rms_4b.read()["data"]["data"])
    pyplot.plot(numpy.linspace(0,125,2048), numpy.array(four_bit)/7)
    pyplot.show()
