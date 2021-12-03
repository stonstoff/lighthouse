from micropython import const
from machine import Pin, ADC
import led_control
import time
import ujson
import os
import activity

activity_led_pin = const(8)

@micropython.native
def measure_light_avg(measurements=64):
    #Disable activity led
    disabled_before = activity.DISABLED
    activity.DISABLED = True
    #Setup pin
    pin = Pin(activity_led_pin, Pin.OUT)
    pin.off()
    pin = Pin(activity_led_pin, Pin.IN, Pin.PULL_UP)
    #Setup ADC
    adc = ADC(Pin(activity_led_pin))
    adc.atten(ADC.ATTN_2_5DB)
    #Take measurements
    acc = 0
    measurement_max = float(2**16)
    for i in range(measurements):
        acc += float(adc.read_u16()) / measurement_max
        time.sleep_us(10) # wait 10 us between measurements
    acc = acc / measurements
    #Reset pin to output
    pin = Pin(activity_led_pin, Pin.OUT)
    pin.off()
    activity.DISABLED = disabled_before
    #Return result
    return acc

def measure_light_median(measurements=5, timeout_period=50):
    values = []
    for i in range(measurements):
        values.append(measure_light_avg())
        time.sleep_ms(timeout_period)
    values.sort()
    return values[int(measurements/2)]

def measure_diff(channel=0, intensity=0.1, delay=100, raw=False):
    red = 1 if channel == 0 else 0
    green = 1 if channel == 1 else 0
    blue = 1 if channel == 2 else 0
    white = 1 if channel == 3 else 0
    v1 = 0
    v2 = -1
    while v2 < v1:
        led_control.off()
        time.sleep_ms(delay)
        v1 = measure_light_median()
        led_control.rgbw(red * intensity, green * intensity, blue * intensity, white * intensity)
        time.sleep_ms(delay)
        v2 = measure_light_median()
        led_control.off()
    return v2 if raw else v2-v1

def calibration_factors(step_width=0.1, raw=False):
    factors = []
    value = 0
    while value <= 1:
        leds = []
        for channel in range(4):
            leds.append(measure_diff(channel=channel, intensity=value, raw=raw))
        factors.append(leds)
        value += step_width
    #print(ujson.dumps(factors)) #useful for plotting
    return factors

def calibrate():
    # reset calibration factors in led_control
    led_control.MINIMA = [0.0,0.0,0.0,0.0]
    led_control.LINEAR = [1.0,1.0,1.0,1.0]
    #stop activity led
    activity.DISABLED = True
    #gather measurements
    step_width = 0.05
    factors = calibration_factors()
    # find maximum of first derivative in each channel
    values = [0,0,0,0]
    indices = [0,0,0,0]
    for i in range(1, len(factors)):
        for c in range(0,4):
            derivative = factors[i][c] - factors[i-1][c]
            if derivative > values[c]:
                indices[c] = i
                values[c] = derivative
    # compute calibration
    #TODO: extend this to quadratic or cubic to account for the higher efficiency at the upper end of the performance spectrum
    minima = [(indices[i] + 1) * step_width for i in range(4)]
    linear = [1.0 - minima[i] for i in range(4)]
    #set calibration factors in led_control
    led_control.MINIMA = minima
    led_control.LINEAR = linear
    #Reenable activity led
    activity.DISABLED = False
    #save calibration to file
    calibration = {
            'minima': minima,
            'linear': linear
    }
    with open("calibration.json", "w") as calibration_file:
        calibration_file.write(ujson.dumps(calibration))
    return calibration

def load_calibration():
    if "calibration.json" in os.listdir():
        with open("calibration.json") as calibration_file:
            calibration = ujson.loads(calibration_file.read())
            led_control.MINIMA = calibration["minima"]
            led_control.LINEAR = calibration["linear"]
            print("Loaded LED calibration")
        return True
    else:
        print("No LED calibration stored")
        return False