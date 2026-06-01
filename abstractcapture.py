from abc import abstractmethod
import numpy as np

class AbstractCapture:
    def __init__(self):
        self.started = False

        self.default_bounding_box = [0,0,1024,1024]
        self.w = 1024
        self.h = 1024
        self.x0 = 0
        self.y0 = 0
        self.hflip = False
        self.vflip = True
        self._last_frame_time = 0
        self._frame_number = 0

    def autofocus_once(self):
        return True

    def focus_towards(self):
        pass

    def focus_away(self):
        pass

    def set_focus(self, lens_position):
        pass

    def move_focus(self, distance):
        pass

    def set_exposure(self, exposure = None, gain = None):
        pass

    def auto_exposure(self, enable = None):
        pass

    def brighter(self):
        pass

    def dimmer(self):
        pass

    def start(self):
        pass

    def print_metadata(self):
        pass


    def stop(self):
        pass

    def get_lens_position(self):
        return 0

    def last_frame_number_and_time(self):
        return self._frame_number, self._last_frame_time

    def capture_frame(self, channels = (2,), flush=True):
        im, ts = self.capture_color_frame(flush=flush)
        if ts > self._last_frame_time:
            self._last_frame_time = ts
            self._frame_number += 1
        ret = [im[:, :, c] for c in channels]
        ret.append(ts)
        return ret

    @abstractmethod
    def capture_color_frame(self, flush = True):
        return np.zeros((3,3,3)),0

    def focus_window(self):
        pass

    def aruco_focus_window(self):
        pass

    def reset_bounding_box(self):
        pass

    def set_bounding_box_from_im_coordinates(self, x0, y0, w, h):
        print(f"old bounding box = {(self.x0, self.y0, self.w, self.h)}")
        print(f"new bounding box im coordinates = {(x0, y0, w, h)}")

        if self.hflip:
            #image ran from x0 to x0+w
            #reversed to x0+w to x0
            #subset runs from (x0+w-x') to (x0 + w - x' - w')
            x0 = self.x0 + self.w - x0 - w
        else:
            x0 = self.x0 + x0
        if self.vflip:
            y0 = self.y0 + self.h - y0 - h
        else:
            y0 = self.y0 + y0
        self.set_bounding_box(x0, y0, w, h)

    def set_bounding_box(self, x0, y0, w, h):
        was_started = self.started
        self.w = w
        self.h = h
        self.x0 = x0
        self.y0 = y0
