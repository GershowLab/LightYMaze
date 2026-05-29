from abstractcapture import AbstractCapture
import cv2

class VideoCapture(AbstractCapture):
    def __init__(self, fname, frame_delta_time = 0.5):
        super().__init__()
        self._vc = cv2.VideoCapture(str(fname)) #TODO correct for mp4
        ret, frame = self._vc.read()
        self.h, self.w = frame.shape[:2]
        self.default_bounding_box = (0, 0, self.w, self.h)
        self._frame_dt = frame_delta_time

    def capture_color_frame(self, flush = True):
        ret, frame = self._vc.read()
        self._frame_number = self._frame_number + 1
        self._last_frame_time = self._last_frame_time + self._frame_dt
        if self.hflip and self.vflip:
            im = frame[self.h - 1::-1, self.w - 1::-1, :]
        else:
            if self.hflip:
                im = frame[:self.h, self.w - 1::-1, :]
            else:
                if self.vflip:
                    im = frame[self.h - 1::-1, :self.w, :]
                else:
                    im = frame[:self.h, :self.w, :]
        return im, self._last_frame_time