import socket
import struct
import numpy 
import time
import scio
import argparse
import albatros_daq_utils
import trimble_utils
import os
import sys

def keep_data_time_of_day(args):
    keep_data=True
    hours=(time.time()%86400)/3600
    tstart=args.start_time
    tstop=args.stop_time
    if (tstart>=0)|(tstop>=0):
        if (tstop>tstart):
            if (hours<tstart)|(hours>tstop):
                keep_data=False
        else:
            if (hours>tstart)&(hours<tstop):
                keep_data=False
    return keep_data

                
    

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("-Q","--freqs",type=str,default="0 20",help="Frequency range to dump baseband.")
    parser.add_argument("-b", "--bits", type=int, default=0, help="Sets the output number of bits (0=1bit, 1=2bit, 3=4bit)")
    parser.add_argument("-r","--rate",type=int,default=250,help="FPGA Sampling rate.")
    parser.add_argument("-n","--nchan",type=int,default=2048,help="FPGA number of channels.  This cannot be changed at script level.")
    parser.add_argument("-g","--gbytes",type=float,default=2.0,help="Target file size in GB")
    parser.add_argument("-c","--setclock",type=int,default=1,help="If true, try to set the system clock from the GPS")
    parser.add_argument("-d","--dir",type=str,default='albatros_baseband',help="Set output directory to this.")
    parser.add_argument("-D","--drive",type=str,default='',help="Force output drive to this (otherwise use drive with most empty space)")
    parser.add_argument("-S","--safety",type=float,default=0.95,help="Treat available size as down by this factor to avoid filling drives.")
    parser.add_argument("-t","--start_time",type=float,default=-1,help="Starting time (in decimal hours) for taking data.");
    parser.add_argument("-T","--stop_time",type=float,default=-1,help="Stopping time (in decimal hours) for taking data.");
    
    args=parser.parse_args()
    

    #print 'keep data is ',keep_data_time_of_day(args)
    #sys.exit(0)
    
    freq=numpy.fromstring(args.freqs,sep=' ')
    print 'freq is ',freq
    chan=albatros_daq_utils.get_channels_from_freq(freq,args.bits,args.rate,args.nchan)
    nspec=albatros_daq_utils.get_nspec(chan)
    header_len=4 #we also read spec# from the fpga
    nbyte=len(chan)*nspec+header_len


    
    s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.bind(("192.168.2.200", 4321))
    except:
        print "Unable to bind to port.  Exiting."
        sys.exit(1)
        
    if len(args.drive)>1:
        outpart=args.drive
    else:
        outpart=albatros_daq_utils.find_emptiest_drive()    
    st=os.statvfs(outpart)
    free_bytes=st.f_bavail*st.f_frsize
    nfile_targ=int(args.safety*free_bytes/(1.0e9*args.gbytes))
    #nfile_targ=3
    print "I think I can write ",nfile_targ," files in available space."
    #outname=albatros_daq_utils.find_emptiest_drive()+'/jls_noise_test.raw'
    #print 'writing data to ',outname
    
    data=bytearray(nbyte)
    i=0
    t0=time.time()
    time_per_spec=(args.nchan)/1e6/args.rate
    time_per_read=time_per_spec*nspec

    reads_per_file=int(1.0e9*args.gbytes/nbyte)
    print "I think I should write ",reads_per_file," packets per file."

    
    reads_per_print=10000
    time_per_print=time_per_read*reads_per_print
    if args.setclock:
        if trimble_utils.set_clock_trimble():
            print 'Successfully updated system clock to gps time from trimble.'
            have_trimble=True
        else:
            print 'Unable to read time from trimble.'
            have_trimble=False
    else:
        if trimble_utils.get_report_trimble() is None:
            have_trimble=False
        else:
            have_trimble=True
    if have_trimble:
        print "Trimble GPS clock successfully detected."
    else:
        print "Trimble GPS clock not found.  Timestamps will come from system clock."

    mydir=outpart+'/'+args.dir
    print 'writing to directory ',mydir
    if not(os.path.isdir(mydir)):
        os.mkdir(mydir)
    file_header=numpy.asarray([nbyte,len(chan),nspec,header_len,have_trimble],dtype='int')    
    for fnum in range(nfile_targ):
        ct=time.time()
        ct_str=repr(int(ct))    
        ct_root=ct_str[:5]
        mydir=outpart+'/'+args.dir+'/'+ct_root
        print mydir
        if not(os.path.isdir(mydir)):
            os.mkdir(mydir)

        fname=mydir+'/'+ct_str+'.raw'
        if keep_data_time_of_day(args):
            print 'writing to ',fname
        else:
            print 'skipping file ',fname,' due to time of day cuts.'
            fname='/dev/null'

        try:
            f=open(fname,'w')
        except:
            print "Unable to write to file ",fname,".  Exiting."
            sys.exit(2)

        file_header.tofile(f)
        if have_trimble:
            gps_time=trimble_utils.get_gps_time_trimble()
            if gps_time is None:
                gps_time={}
                gps_time['week']=0
                gps_time['seconds']=0
            else:
                print 'gps time is now ',gps_time['week'],gps_time['seconds']
            gps_time=numpy.asarray([gps_time['week'],gps_time['seconds']],dtype='int')
            gps_time.tofile(f)
            latlon=trimble_utils.get_latlon_trimble()
            if latlon is None:
                latlon={}
                latlon['lat']=0
                latlon['lon']=0
                latlon['elev']=0
            else:
                print 'lat/lon/elev are ',latlon['lat'],latlon['lon'],latlon['elev']
            latlon=numpy.asarray([latlon['lat'],latlon['lon'],latlon['elev']],dtype='float')
            latlon.tofile(f)
            
        chan.tofile(f)
        for spec in range(reads_per_file):
        
        
            s.recvfrom_into(data,nbyte)
            f.write(data)
            i=i+1
            if i==reads_per_print:
                t1=time.time()
                print 'data size is',len(data),type(data),t1-t0,time_per_print
                i=0
                t0=t1
        if not(fname=='/dev/null'):
            f.close()
    sys.exit(0)
