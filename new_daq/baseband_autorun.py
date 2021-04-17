import time, datetime, subprocess, threading, argparse, ConfigParser
import numpy as nm
import os

#===========================================================
def run_script_subp(cmdstring,retvals=None,runtime=None,attempts=1,success=0):
    cmd = cmdstring.split(' ')
    for iter in range(attempts):
        try:
            pp=subprocess.Popen(cmd)
            time.sleep(runtime)
            pp.terminate()
            stdout,stderr=pp.communicate()
            retval=pp.returncode
            # print 'retval is ',retval
            if retval!=success:
                print 'Finished process', cmdstring
                return retval,attempts
        except:
            print 'hit error on command ',cmd
            retval=-1
        print 'failed on command ',cmd
    return retval,attempts

#===========================================================
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--configfile", type=str, default="baseband_autorun_config.ini", help="Config file that defines the baseband autorun test parameters")
    args = parser.parse_args()

    config_file = ConfigParser.SafeConfigParser()
    config_file.read(args.configfile)

    # Read run parameters
    testlen = int(config_file.get('baseband_autorun', 'testlen'))
    pauselen = int(config_file.get('baseband_autorun', 'pauselen'))
    config_dir = config_file.get('baseband_autorun', 'config_dir')
    cmd_config_fpga = config_file.get('baseband_autorun', 'cmd_config_fpga')
    cmd_dump_spectra = config_file.get('baseband_autorun', 'cmd_dump_spectra')
    cmd_dump_baseband = config_file.get('baseband_autorun', 'cmd_dump_baseband')

    # Figure out how many tests we want to run
    varpars = {}
    baseband_testvals = []
    iters = 1
    for (p,v) in config_file.items('config_varpars'):
        if p == 'iters':
            iters = int(v)
        else:
            baseband_testvals.append(v)
    baseband_testvals = baseband_testvals*iters
            
    # Loop over test values, generate config file, and get your baseband together, Summer
    for baseband_testval in baseband_testvals:
        # Generate configuration file
        timestamp = datetime.datetime.utcfromtimestamp(time.time())
        config_fname = config_dir+'/config_'+str(timestamp).replace(' ','_')+'.ini'
        fp = open(config_fname, 'w')
        # ... Write section head: this should always be at the top of the config file
        fp.write('[albatros2]\n')
        # ... Write all parameter defaults
        defaults = config_file.items('config_defaults')
        for (p,v) in defaults:
            fp.write(p+'='+v+'\n')
        # ... Write bits, channels, channel_coeffs for this specific test
        bits, channels, channel_coeffs = baseband_testval.split()
        fp.write('bits='+bits+'\n')
        fp.write('channels='+channels+'\n')
        fp.write('channel_coeffs='+channel_coeffs+'\n')
        fp.close()
        # Configure FPGA
        cmd = cmd_config_fpga+' -c '+config_fname
        retval = os.system(cmd)
        if retval != 0:
            print 'Failed to configure FPGA with', config_fname, ' -- skipping'
            continue
        time.sleep(pauselen)
        # Spawn threads to run spectra and baseband DAQs
        cmdstrings = [cmd_dump_spectra+' -c '+config_fname,
                      cmd_dump_baseband+' -c '+config_fname]
        xx = set()
        retvals = {}
        for cmdstring in cmdstrings:
            print 'Starting command', cmdstring
            x = threading.Thread(target=run_script_subp, args=(cmdstring,retvals,testlen,3))
            x.start()
            xx.add(x)
        for x in xx:
            x.join()
