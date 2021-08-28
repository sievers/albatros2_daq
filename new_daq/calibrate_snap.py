import numpy as np
import math
import os, time
import subprocess
import scio
#import re
import ConfigParser
import argparse

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--configfile", type=str, default="config.ini")
    parser.add_argument("-t", "--runtime", type=float, default=30.0)
    parser.add_argument("-o", "--cal_data_dir", type=str, default="/home/pi/calibration_data")
    parser.add_argument("-pmin", type=float, default=-50, help="Minimum power level to sweep (dBm)")
    parser.add_argument("-pmax", type=float, default=10, help="Maximum power level to sweep (dBm)")
    parser.add_argument("-pint", type=float, default=10, help="Interval between power levels in sweep (dBm)")
    parser.add_argument("-fmin", type=float, default=5.0, help="Minimum frequency to sweep (MHz)")
    parser.add_argument("-fmax", type=float, default=50.0, help="Maximum frequency to sweep (MHz)")
    parser.add_argument("-fint", type=float, default=10.0, help="Interval between frequencies in sweep (MHz)")
    args = parser.parse_args()

    config_file = ConfigParser.SafeConfigParser()
    config_file.read(args.configfile)
    spectra_output_dir = config_file.get("albatros2", "dump_spectra_output_directory")

    ratio = 125.0/2048.0 # MHz/bin

    timestamp = str(int(time.time()))
    time_frag = timestamp[:5]
    outsubdir = args.cal_data_dir+'/'+time_frag+'/'+timestamp
    if not os.path.isdir(outsubdir):
        os.makedirs(outsubdir)

    print("Starting calibration run...")
    print("Provide known signals to the SNAP using a trusted signal generator.")

    pwrs = np.arange(args.pmin, args.pmax+1, args.pint)
    #print("Power levels: ", pwrs)

    chanmin = int(math.ceil(args.fmin/ratio))
    chanmax = int(math.floor(args.fmax/ratio))
    chaninterval = int(math.floor(args.fint/ratio))
    chans = np.arange(chanmin, chanmax+1, chaninterval)
    #print("Channels: ", chans)

    freqs = chans*ratio
    #print("Frequencies: ", freqs)

    while True:
        inp = raw_input(bcolors.UNDERLINE+"ADC0 or ADC3? (0/3):"+bcolors.ENDC+" ")
        if inp == "0":
            adc = 0
            break
        elif inp == "3":
            adc = 3
            break

    cal_array = np.zeros((len(pwrs), len(freqs)))
    with open(outsubdir+'/cal_log.txt', "w") as log:
        log.write("Frequency (MHz), Channel, Power (dBm), Timestamp\n")

#    pattern = re.compile("Writing current data to (\S+)") # find this pattern in stdout to get data directory

    end = False
    for i, (freq, chan) in enumerate(zip(freqs, chans)):
        if end:
            break
        else:
            for j, pwr in enumerate(pwrs):
                if end:
                    break
                else:
                    while True:
                        inp = raw_input(bcolors.UNDERLINE+"Frequency: {} MHz / Power: {} dBm. (y/n/end):".format(freq, pwr)+bcolors.ENDC+" ")
                        if inp == 'y' or inp == 'Y' or inp == 'n' or inp == 'N' or inp == 'end' or inp == 'END':
                            break
                    if inp == 'n' or inp == 'N':
                        print("Skipping...")
                        continue
                    elif inp == 'end' or inp == 'END':
                        print("Ending sweep...")
                        end = True
                    elif inp == 'y' or inp == 'Y':
                        print("Collecting calibration data... WILL RUN FOR {} SECONDS".format(args.runtime))
                        cmd = "python dump_spectra.py -c "+args.configfile
                        cmd = cmd.split(' ')
                        pp = subprocess.Popen(cmd)
                        time.sleep(args.runtime)
                        pp.terminate()
                        while True:
                            tstamp = raw_input(bcolors.UNDERLINE+"Timestamp:".format(freq, pwr)+bcolors.ENDC+" ")
                            data_dir = spectra_output_dir+'/'+tstamp[:5]+'/'+tstamp
                            if adc == 0:
                                if os.path.isfile(data_dir+'/pol00.scio'):
                                    poldata = scio.read(data_dir+'/pol00.scio')
                                    break
                                elif os.path.isfile(data_dir+'/pol00.scio.bzip2'):
                                    poldata = scio.read(data_dir+'/pol00.scio.bzip2')
                                    break
                            elif adc == 3:
                                if os.path.isfile(data_dir+'/pol11.scio'):
                                    poldata = scio.read(data_dir+'/pol11.scio')
                                    break
                                elif os.path.isfile(data_dir+'/pol11.scio.bzip2'):
                                    poldata = scio.read(data_dir+'/pol11.scio.bzip2')
                                    break
                        #print(poldata)
                        poldata_mean = np.mean(poldata[1:, chan])
                        print("Log ADC value: {}".format(np.log10(poldata_mean)))
                        print("Saving calibration data...")
                        cal_array[j,i] = poldata_mean
                        with open(outsubdir+'/cal_log.txt', 'a') as log:
                            log.write(str(freq)+', '+str(chan)+', '+str(pwr)+', '+tstamp+'\n')
    headerstr = "Power levels (dBm): {}\nFrequencies (MHz): {}\nChannels: {}".format(pwrs, freqs, chans)
    np.savetxt(outsubdir+'/cal_data.txt', cal_array, delimiter=',', header=headerstr)
