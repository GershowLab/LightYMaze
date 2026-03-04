from apa102_pi.driver import apa102
import threading
class LightController:
    def __init__(self):
        self.num_mazes = 9
        self.strip = apa102.APA102(num_led=3*self.num_mazes, global_brightness=9)
        self.semaphore = threading.Semaphore(1)

    def set_led(self, maze_num, channel_num, red, green, blue, bright_pct = 100):
        with self.semaphore:
            self.strip.set_pixel(3*maze_num+channel_num,red, green, blue, bright_percent=bright_pct)

    def update_leds(self):
        with self.semaphore:
            self.strip.show()
    


