#!/usr/bin/python

import muxtools
import supertools
import time
import subprocess



if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument("-s","--sleep",type=float,default=0.0,help="Time to sleep after each initialization command.")
    parser.add_argument("-r","--retries",type=int,default=3,help="Number of retry attempts before giving up.")
    
    args=parser.parse_args()
    
    dt=args.sleep

    diskid=supertools.select_next_drive()
    if diskid is None:
        print('Error - diskid not returned by select_next_drive')
        assert(1==0)

    muxtools.init_mux()
    time.sleep(dt)
    muxtools.poweren(0)
    time.sleep(dt)
    muxtools.muxen(0)
    time.sleep(dt)
    muxtools.mount_drive(diskid)


    
    
