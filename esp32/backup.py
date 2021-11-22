from uosc.client import Bundle, Client, create_message
from uosc.server import run_server
import network

# ADDRESS = "0.0.0.0"
ADDRESS = "192.168.1.104"
PORT = 9001

#run_server(wlan.ifconfig()[0] , PORT)

# from led_control import rgbw,rgb,hsl,off
# import time
# for saturation_i in range(10):
#     for hue_i in range(100):
#         hsl(hue_i / 100.0, saturation_i / 10.0, 0.5)
#         print(hue_i, "%,", saturation_i, "%")
#         time.sleep_ms(100)
#     off()
#     

# run_server(ADDRESS, PORT)

osc_client = Client('192.168.1.100', 9001)
osc_client.send('/controls/frobnicator', 42, 3.1419)

run_server(wlan.ifconfig()[0], 9000)


