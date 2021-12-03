# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)

import network
import ubinascii
from activity import init_activity, activity
import time
import calibration
import temperature

init_activity()

if not calibration.load_calibration():
    print("No calibration found, calibrating")
    calibration.calibrate()

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
#new_mac = b'\x4e\xe8\x73\x7b\xb8\x66'
#print("New mac len:" + str(len(new_mac)))
#wlan.config('mac'=new_mac)
print("My mac: " + ubinascii.hexlify(wlan.config('mac')).decode())
print("My temperature: " + str(temperature.read_temperature()))

wlan.active(True)
SSID = "SSID"
PASS = "password" 
with open("wifi_credentials") as wifi_credentials:
    lines = wifi_credentials.readlines()
    SSID = lines[0].strip()
    PASS = lines[1].strip()
    
print("Connecting to Wifi " + SSID)
wlan.connect(SSID, PASS)
while not wlan.isconnected():
    activity()
    time.sleep_ms(250)
    pass


# print("Network config:", wlan.ifconfig())
print("My IP:", wlan.ifconfig()[0])
mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
print("My MAC:", mac);

### start access point
# ap = network.WLAN(network.AP_IF)
# ap.config(essid="KIELerLEUCHTEN", password="kiel")
# ap.active(True)
# print("Network config:", ap.ifconfig())

# import webrepl
# webrepl.start()

