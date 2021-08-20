import RPi.GPIO as GPIO
import time
import os
import subprocess

gpio_warnings=True

def lprint(logfile=None,*args,**kwargs):
    mystr=''
    for arg in args:
        if len(mystr)>0:
            mystr=mystr+' '
        if isinstance(arg,str):
            mystr=mystr+arg
        else:
            mystr=mystr+repr(arg)
    print(mystr)
    if not(logfile is None):
        logfile.write(mystr+'\n')
        logfile.flush()
    


def init_mux():
    # GPIO pin assignments for mux
    A0 = 6
    A1 = 13
    A2 = 19
    A3 = 26
    MUXEN = 12
    PWREN = 16

    # use Broadcom pinout
    GPIO.setmode(GPIO.BCM)

    # set all pins for digital out
    GPIO.setup(A0, GPIO.OUT)
    GPIO.setup(A1, GPIO.OUT)
    GPIO.setup(A2, GPIO.OUT)
    GPIO.setup(A3, GPIO.OUT)
    GPIO.setup(MUXEN, GPIO.OUT)
    GPIO.setup(PWREN, GPIO.OUT)

def select_drive(drive):
#### Select the drive using the mux via RPi GPIO pins
#### The drive argument must be 0-15.
    
    # Otherwise, we get warnings when we run it again, on setmode and setup
#    GPIO.setwarnings(gpio_warnings)

    # GPIO pin assignments for mux
    A0 = 6
    A1 = 13
    A2 = 19
    A3 = 26
    MUXEN = 12
    PWREN = 16

    # GPIO values
    gv = (GPIO.LOW, GPIO.HIGH)

    #select the appropriate drive.
    GPIO.output(A0, gv[(drive >> 0) & 1])
    GPIO.output(A1, gv[(drive >> 1) & 1])
    GPIO.output(A2, gv[(drive >> 2) & 1])
    GPIO.output(A3, gv[(drive >> 3) & 1])

def poweren(state):
#### Set the power enable status of the mux using RPi GPIO pins
#### State argument must be 0 (off) or 1 (on)
    
    # Otherwise, we get warnings when we run it again, on setmode and setup
#    GPIO.setwarnings(gpio_warnings)

    # GPIO pin assignments for mux
    A0 = 6
    A1 = 13
    A2 = 19
    A3 = 26
    MUXEN = 12
    PWREN = 16

    # GPIO values
    gv = (GPIO.LOW, GPIO.HIGH)

    #set the power state
    GPIO.output(PWREN, gv[state])

def muxen(state):
#### Set the mux enable (data path) status of the mux using RPi GPIO pins
#### State argument must be 0 (off) or 1 (on)    

    # Otherwise, we get warnings when we run it again, on setmode and setup
#    GPIO.setwarnings(gpio_warnings)

    # GPIO pin assignments for mux
    A0 = 6
    A1 = 13
    A2 = 19
    A3 = 26
    MUXEN = 12
    PWREN = 16

    # GPIO values
    gv = (GPIO.LOW, GPIO.HIGH)

    #set the mux state
    GPIO.output(MUXEN, gv[state])


def get_drivestates_path():
    home=os.getenv("HOME")
    if home is None:
        print('HOME environment variable not found.  Falling back to hardwired.')
    return home+'/.drivestates.txt'
def isthere(diskid='sda2'):
    stuff=subprocess.check_output(['lsblk'])
    stuff=stuff.decode('utf-8')
    if diskid in stuff:
        return True
    else:
        return False
def ismounted(diskid='sda2'):
    df=subprocess.check_output(['df','-h']).decode('utf-8')
    lines=df.split('\n')
    for line in lines:
        if diskid in line:
            tags=line.split()
            if  diskid in tags[0]:
                ind=line.find(diskid)
                tmp=line[ind+len(diskid):]
                ind2=tmp.find('/')
                mount_point=tmp[ind2:]
                return mount_point
    return None
