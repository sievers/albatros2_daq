import argparse
import ConfigParser
import logging

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("-c", "--configfile", type=str, default="albatros2_config.ini", help="Config file with all the paramenters")
    args=parser.parse_args()
    config_file=ConfigParser.SafeConfigParser()
    config_file.read(args.configfile)
    logger=logging.getLogger("albatros2_dump_auto_cross_spectra")
    logger.setLevel(logging.INFO)
    
