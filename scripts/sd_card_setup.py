#!/usr/bin/python
import argparse
import subprocess
import os

def make_backup(path):
    i=0
    bak_path=path+".bak"
    while os.path.isfile(bak_path):
        i=i+1
        bak_path=path+".bak.%d"%(i)
    print("Making copy of %s to %s"%(path, bak_path))
    subprocess.call(["cp", path, bak_path])
    return None

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("-b", "--boot", type=str, help="Mount point of SD card boot partition")
    parser.add_argument("-r", "--rootfs", type=str, help="Mount point of SD card rootfs partition")
    parser.add_argument("-i", "--i2c", action="store_true", help="Enable i2c interface")
    parser.add_argument("-spi", "--spi", action="store_true", help="Enable spi interface")
    parser.add_argument("-s", "--ssh", action="store_true", help="Enable ssh on pi")
    parser.add_argument("-sip", "--ssh_ip", type=str, help="Set a static ip for ssh-ing")
    parser.add_argument("-S", "--ssh_interface", default="eth1", type=str, help="Network interface for ssh")
    parser.add_argument("-bip", "--baseband_ip", type=str, help="Set a static ip for reading baseband")
    parser.add_argument("-B", "--baseband_interface", default="eth0", type=str, help="Network interface for baseband")
    parser.add_argument("-rx", "--receive", type=int, help="UDP receive buffer size in bytes")
    parser.add_argument("-g", "--git", type=str, help="git repository for albatros2_daq")
    args=parser.parse_args()

    if args.i2c or args.spi:
        config_file_path=args.boot+"/config.txt"
        make_backup(config_file_path)
        data=None
        with open(config_file_path, "r") as config:
            if args.spi:
                data=config.read()
                print("Enabling SPI bus")
                data=data.replace("#dtparam=spi=on", "dtparam=spi=on")
            if args.i2c:
                print("Enabling I2C bus")
                data=data.replace("#dtparam=i2c_arm=on", "dtparam=i2c_arm=on")
        
        with open(config_file_path, "w") as config:
            config.write(data)
        
    if args.ssh:
        print("Adding ssh file to %s"%(args.boot))
        subprocess.Popen(["touch", "%s/ssh"%(args.boot)]).wait()

    if args.ssh_ip>0 or args.baseband_ip>0:
        dhcpcd_file_path=args.rootfs+"/etc/dhcpcd.conf"
        make_backup(dhcpcd_file_path)
        with open(dhcpcd_file_path, "a") as dhcpcd:
            if args.ssh_ip!=None:
                print("Writing ssh-ing IP address to %s"%(dhcpcd_file_path))
                dhcpcd.write("\n")
                dhcpcd.write("############### Static IP configuration for ssh-ing ###############\n")
                ssh_rdn=args.ssh_ip[:args.ssh_ip.rfind(".")+1]+"1"
                dhcpcd.write("interface %s\n"%(args.ssh_interface))
                dhcpcd.write("static ip_address=%s/24\n"%(args.ssh_ip))
                dhcpcd.write("#static ip6_address=fd51:42f8:caae:d92e::ff/64\n")
                dhcpcd.write("static routers=%s\n"%(ssh_rdn))
                dhcpcd.write("static domain_name_servers=%s 8.8.8.8\n"%(ssh_rdn))
                dhcpcd.write("\n")
                dhcpcd.write("# It is possible to fall back to a static IP if DHCP fails:\n")
                dhcpcd.write("# define static profile\n")
                dhcpcd.write("profile static_%s\n"%(args.ssh_interface))
                dhcpcd.write("static ip_address=%s/24\n"%(args.ssh_ip))
                dhcpcd.write("#static routers=%s\n"%(ssh_rdn))
                dhcpcd.write("#static domain_name_servers=%s 8.8.8.8\n"%(ssh_rdn))
                dhcpcd.write("\n")
                dhcpcd.write("# fallback to static profile on %s\n"%(args.ssh_interface))
                dhcpcd.write("interface %s\n"%(args.ssh_interface))
                dhcpcd.write("fallback static_%s\n"%(args.ssh_interface))
                dhcpcd.write("###################################################################\n")
            if args.baseband_ip!=None:
                print("Writing baseband reading IP address to %s"%(dhcpcd_file_path))
                dhcpcd.write("\n")
                dhcpcd.write("############## Static IP configuration for baseband ###############\n")
                baseband_rdn=args.baseband_ip[:args.baseband_ip.rfind(".")+1]+"1"
                dhcpcd.write("interface %s\n"%(args.baseband_interface))
                dhcpcd.write("static ip_address=%s/24\n"%(args.baseband_ip))
                dhcpcd.write("#static ip6_address=fd51:42f8:caae:d92e::ff/64\n")
                dhcpcd.write("#static routers=%s\n"%(baseband_rdn))
                dhcpcd.write("#static domain_name_servers=%s 8.8.8.8\n"%(baseband_rdn))
                dhcpcd.write("\n")
                dhcpcd.write("# It is possible to fall back to a static IP if DHCP fails:\n")
                dhcpcd.write("# define static profile\n")
                dhcpcd.write("profile static_%s\n"%(args.baseband_interface))
                dhcpcd.write("static ip_address=%s/24\n"%(args.baseband_ip))
                dhcpcd.write("#static routers=%s\n"%(baseband_rdn))
                dhcpcd.write("#static domain_name_servers=%s 8.8.8.8\n"%(baseband_rdn))
                dhcpcd.write("\n")
                dhcpcd.write("# fallback to static profile on %s\n"%(args.baseband_interface))
                dhcpcd.write("interface %s\n"%(args.baseband_interface))
                dhcpcd.write("fallback static_%s\n"%(args.baseband_interface))
                dhcpcd.write("###################################################################\n")

    if args.receive>0:
        sysctl_file_path=args.rootfs+"/etc/sysctl.conf"
        make_backup(sysctl_file_path)
        with open(sysctl_file_path, "a") as scf:
            print("Setting udp receive buffer size to %d"%(args.receive))
            scf.write("net.core.rmem_default=%d\n"%(args.receive))
            scf.write("net.core.rmem_max=%d\n"%(args.receive))
        
    if args.git>0:
        print("Cloning %s to %s/home/pi/albatros2_daq"%(args.git, args.rootfs))
        subprocess.Popen(["git", "clone", args.git, "%s/home/pi/albatros2_daq"%(args.rootfs)]).wait()
