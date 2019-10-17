import albatrosdigitizer
import ConfigParser
import logging

logger=logging.getLogger("albatros2_config_fpga")
logger.setLevel(logging.INFO)


configfile = 'config.ini' # HARDCODED config file name
config_file=ConfigParser.SafeConfigParser()
config_file.read(configfile)
    
snap_ip=config_file.get("albatros2", "snap_ip")
snap_port=int(config_file.get("albatros2", "snap_port"))

albatros_snap=albatrosdigitizer.AlbatrosDigitizer(snap_ip, snap_port, logger)
adc_stats=albatros_snap.get_adc_stats()
print("ADC bits used: (adc0, %.2f) (adc3, %.2f)"%(adc_stats["adc0"]["bits_used"], adc_stats["adc3"]["bits_used"]))
