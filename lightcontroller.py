from time import sleep
try:
    from apa102_pi.driver import apa102
    import threading
    class LightController:
        def __init__(self):
            self.num_mazes = 9
            self.strip = apa102.APA102(num_led=3*self.num_mazes, global_brightness=9)
            self.lock = threading.Lock()

        def set_global_brightness(self, global_brightness):
            self.strip.set_global_brightness(global_brightness)

        #maze num is 1 to 9; not 0 to 8
        def set_led(self, maze_num, channel_num, red, green, blue, bright_pct = 100):
            with self.lock:
                self.strip.set_pixel(3*(maze_num-1)+channel_num,red, green, blue, bright_percent=bright_pct)
                print(f"{maze_num}, {channel_num}: {red},{green},{blue}")

        def update_leds(self):
            with self.lock:
                self.strip.show()

        def test_leds(self, timeout = 0.1):
            for m in range(self.num_mazes):
                for c in range(3):
                    self.set_led(m, c, 0, 0, 255)
                    self.update_leds()
                    sleep(timeout)
                    self.set_led(m, c, 255, 0, 0)
                    self.update_leds()
                    sleep(timeout)
                    self.update_leds()
                    self.set_led(m, c, 0, 255, 0)
                    self.update_leds()
                    sleep(timeout)
                    self.set_led(m, c, 0, 0, 0)
            self.update_leds()

except:
    class LightController:
        def __init__(self):
            self.num_mazes = 9

        def set_global_brightness(self, global_brightness):
            return #no op
        def set_led(self, maze_num, channel_num, red, green, blue, bright_pct=100):
            return #no op
        def update_leds(self):
            return #no op


def ledtest():
    lc = LightController()
    to = 1
    for m in range(lc.num_mazes):
        for c in range(3):
            lc.set_led(m,c,0,0,255)
            lc.update_leds()
            sleep(to)
            lc.set_led(m,c,255,0,0)
            lc.update_leds()
            sleep(to)
            lc.update_leds()
            lc.set_led(m,c,0,255,0)
            lc.update_leds()
            sleep(to)
            lc.set_led(m,c,0,0,0)
    lc.update_leds()

           

if __name__ == "__main__":
    ledtest()
