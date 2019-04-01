import numpy as np
import subprocess

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
    
