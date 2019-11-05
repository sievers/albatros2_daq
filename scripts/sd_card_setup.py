#!/usr/bin/python
import argparse
import subprocess
import os

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("-b", "--boot", type=str, help="Mount point of SD card boot partition")
    parser.add_argument("-r", "--rootfs", type=str, help="Mount point of SD card rootfs partition")
    parser.add_argument("-i", "--i2c", action="store_true", help="Enable i2c interface")
    parser.add_argument("-s", "--ssh", action="store_true", help="Enable ssh on pi")
    parser.add_argument("-g", "--git", type=str, help="git repository for albatros2_daq")
    args=parser.parse_args()

    i=0
    config_path=args.boot+"/config.txt"
    bak_path=args.boot+"/config.txt"+".bak"
    while os.path.isfile(bak_path):
        i=i+1
        bak_path=args.boot+"/config.txt"+".bak.%d"%(i)
    print("Making copy of %s to %s"%(config_path, bak_path))
    subprocess.call(["cp", config_path, bak_path])

    data=None
    with open(config_path, "r") as config:
        data=config.read()
        print("Enabling SPI bus")
        data=data.replace("#dtparam=spi=on", "dtparam=spi=on")
        if args.i2c:
            print("Enabling I2C bus")
            data=data.replace("#dtparam=i2c_arm=on", "dtparam=i2c_arm=on")
        
    with open(config_path, "w") as config:
        config.write(data)
        
    if args.ssh:
        print("Adding ssh file to %s"%(args.boot))
        subprocess.Popen(["touch", "%s/ssh"%(args.boot)]).wait()

    if args.git>0:
        print("Cloning %s to %s/home/pi/albatros2_daq"%(args.git, args.rootfs))
        subprocess.Popen(["git", "clone", args.git, "%s/home/pi/albatros2_daq"%(args.rootfs)]).wait()
