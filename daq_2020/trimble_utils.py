import tsip
import serial
import datetime
import os
import time
import math
import stat
import logging
#import subprocess

#from functools import wraps
#import errno
##import os
#import signal

import signal

logger=logging.getLogger(__name__)

class TimeoutError(Exception):
    pass
    
class timeout:
    def __init__(self, seconds=1, error_message='Timeout'):
        self.seconds = seconds
        self.error_message = error_message
    def handle_timeout(self, signum, frame):
        raise TimeoutError(self.error_message)
    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)
    def __exit__(self, type, value, traceback):
        signal.alarm(0)


def get_report_trimble_raw(id=171,baud=9600,port='/dev/ttyUSB0',maxtime=10):
    #mystr=subprocess.check_output(['ls','-l',port])
    try:
        st=os.stat(port)    
        if ((st.st_mode&stat.S_IROTH)==0)&((st.st_mode&stat.S_IWOTH)==0):
            logger.error('%s is not generally readable.'%(port))
            os.system('sudo chmod a+rw '+port)
            st=os.stat(port)
            if ((st.st_mode&stat.S_IROTH)&(st.st_mode&stat.S_IWOTH)):
                logger.error('Unable to fix permissions on port %s.  Exiting get_report_trimble_raw'%(port))
                return None
    except:
        logger.error('Port %s does not exist.  Exiting get_report_trimble_raw'%(port))
        return None
    
    with timeout(seconds=maxtime):  #This sort of timeout should probably be added to the packet receiving code so it times out in the event of an FPGA hang.
        serial_conn = serial.Serial(port, baud)    
        gps_conn = tsip.GPS(serial_conn)
        command = tsip.Packet(0x21)
        gps_conn.write(command)
        report=gps_conn.read()
        while report[1]!=id:
            report=gps_conn.read()
        return report

def get_report_trimble(id=171,baud=9600,port='/dev/ttyUSB0',maxtime=4,maxiter=5):
    for i in range(maxiter):
        try:
            report=get_report_trimble_raw(id,baud,port,maxtime)
            return report
        except:
            logger.error('Failed to read trimble on attempt %d'%(i+1))
    return None #hopefully not get here

    
        

def set_clock_trimble(id=171,baud=9600,port='/dev/ttyUSB0'):
    report=get_report_trimble(id,baud,port)
    if report is None:
        logger.error('Unable to read time from trimble in set_clock_trimble.')
        return False
    mytime=datetime.datetime(report[11],report[10],report[9],report[8],report[7],report[6])
    to_exec='sudo date -s " %s "' % mytime.ctime()
    os.system(to_exec)
    return True
    #return mytime

def get_gps_time_trimble(id=171,baud=9600,port='/dev/ttyUSB0'):
    report=get_report_trimble(id,baud,port)
    if report is None:
        logger.error('Unable to read trimble in get_gps_time_trimble')
        return None
    gps_time={}
    gps_time['week']=report[3]
    gps_time['seconds']=report[2]
    return gps_time

def get_latlon_trimble(id=172,baud=9600,port='/dev/ttyUSB0'):
    report=get_report_trimble(id,baud,port)
    if report is None:
        logger.error('Unable to read trimble in get_latlon_trimble.')
        return None
    latlon={}
    latlon['lat']=report[17]*180/math.pi
    latlon['lon']=report[18]*180/math.pi
    latlon['elev']=report[19]
    return latlon