def lsblk():
    mybytes=subprocess.check_output(['lsblk'])
    return mybytes.decode('utf-8')

def mount_drive_simple(id):
    time.sleep(1)
    select_drive(id)
    time.sleep(1)
    poweren(1)
    time.sleep(1)
    print('calling muxen')
    muxen(1)
    print('made it immediately past muxen')
    time.sleep(5)
    print('made it past 5 seconds')
    time.sleep(30)
    print('mounting drive')
    os.system('sudo mount /dev/sda2 /media/pi/MARS3')
    print('drive is mounted')
    
def mount_drive(id,diskid='sda2',timeout=60,dt=2,mount_point='/media/pi/MARS3'):
    mp=ismounted(diskid)
    if not(mp is None):
        print('drive already mounted at ',mp,'.  Please unmount before proceeding.')
        return None
    if (False):
        print('skipping initial lsblk')
    else:
        if (diskid in lsblk()):
            print('drive ',diskid,' appears in lsblk.  I think you should clean up first in mount_drive.')
            return None
    print('selecting drive')
    select_drive(id)
    time.sleep(0.5)
    print('enabling power')
    poweren(1)
    time.sleep(0.5)
    print('enabling mux')
    muxen(1)
    time.sleep(10.5)
    if False:
        print('sleeping in lieu of lsblk')        
        time.sleep(30)
    else:
        print('starting lsblk search')
        t1=time.time()
        while True:
            if diskid in lsblk():
                print('found drive in lsblk')
                success=True
                break
            if time.time()-t1>timeout:
                print('timeout recognizing drive in lsblk.')
                success=False
                break
            time.sleep(dt)

    time.sleep(0.5)
    mp=ismounted(diskid)
    if not(mp is None):
        print('Drive seemed to automount')
        return mp  #get here if the drive is now mounted
    os.system('sudo mount /dev/'+diskid+' '+mount_point)
    t1=time.time()
    print('mounting drive')
    while True:
        mp=ismounted(diskid)
        if not(mp is None):
            return mp
        if time.time()-t1>timeout:
            print('timout mounting disk')
            return None
        time.sleep(dt)
                  
    
    
def _mount_drive_old(id,diskid='sda2',timeout=60,dt=2):
    if not(ismounted(diskid) is None):
        print('drive is already mounted.  please unmount first.')
        return None
    
    select_drive(id)
    poweren(1)
    muxen(1)
    t1=time.time()
    while (time.time()-t1<timeout):
        mount_point=ismounted(diskid)
        if not(mount_point is None):
            return mount_point
        print('drive not yet mounted')
        time.sleep(dt)
    print('timed out selecting drive ',id)
    return None

def free_drive(dev='/dev/sda2'):
    mp=ismounted(dev)
    if not(mp is None):
        os.system('sudo umount '+dev)
    dd=dev[:-1]
    os.system('sudo udisksctl power-off -b '+dd)
    time.sleep(0.5)
    muxen(0)
    time.sleep(0.5)
    poweren(0)


def scan_drives_jls(diskid='sda2',outf=None):
    t1=time.time()
    for id in range(16):
        lprint(outf,'mounting drive ',id)
        mp=mount_drive(id)
        if mp is None:
            lprint(outf,'failure in mounting drive, going to try again.')
            mp=mount_drive(id)
            if mp is None:
                lprint(outf,'double failure  in mounting.')
        lprint(outf,'drive ',id,' mounted at ',mp,' after ',time.time()-t1,' seconds.')
        time.sleep(1)
        lprint(outf,'calling df')
        os.system('df -kh | grep ' + diskid)
        time.sleep(1)
        myout=subprocess.check_output(['df']).decode('utf-8')
        if diskid in myout:
            lines=myout.split('\n')
            for ll in lines:
                if diskid in ll:
                    lprint(outf,ll)
        else:
            lprint(outf,'Sadness - drive does not appear in df')
        lprint(outf,'freeing drive')
        free_drive()
        lprint(outf,'freed')
        time.sleep(1)
        
