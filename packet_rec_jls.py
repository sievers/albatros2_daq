import socket
import struct
import numpy 
import time
import scio
import argparse
import albatros_daq_utils
import os

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("-Q","--freqs",type=str,default="0 20",help="Frequency range to dump baseband.")
    parser.add_argument("-b", "--bits", type=int, default=0, help="Sets the output number of bits (0=1bit, 1=2bit, 3=4bit)")
    parser.add_argument("-r","--rate",type=int,default=250,help="FPGA Sampling rate.")
    parser.add_argument("-n","--nchan",type=int,default=2048,help="FPGA number of channels.  This cannot be changed at script level.")
    parser.add_argument("-g","--gbytes",type=float,default=2.0,help="Target file size in GB")
    parser.add_argument("-S","--safety",type=float,default=0.95,help="Treat available size as down by this factor to avoid filling drives.")
    args=parser.parse_args()
    
    
    freq=numpy.fromstring(args.freqs,sep=' ')
    print 'freq is ',freq
    chan=albatros_daq_utils.get_channels_from_freq(freq,args.bits,args.rate,args.nchan)
    nspec=albatros_daq_utils.get_nspec(chan)
    header_len=4 #we also read spec# from the fpga
    nbyte=len(chan)*nspec+header_len


    
    s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("192.168.2.200", 4321))

    outpart=albatros_daq_utils.find_emptiest_drive()
    st=os.statvfs(outpart)
    free_bytes=st.f_bavail*st.f_frsize
    nfile_targ=int(args.safety*free_bytes/(1.0e9*args.gbytes))
    print "I think I can write ",nfile_targ," files in available space."
    outname=albatros_daq_utils.find_emptiest_drive()+'/jls_noise_test.raw'
    print 'writing data to ',outname
    #f=open(outname,'w')
    #f=open('/media/pi/ALBATROS_5TB_1/snap1_noise_test_short.raw','w')
    #nbyte=5*264+4 #should this be 1230?
    
    data=bytearray(nbyte)
    i=0
    t0=time.time()
    time_per_spec=(args.nchan)/1e6/args.rate
    time_per_read=time_per_spec*nspec

    reads_per_file=int(1.0e9*args.gbytes/nbyte)
    print "I think I should write ",reads_per_file," packets per file."

    
    reads_per_print=10000
    time_per_print=time_per_read*reads_per_print
    for fnum in range(nfile_targ):
        ct=time.time()
        ct_str=repr(int(ct))    
        ct_root=ct_str[:5]
        mydir=outpart+'/'+ct_root
        print mydir
        if not(os.path.isdir(mydir)):
            os.mkdir(mydir)
        fname=mydir+'/'+ct_str+'.raw'
        print 'writing to ',fname
        f=open(fname,'w')
        for spec in range(reads_per_file):
        
        
            s.recvfrom_into(data,nbyte)
            f.write(data)
            i=i+1
            if i==reads_per_print:
                t1=time.time()
                print 'data size is',len(data),type(data),t1-t0,time_per_print
                i=0
                t0=t1
        f.close()

