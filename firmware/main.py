import network
import logging
import socket
import time
import esp32
import machine
from ota_updater import OTAUpdater
from HttpOTA import HttpOTA
import senko
import uota
import sys


# TODO firmware update
#otaUpdater = OTAUpdater('https://github.com/stonstoff/lighthouse')
#print(otaUpdater.get_latest_version())
#otaUpdater.install_update_if_available()
#if (otaUpdater.check_for_update_to_install_during_next_reboot()):
#    machine.reset()
#otaUpdater.check_for_update_to_install_during_next_reboot()
#otaUpdater.install_update_if_available()
#print(otaUpdater._check_for_new_version())


# httpOta = HttpOTA("esp32", base_url="https://github.com/stonstoff/lighthouse/esp32")




debug=True

from uosc.client import Bundle, Client, create_message
from led_control import rgbw,rgb,hsl,off

from activity import activity

import temperature
import calibration
import ujson

FIRMWARE_VERSION = -1
with open('version','r') as file:
    FIRMWARE_VERSION = file.read().strip()


# that's me
OSC_CLIENT_IP = wlan.ifconfig()[0]
OSC_CLIENT_PORT = 9001

# Audio Lab OSCbroadcaster
OSC_SERVER_IP = "149.222.206.225"
OSC_SERVER_PORT = 9000



BASE_PATTERN = "/lighthouse"

my_ip = OSC_CLIENT_IP
my_mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
my_location = [-1,-1]
my_brightness = 1.0

try:
    from ustruct import unpack
except ImportError:
    from struct import unpack

from uosc.common import Impulse, to_time

if debug:
    from uosc.socketutil import get_hostport

log = logging.getLogger("lighthouse_server")
MAX_DGRAM_SIZE = 1472


def lookup_position():
    # https://forum.micropython.org/viewtopic.php?t=1969
    global my_location
    with open('ip-location.csv','r') as file:
        for line in file:
            line=line.rstrip('\n')
            line=line.rstrip('\r')
            ip_pos = line.split(',')
            if ip_pos[0] == my_ip:
                my_location = [int(ip_pos[1]),int(ip_pos[2])]
    if my_location[0] > -1:
        print("My Position x:%d, y:%d" % (my_location[0]
                                          ,my_location[1])
              )
        return True
    else:
        print("IP for LED Position not found.")
        return False


def limit_value(v):
    return float(min(max(v, 0.0), 1.0))


def split_oscstr(msg, offset):
    end = msg.find(b'\0', offset)
    return msg[offset:end].decode('utf-8'), (end + 4) & ~0x03


def split_oscblob(msg, offset):
    start = offset + 4
    size = unpack('>I', msg[offset:start])[0]
    return msg[start:start + size], (start + size + 4) & ~0x03


def parse_timetag(msg, offset):
    """Parse an OSC timetag from msg at offset."""
    return to_time(unpack('>II', msg[offset:offset + 4]))


def parse_message(msg, strict=False):
    args = []
    addr, ofs = split_oscstr(msg, 0)

    if not addr.startswith('/'):
        raise ValueError("OSC address pattern must start with a slash.")

    # type tag string must start with comma (ASCII 44)
    if ofs < len(msg) and msg[ofs:ofs + 1] == b',':
        tags, ofs = split_oscstr(msg, ofs)
        tags = tags[1:]
    else:
        errmsg = "Missing/invalid OSC type tag string."
        if strict:
            raise ValueError(errmsg)
        else:
            log.warning(errmsg + ' Ignoring arguments.')
            tags = ''

    for typetag in tags:
        size = 0

        if typetag in 'ifd':
            size = 8 if typetag == 'd' else 4
            args.append(unpack('>' + typetag, msg[ofs:ofs + size])[0])
        elif typetag in 'sS':
            s, ofs = split_oscstr(msg, ofs)
            args.append(s)
        elif typetag == 'b':
            s, ofs = split_oscblob(msg, ofs)
            args.append(s)
        elif typetag in 'rm':
            size = 4
            args.append(unpack('BBBB', msg[ofs:ofs + size]))
        elif typetag == 'c':
            size = 4
            args.append(chr(unpack('>I', msg[ofs:ofs + size])[0]))
        elif typetag == 'h':
            size = 8
            args.append(unpack('>q', msg[ofs:ofs + size])[0])
        elif typetag == 't':
            size = 8
            args.append(parse_timetag(msg, ofs))
        elif typetag in 'TFNI':
            args.append({'T': True, 'F': False, 'I': Impulse}.get(typetag))
        else:
            raise ValueError("Type tag '%s' not supported." % typetag)

        ofs += size

    return (addr, tags, tuple(args))


def parse_bundle(bundle, strict=False):
    """Parse a binary OSC bundle.

    Returns a generator which walks over all contained messages and bundles
    recursively, depth-first. Each item yielded is a (timetag, message) tuple.

    """
    if not bundle.startswith(b'#bundle\0'):
        raise TypeError("Bundle must start with b'#bundle\\0'.")

    ofs = 16
    timetag = to_time(*unpack('>II', bundle[8:ofs]))

    while True:
        if ofs >= len(bundle):
            break

        size = unpack('>I', bundle[ofs:ofs + 4])[0]
        element = bundle[ofs + 4:ofs + 4 + size]
        ofs += size + 4

        if element.startswith(b'#bundle'):
            for el in parse_bundle(element):
                yield el
        else:
            yield timetag, parse_message(element, strict)


