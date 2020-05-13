#!/usr/bin/python
import subprocess
import sys

mystr=subprocess.check_output('ifconfig')
lines=mystr.split('\n')
targ='192.168.2.200'
for i in range(len(lines)):
    ll=lines[i]
    if ll.find(targ)>0:
        #print 'found target in line ',ll
        #print 'previous line was ',lines[i-1]
        tags=lines[i-1].split()
        print '0x'+tags[0][3:-1]
        sys.exit(0)
        
