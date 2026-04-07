from lightcontroller import LightController

lc = LightController()
lc.test_leds(0.1)
for m in range(27):
    lc.set_led_direct(m,255,255,255,100)

lc.update_leds()