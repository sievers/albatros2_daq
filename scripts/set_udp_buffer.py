#!/usr/bin/python
import argparse
import subprocess
import os

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("path", type=str, help="Location of sysctl file")
    parser.add_argument("-rx", "--receive", type=int, help="UDP receive buffer size in bytes")
    args=parser.parse_args()

    i=0
    bak_path=args.path+".bak"
    while os.path.isfile(bak_path):
        i=i+1
        bak_path=args.path+".bak.%d"%(i)
    print("Making copy of %s to %s"%(args.path, bak_path))
    subprocess.call(["cp", args.path, bak_path])

    with open(args.path, "a") as scf:
        print("Setting udp receive buffer size to %d"%(args.receive))
        scf.write("net.core.rmem_default=%d\n"%(args.receive))
        scf.write("net.core.rmem_max=%d\n"%(args.receive))