def scan_drives(drivesafety=0.95):
#### Makes or updates a statetable with 5 columns: drive number, bytes used, bytes free, percent used, active flag
#### Will take ~8 mins to run as each drive can take ~30sec to be recognized by the Pi.
#### The drivesafety argument is the drive safety parameter from the config file.
#### Uses the mountpoint /media/pi/ALBATROS for all drives.
#### No drives will be mounted after this. Running the following function get_active_drive should mount one if available.
    
    mountpoint = '/media/pi/ALBATROS'
    #sudopassword = 'raspberry'
    sudopassword = 'M@ri0n!'
    mountcmd = 'mount /dev/sda2 ' + mountpoint         ####put an lsblk command here for more robustness, this is ok for now
    umountcmd = 'umount ' + mountpoint
    poweroffcmd = 'udisksctl power-off -b /dev/sda'
    
    #unmount and power-off a drive if one is mounted:
    if os.path.ismount(mountpoint):
        os.system('echo %s|sudo -S %s' % (sudopassword, umountcmd))
        os.system('echo %s|sudo -S %s' % (sudopassword, poweroffcmd))
        time.sleep(5) #let the drive spin down before killing power
    #also set the mux to an off state
    muxen(0)
    poweren(0)
        
    #filepath = '/home/pi/Documents/mux_testing/' #'statetable-filepath-goes-here'
    #filename = filepath+'drivestates.txt'
    filename=get_drivestates_path()
    
    #Open or create the statetable file and read it
    try:
        file = open(filename, "a+")
        filelines = file.readlines()
        file.close()
    except:
        filelines=[]
    
    #scanning through 16 drives
    drivelist = range(16)
    
    #make a default empty list to write the lines to, if the statetable wasn't already present
    if len(filelines) <= 0:
        filelines = [str(drive) + ' 0 0 0 False' for drive in drivelist]

    #now go through all the drives.
    for drive in drivelist:
        #s/p/m/mount drive:
        select_drive(drive)
        poweren(1)
        muxen(1)  
        #can take ~30 sec for the Pi to detect the drive
        time.sleep(30)
        #mount the drive:
        os.system('echo %s|sudo -S %s' % (sudopassword, mountcmd))
        #check the drive's free space and get ready to update the table
        time.sleep(5) #let the mounting finish
        mystr = subprocess.check_output(['df','-k',mountpoint])
        if isinstance(mystr,bytes):
            mystr=mystr.decode('utf-8')
        info = mystr.split('\n') #driveinfo
        tags = info[1].split()
        usedbytes = tags[2]
        freebytes = tags[3]
        usedprct = tags[4].replace('%','') #remove the % symbol from the output of df     
        
        #update the elements of the table
        split = filelines[drive].split()
        split[1] = usedbytes
        split[2] = freebytes
        split[3] = usedprct
        line = ' '.join(split) + '\n'
        filelines[drive] = line

        #unmount and power-off the drive
        time.sleep(5) #let anything from the df command finish
        os.system('echo %s|sudo -S %s' % (sudopassword, umountcmd))
        os.system('echo %s|sudo -S %s' % (sudopassword, poweroffcmd))
        time.sleep(5) #let the drive spin down before killing power
        muxen(0)
        poweren(0)
        
    #after going through all the drives, write the updated table.
    file = open(filename, "w")
    file.writelines(filelines)
    file.close()
    print("Finished updating table!")
    return True

