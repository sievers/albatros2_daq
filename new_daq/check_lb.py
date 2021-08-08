import lbtools_l

if __name__ == "__main__":
    if lbtools_l.lb_set():
        gps_data = lbtools_l.lb_read()
        ctime = gps_data[0]
        gpsloc = gps_data[1][2:] # GPS location
        htime = str(gps_data[2]) # human-readable time
        print("GPS time: "+htime)
        print("Timestamp: {}".format(ctime))
        print("Latitude: {}".format(gpsloc[1]))
        print("Longitude: {}".format(gpsloc[0]))
        print("Elevation: {}".format(gpsloc[2]))
        if gps_data[1][1][-4:][1] == '0':
            print("WARNING: GPS location is not reliable.")
        if gps_data[1][1][-4:][2] == '0' or gps_data[1][1][-4:][3] == '0':
            print("WARNING: GPS time and date is not reliable.")
    else:
        print("Something went wrong.")
