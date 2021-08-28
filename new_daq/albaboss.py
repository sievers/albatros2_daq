import argparse
import threading
import time
import os
import subprocess

def run_script(cmd,attempts=1,success=0):
    #return 0,0  #useful for testing
    for iter in range(attempts):
        retval=os.system(cmd)
        #retval=success
        #os.system(cmd)
        if retval==success:
            return retval,iter
    return retval,iter+1

def run_script_subp(cmd,retvals=None,attempts=1,success=0):
    for iter in range(attempts):
        try:
            #if you want to read stdout/stderr from the subprocess, you can do that by setting the flags to PIPE
            #pp=subprocess.Popen([cmd,''],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            # pp=subprocess.Popen([cmd,''])
            tags=cmd.split()
            if len(tags)==1:
                pp=subprocess.Popen([cmd])
            else:
                pp=subprocess.Popen(tags)
            time.sleep(3)
            stdout,stderr=pp.communicate()
            retval=pp.returncode
            print('retval is ',retval)
            if not(retvals is None): #if threaded, we can't easily get return values, so write to a dictionary.
                retvals[cmd]=retval
            if retval==success:
                #print 'stdout on ',cmd,' is :',stdout
                #print 'stderr on ',cmd,' is :',stderr
                #print 'retval is ',retval,' on ',cmd
                return retval,attempts
        except:
            print('hit error on command ',cmd)
            retval=-1
        print('failed on command ',cmd)
    return retval,attempts

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument("-I","--init",nargs='+',type=str,default="",help="List of commands to execute as initializations.")
    parser.add_argument("-C","--commands",nargs='+',type=str,default="",help="List of commands to execute after initialization.")
    parser.add_argument("-s","--sleep",type=float,default=0.0,help="Time to sleep after each initialization command.")
    parser.add_argument("-r","--retries",type=int,default=3,help="Number of retry attempts before giving up.")
    args=parser.parse_args()

    #print 'input string is',args.init
    #print 'type is ',type(args.init)
    #print 'input commands are',args.commands
    
    #print 'going to execute the following sequentially at startup:'
    for cmd in args.init:
        print('executing ',cmd,' at startup.')
        retval,iter=run_script(cmd,attempts=args.retries)
        if retval!=0:
            print('Command ',cmd,' failed with exit code ',retval,' with ',iter,' failures.')
            #you might wish to exit or reboot or something if this happens
        else:
            print('Command ',cmd,'succeeded after ',iter,' failures.')
        if args.sleep>0:
            time.sleep(args.sleep)


    xx=set()
    retvals={}
    for cmd in args.commands:  #loop over commands, and start a thread for each that will spawn subprocesses
        print('starting command ',cmd)
        x=threading.Thread(target=run_script_subp,args=(cmd,retvals,args.retries))
        x.start()
        xx.add(x)
    for x in xx:  #this
        x.join()
    for cmd in args.commands:
        print('return value for ',cmd,' is ',retvals[cmd])
    #print 'keys are ',retvals.keys()


