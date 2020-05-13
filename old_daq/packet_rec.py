import socket
import struct
import numpy 
import time
import scio
s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("192.168.2.200", 4321))

#def process_packets(data):
#        data=numpy.asarray(struct.unpack("<I1230B", data), dtype="uint32")
#        return data

#file_scio=scio.scio("./test_3.scio")
#while True:
#	start=time.time()
#	data=process_packets(s.recvfrom(2048)[0]
#        file_scio.append(numpy.array(data, dtype="uint32"))
#        print(time.time()-start)



###JLS version

f=open('/media/pi/ALBATROS_5TB_1/snap1_noise_test_short.raw','w')
nbyte=5*264+4 #should this be 1230?
data=bytearray(nbyte)
i=0
t0=time.time()
while True:
    s.recvfrom_into(data,nbyte)
    f.write(data)
    i=i+1
    if i==10000:
        t1=time.time()
        print 'data size is',len(data),type(data),t1-t0
        i=0
        t0=t1


