#!/usr/bin/env /usr/bin/python

import os, subprocess

# Before doing anything, check if supervisord is running already.  If
# yes, then cry for help and don't do anything.
txt = subprocess.Popen(['ps','-C','supervisord','-o','pid='], stdout=subprocess.PIPE).communicate()[0]
txt = txt.strip()
if len(txt) > 0:
    print 'Looks like supervisord is already running under process ID',txt
    print 'Quitting here and not starting DAQ.'
    exit(0)

cmd = 'supervisord -c ${DAQDIR}/supervisord_albaboss.conf'
os.system(cmd)
print 'Started supervised DAQ process'
exit(0)
