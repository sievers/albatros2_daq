# Add this to ~/albatros2_daq/new_daq/ on RPi
import trimble_utils
import argparse
import sys
import datetime

if __name__ == "__main__":
	gps_time = trimble_utils.get_gps_timestamp_trimble()
	if gps_time is None:
		sys.exit()
	else:
		htime = str(datetime.datetime.utcfromtimestamp(gps_time))
		print('GPS time: '+htime+', (timestamp: {:d})'.format(int(gps_time))) 

	latlon = trimble_utils.get_latlon_trimble()
	if latlon is None:
		sys.exit()
	else:
		print('Latitude: {}, Longitude: {}, Elevation: {}'.format(latlon['lat'], latlon['lon'], latlon['elev']))
