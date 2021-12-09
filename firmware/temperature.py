from machine import mem32
import time

def read_temperature():
    # all addresses from https://www.espressif.com/sites/default/files/documentation/esp32-s2_technical_reference_manual_en.pdf
    # page 826 and surrounding
    PERIBUS2_RTC_PERI = const(0x60008800)
    SENS_SAR_TSENS_CTRL_REG = const(PERIBUS2_RTC_PERI + 0x50)
    SENS_SAR_TSENS_CTRL2_REG = const(PERIBUS2_RTC_PERI + 0x54)
    
    SENS_TSENS_OUT = const(0xFF)
    SENS_TSENS_POWER_UP = const(1<<22)
    SENS_TSENS_POWER_UP_FORCE = const(1<<23)
    SENS_TSENS_READY = const(1<<8)
    SENS_TSENS_DUMP_OUT = const(1<<24)
    SENS_TSENS_RESET = const(1<<16)
    
    SENS_TSENS_CLKGATE_EN = const(1<<15)
    
    #1. Make sure, the clock is enabled
    if not (mem32[SENS_SAR_TSENS_CTRL2_REG] & SENS_TSENS_CLKGATE_EN > 0):
        print("Temperature sensor clock is disabled, enabling")
        mem32[SENS_SAR_TSENS_CTRL2_REG] |= SENS_TSENS_CLKGATE_EN
    
    #2. Power up the sensor
    mem32[SENS_SAR_TSENS_CTRL_REG] |= SENS_TSENS_POWER_UP
    mem32[SENS_SAR_TSENS_CTRL_REG] |= SENS_TSENS_POWER_UP_FORCE
    
    # 2. Wait for "a while" (esp32-s2 technical reference manual p.818)
    time.sleep_ms(50)
    
    #3. Set "dump out" register
    mem32[SENS_SAR_TSENS_CTRL_REG] |= SENS_TSENS_DUMP_OUT
    
    
    #4. Wait for SENS_TSENS_READY
    retries = 5
    while not (mem32[SENS_SAR_TSENS_CTRL_REG] & SENS_TSENS_READY > 0):
        print("Waiting for SENS_TSENS_READY")
        retries -= 1
        time.sleep_ms(10)
        if retries < 1:
            break;
    
    #5. Read result
    result = mem32[SENS_SAR_TSENS_CTRL_REG] & SENS_TSENS_OUT
    #print("Raw result: " + str(result))
    
    #6. Reset temperature sensor
    mem32[SENS_SAR_TSENS_CTRL_REG] &= ~SENS_TSENS_DUMP_OUT
    mem32[SENS_SAR_TSENS_CTRL_REG] &= ~SENS_TSENS_POWER_UP
    mem32[SENS_SAR_TSENS_CTRL_REG] &= ~SENS_TSENS_POWER_UP_FORCE
    #mem32[SENS_SAR_TSENS_CTRL2_REG] &= ~SENS_TSENS_CLKGATE_EN
    mem32[SENS_SAR_TSENS_CTRL2_REG] &= ~SENS_TSENS_RESET
    
    
    #6. Convert result
    offset = 0
    temperature = 0.4386 * float(result)  - 27.88 * offset - 20.52
    
    return temperature