def handle_osc(data, src, dispatch=None, strict=False):
    try:
        head, _ = split_oscstr(data, 0)

        if head.startswith('/'):
            messages = [(-1, parse_message(data, strict))]
        elif head == '#bundle':
            messages = parse_bundle(data, strict)
    except Exception as exc:
        if debug:
            log.debug("Could not parse message from", src, exc)
            log.debug("Data: %r", data)
        return

    try:
        for timetag, (oscaddr, tags, args) in messages:
            
            addr_pattern = oscaddr.split('/')
            if (addr_pattern[1] == "lighthouse"):
                #
                # addressed to all lights
                if not args: 
                    if addr_pattern[2] == "status":
                        send_message("ready", 1)
                    elif addr_pattern[2] == "update":
                        send_message("firmware", firmware_update())
                    elif addr_pattern[2] == "temperature":
                        send_message("celsius", temperature.read_temperature())
                    elif addr_pattern[2] == "brightness":
                        send_message("adc", calibration.measure_light_median())
                    elif addr_pattern[2] == "calibrate":
                        send_message("adc", ujson.dumps(calibration.calibrate()))
                    elif addr_pattern[2] == "firmware":
                        send_message("version", FIRMWARE_VERSION)
                    elif addr_pattern[2] == "off":
                        off()
                    elif addr_pattern[2] == "restart":
                        send_message("ready", 0)
                        machine.reset()
                        
                #                        
                # addressed only to me
                elif is_my_location(addr_pattern[2]):
                    if args[0] == "off":
                        off()
                    elif args[0] == "network":
                        send_message("mac", my_mac)
                        send_message("ip", my_ip)
                    else:                    
                        # set light
                        the_red = float(args[0]/255)
                        the_green = float(args[1]/255)
                        the_blue = float(args[2]/255)
                        print(the_red, the_green, the_blue)
                        rgb(limit_value(the_red)
                            , limit_value(the_green)
                            , limit_value(the_blue)
                            , limit_value(my_brightness)
                            )
                    
            
            if debug:
                log.debug("OSC address: %s" % oscaddr)
                log.debug("OSC type tags: %r" % tags)
                log.debug("OSC arguments: %r" % (args,))

            if dispatch:
                dispatch(timetag, (oscaddr, tags, args, src))
    except Exception as exc:
        log.error("Exception in OSC handler: %s", exc)


def run_server(saddr, port, handler=handle_osc):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if debug: log.debug("Created OSC UDP server socket.")

    sock.bind((saddr, port))
    log.info("Listening for OSC messages on %s:%i.", saddr, port)

    try:
        while True:
            data, caddr = sock.recvfrom(MAX_DGRAM_SIZE)
            if debug: log.debug("RECV %i bytes from %s:%s",
                                    len(data), *get_hostport(caddr))
            activity()
            handler(data, caddr)
    except:
        log.debug("Something went wrong")
        
    finally:
        sock.close()
        log.info("Bye!")


def send_message(sub_pattern, arg):
    osc_client.send(BASE_PATTERN +'/'+sub_pattern
                    , my_location[0]
                    , my_location[1]
                    , arg
                    )
    
    
def firmware_update():
    if uota.check_for_updates(version_check=False):
        send_message("ready", 0)        
        uota.install_new_firmware()
        machine.reset()
    else:
        print("nothing to do")
    

def is_my_location(location_pattern):
    # skip substring 'light'
    location_pattern = location_pattern.split("light")
    if location_pattern[0] == "":
        location_pattern = location_pattern[1].split("x")
        location_pattern = location_pattern[1].split("y")
        x_pos = int(location_pattern[0])
        y_pos = int(location_pattern[1])
        if (x_pos == my_location[0]) and (y_pos == my_location[1]):
            return True
        else:
            # not my position
            return False
    else:
        # not light' addressed
        return False
    
def green_on_ready():
    rgb(0,1,0,0.3)
    time.sleep_ms(1000)
    off()
    
    
def red_on_error():
    while True:
        rgb(1,0,0,0.3)
        time.sleep_ms(200)
        off()
        time.sleep_ms(200)   

def yellow_on_error():
    while True:
        rgb(1,1,0,0.3)
        time.sleep_ms(200)
        off()
        time.sleep_ms(200)
        

osc_client = Client(OSC_SERVER_IP, OSC_SERVER_PORT)

if not wlan.isconnected():
    yellow_on_error()
elif not lookup_position():
    send_message("ready", 0)
    red_on_error()
else:     
    send_message("ready", 1)
    green_on_ready()
    
# keepalive ping
from machine import Timer
keepalive_timer = Timer(1)
from micropython import schedule
keepalive_timer.init(period=5000, mode=Timer.ONE_SHOT, callback=lambda t: schedule(keepalive_callback,1))
def keepalive_callback(first):
    temp_deg_c = temperature.read_temperature()
    send_message("keepalive_temp_c",temp_deg_c)
    print("Keepalive Temperature: " + str(temp_deg_c))
    keepalive_timer.init(period=5000, mode=Timer.ONE_SHOT, callback=lambda t: schedule(keepalive_callback,0))

run_server(OSC_CLIENT_IP, OSC_CLIENT_PORT, handle_osc)


# from led_control import rgbw,rgb,hsl,off
# 
# for saturation_i in range(10):
#     for hue_i in range(100):
#         hsl(hue_i / 100.0, saturation_i / 10.0, 0.5)
#         print(hue_i, "%,", saturation_i, "%")
#         time.sleep_ms(100)
#     off()
#     

