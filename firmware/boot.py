# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)

import network
import ubinascii

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

the_ssid = "DISSIZIT"
the_passwd = "lisboapw"

print("Connecting to Wifi")
wlan.connect(the_ssid, the_passwd)
while not wlan.isconnected():
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
