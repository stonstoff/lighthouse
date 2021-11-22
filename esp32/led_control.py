from machine import Pin, PWM

pin_blue = Pin(13)
pin_red =Pin(12)
pin_green = Pin(10)
pin_white = Pin(11)

pwm_blue = PWM(pin_blue)
pwm_red = PWM(pin_red)
pwm_green = PWM(pin_green)
pwm_white = PWM(pin_white)


def init_pwm():
    pwm_blue.freq(1000)
    pwm_red.freq(1000)
    pwm_green.freq(1000)
    pwm_white.freq(1000)
    pwm_blue.duty(0)
    pwm_red.duty(0)
    pwm_green.duty(0)
    pwm_white.duty(0)
    

def rgbw(r,g,b,w,brightness):
    r = r * brightness
    g = g * brightness
    b = b * brightness
    w = w * brightness
    pwm_blue.duty(int(b * 1023.0))
    pwm_red.duty(int(r * 1023.0))
    pwm_green.duty(int(g * 1023.0))
    pwm_white.duty(int(w * 1023.0))
   
   
def rgb(r,g,b,brightness):
    maxv = max(r,g,b)
    if maxv == 0:
        rgbw(0,0,0,0)
    else:
        multiplier = 1.0/maxv
        hr = r * multiplier
        hg = g * multiplier
        hb = b * multiplier
        M = max(hr, max(hg, hb))
        m = min(hr, min(hg,hb))
        luminance = ((M + m) / 2.0 - 0.5) * (2.0 / multiplier)
        rgbw(r - luminance, g - luminance, b - luminance, luminance, brightness)
        
        
def hsl(h,s,l):
    #https://stackoverflow.com/a/9493060
    r = 0.0
    g = 0.0
    b = 0.0
    if s == 0:
        r = l
        g = l
        b = l
        rgb(r,g,b)
    else:
        def hue2rgb(p,q,t):
            if t < 0:
                t+= 1
            if t > 1:
                t -= 1
            if t < 1.0/6.0:
                return p + (q - p) * 6.0 * t
            if t < 0.5:
                return q
            if t < 2.0/3.0:
                return p + (q - p) * ((2.0 / 3.0) - t) * 6
            return p
        
        q = 0
        if l < 0.5:
            q = l * (1.0 + s)
        else:
            q = l + s - (l * s)
        p = 2.0 * l - q
        r = hue2rgb(p,q,h + (1.0/3.0))
        g = hue2rgb(p,q,h)
        b = hue2rgb(p, q, h - (1.0/3.0))
        # TODO: brightness for hsl color model
        rgb(r,g,b,1)
     
     
def off():
    pwm_blue.duty(0)
    pwm_red.duty(0)
    pwm_green.duty(0)
    pwm_white.duty(0)