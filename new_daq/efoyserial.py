# -*- coding: utf-8 -*-
"""
Created on Mon Aug 16 15:12:32 2021

@author: harry
"""

import serial
import time
import serial.tools.list_ports
import datetime

def read_efoy():
    ports = None
    comport = None
    
    try:
        ports = serial.tools.list_ports.comports() #get all the comports in use
        if not ports:
            print("could not find comports")
            return False
    except:
        print("error listing comports")
        return False
        
    try:        
        for port in ports:
#            if 'Serial' in port.description: #find the USB-Serial adapter. Could also use port.pid or port.vid to use the USB vendor ID or product ID to get more specific
            if 'US232R' in port.description: #find the USB-Serial adapter - linux description
                comport = port.device #that's our comport
        if comport is None:
            print("could not find USB-Serial adapter")
            return False
    except:
        print("error finding comport")
        return False

    try:
        ser = serial.Serial(comport) #open the port
    except:
        print("error opening comport")
        return False
        
    try:
        ser.write('SFC') #write the command
        ser.write('\r') #efoy is unhappy if it gets SFC and carriage return on the same line...dunno why
    except:
        print("error writing to comport")
        return False

    time.sleep(.5) #let the efoy answer

    try:
        output = ser.read(ser.in_waiting).split('\r') #get the output
    except:
        print("error reading comport buffer")
        return False
    
    try:
        ser.close()
    except: 
        print("error closing comport")
        return False
    
    tstamp = datetime.datetime.utcnow()
    
    return tstamp, output

filepath = '/home/pi/logs/efoy/'

while(True):
    
    efoydata = read_efoy()
    
    if efoydata is not False:
        tstamp = efoydata[0].strftime('%Y%m%d')
        ctime = int((efoydata[0]-datetime.datetime(1970,1,1)).total_seconds())
        filedata = str(ctime)+' '+str(efoydata[0])+' '+str(efoydata[1])+'\n'
        
        filename = tstamp+'.txt'
        file = open(filepath+filename, 'a+')
        file.write(filedata)
        file.close()
        print('wrote to ' + filename)

    time.sleep(60)
        


