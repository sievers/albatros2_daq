#!/usr/bin/python
import argparse
import subprocess
import os

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("path", type=str, default="/etc/dhcpcd.conf", help="Path to dhcpcd.conf")
    parser.add_argument("-s", "--ssh", type=str, help="Set a static ip for ssh-ing")
    parser.add_argument("-S", "--ssh_interface", default="eth1", type=str, help="Network interface for ssh")
    parser.add_argument("-b", "--baseband", type=str, help="Set a static ip for reading baseband")
    parser.add_argument("-B", "--baseband_interface", default="eth0", type=str, help="Network interface for baseband")
    args=parser.parse_args()

    i=0
    bak_path=args.path+".bak"
    while os.path.isfile(bak_path):
        i=i+1
        bak_path=args.path+".bak.%d"%(i)
    print("Making copy of %s to %s"%(args.path, bak_path))
    subprocess.call(["cp", args.path, bak_path])
    
    with open(args.path, "a") as dhcpcd:
        if args.ssh!=None:
            print("Writing ssh-ing IP address to %s"%(args.path))
            dhcpcd.write("\n")
            dhcpcd.write("############### Static IP configuration for ssh-ing ###############\n")
            ssh_rdn=args.ssh[:args.ssh.rfind(".")+1]+"1"
            dhcpcd.write("interface %s\n"%(args.ssh_interface))
            dhcpcd.write("static ip_address=%s/24\n"%(args.ssh))
            dhcpcd.write("#static ip6_address=fd51:42f8:caae:d92e::ff/64\n")
            dhcpcd.write("static routers=%s\n"%(ssh_rdn))
            dhcpcd.write("static domain_name_servers=%s 8.8.8.8\n"%(ssh_rdn))
            dhcpcd.write("\n")
            dhcpcd.write("# It is possible to fall back to a static IP if DHCP fails:\n")
            dhcpcd.write("# define static profile\n")
            dhcpcd.write("profile static_%s\n"%(args.ssh_interface))
            dhcpcd.write("static ip_address=%s/24\n"%(args.ssh))
            dhcpcd.write("#static routers=%s\n"%(ssh_rdn))
            dhcpcd.write("#static domain_name_servers=%s 8.8.8.8\n"%(ssh_rdn))
            dhcpcd.write("\n")
            dhcpcd.write("# fallback to static profile on %s\n"%(args.ssh_interface))
            dhcpcd.write("interface %s\n"%(args.ssh_interface))
            dhcpcd.write("fallback static_%s\n"%(args.ssh_interface))
            dhcpcd.write("###################################################################\n")
        if args.baseband!=None:
            print("Writing baseband reading IP address to %s"%(args.path))
            dhcpcd.write("\n")
            dhcpcd.write("############## Static IP configuration for baseband ###############\n")
            baseband_rdn=args.baseband[:args.baseband.rfind(".")+1]+"1"
            dhcpcd.write("interface %s\n"%(args.baseband_interface))
            dhcpcd.write("static ip_address=%s/24\n"%(args.baseband))
            dhcpcd.write("#static ip6_address=fd51:42f8:caae:d92e::ff/64\n")
            dhcpcd.write("#static routers=%s\n"%(baseband_rdn))
            dhcpcd.write("#static domain_name_servers=%s 8.8.8.8\n"%(baseband_rdn))
            dhcpcd.write("\n")
            dhcpcd.write("# It is possible to fall back to a static IP if DHCP fails:\n")
            dhcpcd.write("# define static profile\n")
            dhcpcd.write("profile static_%s\n"%(args.baseband_interface))
            dhcpcd.write("static ip_address=%s/24\n"%(args.baseband))
            dhcpcd.write("#static routers=%s\n"%(baseband_rdn))
            dhcpcd.write("#static domain_name_servers=%s 8.8.8.8\n"%(baseband_rdn))
            dhcpcd.write("\n")
            dhcpcd.write("# fallback to static profile on %s\n"%(args.baseband_interface))
            dhcpcd.write("interface %s\n"%(args.baseband_interface))
            dhcpcd.write("fallback static_%s\n"%(args.baseband_interface))
            dhcpcd.write("###################################################################\n")
