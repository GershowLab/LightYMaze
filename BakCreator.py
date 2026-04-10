import numpy as np
import cv2
from threading import Lock


class BakCreator:
    _lock: Lock

    def __init__(self, stacklen, bgim):
        self._stack_len = stacklen
        self._last_update_time = -1000
        self._last_update_frame = -1000
        self._update_frame_interval = -1
        self._update_time_interval = -1
        self._lock = Lock()
        self._bgim = bgim
        self._fgim = bgim
        self._bsub = cv2.createBackgroundSubtractorMOG2(history=stacklen, varThreshold=60, detectShadows=False)
        self._bsub.apply(bgim,1) #reset to bgim
        self._nupdates = 0

    def set_threshold(self, thresh):
        self._bsub.setVarThreshold(thresh)

    def set_update_intervals(self, update_frame_interval=None, update_time_interval=None):
        if update_frame_interval is not None:
            self._update_frame_interval = update_frame_interval
        if update_time_interval is not None:
            self._update_time_interval = update_time_interval

    #

    def _update(self, new_im, frame_num=None, frame_time=None):
        updatebg = True
        if (frame_num is not None) and (self._update_frame_interval > 0) and (
                frame_num - self._last_update_frame < self._update_frame_interval):
            updatebg = False
        if (frame_time is not None) and (self._update_time_interval > 0) and (
                frame_time - self._last_update_time < self._update_frame_interval):
            updatebg = False
        if updatebg:
            self._fgim = self._bsub.apply(new_im)
            self._nupdates += 1
        else:
            self._fgim = self._bsub.apply(new_im, learningRate=0)

        if frame_num is not None:
            self._last_update_frame = frame_num
        if frame_time is not None:
            self._last_update_time = frame_time

    # returns true if full complement of background images
    def update_background(self, new_im, frame_num=None, frame_time=None):
        with self._lock:
            self._update(new_im, frame_num, frame_time)
            return self._nupdates >= self._stack_len

    def get_background(self):
        return self._bgim

    def get_foreground(self):
        return self._fgim

    def get_thresholded_image(self):
        # _, fgthresh = cv2.threshold(self.get_foreground(im), thresh, 255, cv2.THRESH_BINARY)
        fgthresh = cv2.morphologyEx(self.get_foreground(), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        fgthresh = cv2.morphologyEx(fgthresh, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        return fgthresh
