import numpy as np
import subprocess
import sys
import math
import operator
import os
import stat
import datetime

def get_channels_from_str(chan, nbits):
    new_chans=np.empty(0, dtype=">H")
    multi_chan=chan.split(" ")
    chan_start_stop=[]
    for single_chan in multi_chan:
        start_stop=map(int, single_chan.split(":"))
        chan_start_stop.extend(start_stop)
    if nbits==1:
        for i in range(len(chan_start_stop)/2):
            new_chans=np.append(new_chans, np.arange(chan_start_stop[2*i], chan_start_stop[2*i+1], 2, dtype=">H"))
    elif nbits==2:
        for i in range(len(chan_start_stop)/2):
            new_chans=np.append(new_chans, np.arange(chan_start_stop[2*i], chan_start_stop[2*i+1], dtype=">H"))
    else:
        for i in range(len(chan_start_stop)/2):
            chans=np.arange(chan_start_stop[2*i], chan_start_stop[2*i+1], dtype=">H")
            new_chans=np.append(new_chans, np.ravel(np.column_stack((chans, chans))))
    return new_chans

def get_coeffs_from_str(coeffs):
    multi_coeff=coeffs.split(" ")
    new_coeffs=np.zeros(2048)
    for single_coeff in multi_coeff:
        start_stop_coeff=map(int, single_coeff.split(":"))
        if start_stop_coeff[2]>=0:
            val=start_stop_coeff[2]
        else:
            val=2**(-start_stop_coeff[2])
        #new_coeffs[np.arange(start_stop_coeff[0], start_stop_coeff[1])]=start_stop_coeff[2]
        new_coeffs[np.arange(start_stop_coeff[0], start_stop_coeff[1])]=val
    new_coeffs=np.asarray(new_coeffs, dtype=">I")
    return new_coeffs

def get_channels_from_freq(nu=[0,30],nbit=0,nu_max=125,nchan=2048,dtype='>i2',verbose=False):

    nseg=len(nu)/2
    for j in range(nseg):
        nu0=nu[2*j]
        nu1=nu[2*j+1]
        if (nu0<nu_max)&(nu1>nu_max):
            print 'frequency segment covering max native frequency not allowed'
            return None
        if nu0>nu_max:
            nu0=2*nu_max-nu0
        if nu1>nu_max:
            nu1=2*nu_max-nu1
        if nu0>nu1:
            tmp=nu1
            nu1=nu0
            nu0=tmp
        ch_min=np.int(np.floor(nu0*1.0/nu_max*nchan))
        ch_max=np.int(np.ceil(nu1*1.0/nu_max*nchan))
        mynchan=ch_max-ch_min+1
        if verbose:
            print j,nu0,nu1,ch_min,ch_max,mynchan
        if nbit==0:
            if mynchan&1==1:
                if verbose:
                    print 'padding 1-bit requested data to have even # of channels'
                mynchan=mynchan+1
        if nbit==0:
            myvec=np.arange(mynchan/2,dtype=dtype)*2+ch_min
        if nbit==1:
            myvec=np.arange(mynchan,dtype=dtype)+ch_min
        if nbit==2:
            myvec=np.arange(mynchan*2,dtype=dtype)/2+ch_min
        if j==0:
            ch_vec=myvec
        else:
            ch_vec=np.append(ch_vec,myvec)
        ch_vec=np.asarray(ch_vec,dtype=dtype)
        print(ch_vec)
    return ch_vec