def get_active_drive(drivesafety):
####  Verify that the current active drive, if there is one, isn't too full and keep using it if so.
####  It will also mount the active drive if it was unmounted after for example a power reset and 
####     did not automatically remount itself.
####  Assumes all drives use the mountpoint /media/pi/ALBATROS
####  If the current active drive gets too full, or if there was no active drive, move on to the next 
####     most free drive, set it as the active drive, select it via the mux and mount it.
####  If there is no next most free drive below the drive safety percentage parameter, then all drives are full.
#### The drivesafety argument is the drive safety parameter from the config file.
####  Returns the active drive number (0-15), or False if all drives full.

    #set up some initial parameters
    drives = []
    mountpoint = '/media/pi/ALBATROS'
    sudopassword = 'raspberry'
    mountcmd = 'mount /dev/sda2 ' + mountpoint ####put an lsblk command here for more robustness, this is ok for now
    umountcmd = 'umount ' + mountpoint
    poweroffcmd = 'udisksctl power-off -b /dev/sda'

    #read the state table
    #make a list of unfull drives    
    filepath = '/home/pi/Documents/mux_testing/' #'statetable-filepath-goes-here'
    filename = filepath+'drivestates.txt'
    file = open(filename, "r")
    filelines = file.readlines()
    file.close()
    for i in range(len(filelines)):
        split = filelines[i].split()
        usedprct = int(split[3])
        if usedprct <= drivesafety:
            drives.append(filelines[i])
            
    #look for the active drive
    activedrive = None
    for drive in drives:
        split = drive.split()
        if split[4] == 'True':
            activedrive = drive
            
    #if it finds an active drive: 
    if activedrive is not None:
        isfull = False
        split = activedrive.split()
        drive = int(split[0])
        #check if it's mounted. if it's not, mount it (this assumes if a drive was mounted it was the active drive):
        if os.path.ismount(mountpoint) is False:
        #set the mux state to off, then select the drive, power it on, wait 30sec, and mount it
            muxen(0)
            poweren(0)
            select_drive(drive)
            poweren(1)
            muxen(1)
            #takes ~30sec for the pi to recognize the drive:
            time.sleep(30)
            os.system('echo %s|sudo -S %s' % (sudopassword, mountcmd))
        #check the active drive's free space.  
        mystr = subprocess.check_output(['df','-k',mountpoint])
        info = mystr.split('\n') #driveinfo
        tags = info[1].split()
        usedbytes = tags[2]
        freebytes = tags[3]
        usedprct = int(tags[4].replace('%','')) #remove the % symbol from the output of df
        split[1] = usedbytes
        split[2] = freebytes
        split[3] = str(usedprct)
        #if it is too full, unmount it and set its status in the table
        if usedprct >= drivesafety:
            split[4] = 'False'
            #unmount and power-off the drive
            os.system('echo %s|sudo -S %s' % (sudopassword, umountcmd))
            os.system('echo %s|sudo -S %s' % (sudopassword, poweroffcmd))
            time.sleep(5) #let the drive spin down before killing power
            muxen(0)
            poweren(0)
            isfull = True
            drives.remove(activedrive)
            line = ' '.join(split)+'\n'
            filelines[drive] = line
        #if it's not too full update the table and we're done:
        else:
            line = ' '.join(split)+'\n'
            filelines[drive] = line
            file = open(filename, "w")
            file.writelines(filelines)
            file.close()
            return drive
            
    #if there is no active drive, or if the active drive was too full:
    if activedrive is None or isfull is True:
        #pick the next most free drive. if there is no next most free drive, then all drives are full.
        try:
            freespace = [int(row.split()[3]) for row in drives]
            minindex = freespace.index(min(freespace))
            activedrive = drives[minindex]
        except (ValueError):
            print("All drives are full!")
            #update the table:
            file = open(filename, "w")
            file.writelines(filelines)
            file.close()
            return False
        
        #mount it, and it should be good to go, only the active drive was in use so the table should be accurate for this drive.
        split = activedrive.split()
        drive = int(split[0])
        muxen(0)
        poweren(0)
        select_drive(drive)
        poweren(1)
        muxen(1)
        #can take ~30 sec for the pi to recognize the drive.
        time.sleep(30)
        os.system('echo %s|sudo -S %s' % (sudopassword, mountcmd))
        #update the table with this drive as the active drive, and that's it.
        split[4] = 'True'
        line = ' '.join(split)+'\n'
        filelines[drive] = line
        file = open(filename, "w")
        file.writelines(filelines)
        file.close()
        return drive
