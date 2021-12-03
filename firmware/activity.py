from machine import Pin, Timer
from micropython import schedule
# set up status LED
pin_status = Pin(8, Pin.OUT)
status_timer = Timer(0)
status_led = 0
status_next = 0
DISABLED = False

def init_activity():
    print("Initializing status LED")
    global status_led
    global status_next
    status_led = 0
    status_next = 0 
    status_timer.init(period=500, mode=Timer.ONE_SHOT, callback=lambda t: schedule(status_callback,1))

def status_callback(first):
    global DISABLED
    global status_led
    global status_next
    if not DISABLED:
        if status_led == 1:
            pin_status.off()
            status_led = 0
        else:
            if status_next == 1:
                status_led = 1
                pin_status.on()
                status_next = 0
    else:
        status_led = 0
        status_next = 0
    status_timer.init(period=500, mode=Timer.ONE_SHOT, callback=lambda t: schedule(status_callback,0))
        
def activity():
    global status_next
    status_next = 1
