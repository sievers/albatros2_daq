import RPi.GPIO as GPIO
import time
import argparse

def snap_reset(cooldowntime, pin=20):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, 1)
    time.sleep(cooldowntime)
    GPIO.output(pin, 0)
    time.sleep(5) # 5 second wait time to let SNAP power up fully

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script to reset SNAP Board")
    parser.add_argument("-t", "--cooldowntime", type=float, default=10, help="Time in seconds to let SNAP Board cool before turning it back on")
    #parser.add_argument("-p", "--pin", type=int, default=20, help="RPi GPIO pin used for resetting SNAP Board")
    args = parser.parse_args()

    print("Shutting down SNAP for {} second(s).".format(args.cooldowntime))
    snap_reset(args.cooldowntime)
    print("SNAP reset complete.")