def get_channels_from_freq_old(nu0=0,nu1=30,nbit=0,nu_max=125,nchan=2048,dtype='>i2'):
    mylen=1
    try:
        mylen=len(nu0)
    except:
        pass
    if mylen>1:
        if len(nu1)!=mylen:
            print 'length of nu0 and nu1 in get_channels_from_freq do not match.'
            return None
        for j in range(mylen):
            tmp=get_channels_from_freq(nu0[j],nu1[j],nbit,nu_max,nchan,dtype)
            if j==0:
                ch_vec=tmp
            else:
                ch_vec=np.append(ch_vec,tmp)
        return np.asarray(ch_vec,dtype=dtype)

    ch_min=np.int(np.floor(nu0*1.0/nu_max*nchan))
    ch_max=np.int(np.ceil(nu1*1.0/nu_max*nchan))
    nchan=ch_max-ch_min+1
    #print ch_min,ch_max,nchan
    if nbit==0:
        if nchan&1==1:
            print 'padding 1-bit requested data to have even # of channels'
            nchan=nchan+1
    if nbit==0:
        ch_vec=np.arange(nchan/2,dtype=dtype)*2+ch_min
    if nbit==1:
        ch_vec=np.arange(nchan,dtype=dtype)+ch_min
    if nbit==2:
        ch_vec=np.arange(nchan*2,dtype=dtype)/2+ch_min
    ch_vec=np.asarray(ch_vec,dtype=dtype)
    return ch_vec

def get_nspec(chans,max_nbyte=1380):
    nspec=np.int(np.floor(max_nbyte/len(chans)))
    if nspec>30:
        nspec=30
    return nspec

def find_emptiest_drive(tag='media'):
    """Find the entry in df with the most free space that included tag in its path."""
    mystr=subprocess.check_output(['df','-k'])
    lines=mystr.split('\n')
    best_free=0
    for ll in lines:
        #print ll
        tags=ll.split()        
        if len(tags)>1:
            #print tags[-1]
            if tags[-1].find(tag)>=0:
                myfree=float(tags[3])
                #print 'possible drive is ',tags[-1],myfree
                if myfree>best_free:
                    best_free=myfree
                    best_dir=tags[-1]
    #print 'best directory is ',best_dir,' with ',best_free/1024./1024.,' free GB'
    if best_free>0:
        return best_dir
    else:
        return None

def list_drives_to_write_too(drive="ALBATROS"):
    process_output=subprocess.check_output(['df','-k', '--block-size=1'])
    process_lines=process_output.split('\n')
    drives=[]
    for line in process_lines:
        if len(line)>0:
            tags=line.split()
            if tags[-1].find(drive)>=0:
                drives.append({"Partition name":tags[-1].split("/")[-1], "Device":tags[0], "Blocks":int(tags[1]), "Used":int(tags[2]), "Available":int(tags[3]), "Use%":int(tags[4][:-1]), "Mounted on":tags[5]})
    drive_free_bytes=[]
    for drive in drives:
        drive_free_bytes.append(drive["Use%"])
    new_drives=[]
    for i in range(len(drive_free_bytes)):
        max_index, max_value=max(enumerate(drive_free_bytes), key=operator.itemgetter(1))
        new_drives.append(drives.pop(max_index))
        drive_free_bytes.pop(max_index)
    return new_drives

def num_files_can_write(drive_path, safety, file_size):
    st=os.statvfs(drive_path)
    used_bytes=st.f_blocks*st.f_bsize-st.f_bfree*st.f_bsize
    free_bytes=st.f_bsize*st.f_bavail
    total=used_bytes+free_bytes
    nfile_targ=int(math.floor((safety/100.*total-used_bytes)/(1.024e9*file_size)))
    return nfile_targ
    
def find_mac():    
    mystr=subprocess.check_output('ifconfig')
    lines=mystr.split('\n')
    targ='192.168.2.200'
    mac=""
    for i in range(len(lines)):
        ll=lines[i]
        if ll.find(targ)>0:
            #print 'found target in line ',ll
            #print 'previous line was ',lines[i-1]
            tags=lines[i-1].split()
            mac='0x'+tags[0][3:-1]
    return mac
            
def gps_time_from_rtc():
    utc=datetime.datetime.now()
    datetimeformat="%Y-%m-%d %H:%M:%S"
    epoch=datetime.datetime.strptime("1980-01-06 00:00:00",datetimeformat)
    tdiff=utc-epoch
    gpsweek=tdiff.days//7 
    gpsdays=tdiff.days-7*gpsweek         
    gpsseconds=tdiff.seconds+86400*(tdiff.days-7*gpsweek)
    return {"week":gpsweek, "seconds":gpsseconds}
