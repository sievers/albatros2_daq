import tsip
import serial
import datetime
import os
import time
import math
import stat
#import subprocess

#from functools import wraps
#import errno
##import os
#import signal

import signal


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
            print port, ' is not generally readable.'
            os.system('sudo chmod a+rw '+port)
            st=os.stat(port)
            if ((st.st_mode&stat.S_IROTH)&(st.st_mode&stat.S_IWOTH)):
                print 'was unable to fix permissions on port ',port, '.  Exiting get_report_trimble_raw'
                return None
    except:
        print 'port ',port,' does not exist.  Exiting get_report_trimble_raw'
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
            print 'failed to read trimble on attempt ',i
    return None #hopefully not get here

    
        

def set_clock_trimble(id=171,baud=9600,port='/dev/ttyUSB0'):
    report=get_report_trimble(id,baud,port)
    if report is None:
        print 'unable to read time from trimble in set_clock_trimble.'
        return False
    mytime=datetime.datetime(report[11],report[10],report[9],report[8],report[7],report[6])
    to_exec='sudo date -s " %s "' % mytime.ctime()
    os.system(to_exec)
    return True
    #return mytime

def get_gps_time_trimble(id=171,baud=9600,port='/dev/ttyUSB0',maxtime=4,maxiter=5):
    report=get_report_trimble(id,baud,port,maxtime,maxiter)
    if report is None:
        print 'unable to read trimble in get_gps_time_trimble'
        return None
    gps_time={}
    gps_time['week']=report[3] # sometimes week number is off by 1024 (GPS rollover problem)
    gps_time['seconds']=report[2]
    return gps_time

def get_latlon_trimble(id=172,baud=9600,port='/dev/ttyUSB0',maxtime=4,maxiter=5):
    report=get_report_trimble(id,baud,port,maxtime,maxiter)
    if report is None:
        print 'unable to read trimble in get_latlon_trimble.'
        return None
    latlon={}
    latlon['lat']=report[17]*180/math.pi
    latlon['lon']=report[18]*180/math.pi
    latlon['elev']=report[19]
    return latlon

def get_gps_timestamp_trimble(id=171,baud=9600,port='/dev/ttyUSB0',maxtime=4,maxiter=5):
    report=get_report_trimble(id,baud,port,maxtime,maxiter)
    if report is None:
        print('unable to read trimble in get_gps_timestamp_trimble')
        return None
    year=report[11]
    month=report[10]
    day=report[9]
    hour=report[8]
    minute=report[7]
    second=report[6]
    return (datetime.datetime(year,month,day,hour,minute,second)-datetime.datetime(1970,1,1)).total_seconds()

def convert_gps_to_sys(gps_time):
    gps_to_sys = (datetime.datetime(year=1980,month=1,day=6) - datetime.datetime(year=1970,month=1,day=1)).total_seconds()
    sys_time = gps_time["week"]*7*24*3600 + gps_time["seconds"] + gps_to_sys
    return sys_time
