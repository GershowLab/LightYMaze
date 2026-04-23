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
        self._fgim = np.zeros_like(bgim)
        self._bsub = cv2.createBackgroundSubtractorMOG2(history=stacklen, varThreshold=60, detectShadows=False)
        self._bsub.setBackgroundRatio(0.1)
      #  self._bsub.setNMixtures(5)
        self._bsub.apply(bgim,1) #reset to bgim
        self._learning_rate = -1
        self._nupdates = 0
        self._tims = CircularBuffer(4,np.zeros_like(bgim))
        self._alpha = 0.1
        self._exclude_larva_from_update = True
        self._bg_was_updated = False
        self._debug = False

    def set_threshold(self, thresh):
        self._bsub.setVarThreshold(thresh)

    def set_update_intervals(self, update_frame_interval=None, update_time_interval=None):
        if update_frame_interval is not None:
            self._update_frame_interval = update_frame_interval
        if update_time_interval is not None:
            self._update_time_interval = update_time_interval

    def largest_contour(self):
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            self._fgim, connectivity=8
        )
        if num_labels < 2:
            return self._fgim
        area = [stats[i, cv2.CC_STAT_AREA] for i in range(1, num_labels)]
        larva_ind = np.argmax(area) + 1
        return cv2.morphologyEx((labels == larva_ind).astype(np.uint8) * 255, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=10)

    def _update(self, new_im, frame_num=None, frame_time=None):
        new_im = cv2.blur(new_im, (3,3))
        updatebg = True
        if (frame_num is not None) and (self._update_frame_interval > 0) and (
                frame_num - self._last_update_frame < self._update_frame_interval):
            updatebg = False
        if (frame_time is not None) and (self._update_time_interval > 0) and (
                frame_time - self._last_update_time < self._update_frame_interval):
            updatebg = False
        updatebg = self._check_thresh_movement() and updatebg
        if updatebg:
            lr = self._learning_rate
            self._nupdates += 1
            if frame_num is not None:
                self._last_update_frame = frame_num
            if frame_time is not None:
                self._last_update_time = frame_time
        else:
            lr = 0
        if self._exclude_larva_from_update and self._nupdates > 1:
            self._fgim = self._bsub.apply(new_im, learningRate=lr, fgmask=self.largest_contour())
        else:
            self._fgim = self._bsub.apply(new_im, learningRate=lr)

        fgbrighter = cv2.morphologyEx(cv2.compare(new_im, self.get_background(), cv2.CMP_GE).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=5)
        self._fgim = cv2.bitwise_and(self._fgim, fgbrighter, self._fgim)
        self._fgim = cv2.morphologyEx(self._fgim, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        self._fgim = cv2.morphologyEx(self._fgim, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=3)

        self._bg_was_updated = updatebg


    # returns true if minimum number of threshold images have been collected
    def update_background(self, new_im, frame_num=None, frame_time=None):
        with self._lock:
            self._update(new_im, frame_num, frame_time)
            return self._tims.full()

    def get_background(self):
        return self._bsub.getBackgroundImage()

    def get_foreground(self):
        return self._fgim

    def get_thresholded_image(self):
        return self.get_foreground()

    def _check_thresh_movement(self):
        if self._fgim is None:
            return True #do update
        if not self._tims.full():
            self._tims.add(self._fgim)
            return True
        t_mask = np.asarray(255*np.any(self._tims.get_stack(), axis=0), np.uint8)
        nnz = np.count_nonzero(self._tims.get_stack())/self._tims.get_stack().shape[0]
        num_new = np.count_nonzero(cv2.bitwise_and(cv2.bitwise_not(t_mask), self._fgim))
        new_t = num_new >= self._alpha*nnz
        if self._debug:

            cv2.imshow("fgoverlay", cv2.merge((np.asarray(t_mask, np.uint8), self._fgim, self._fgim)))
            st = self._tims.get_stack()
            for j in range(st.shape[0]):
                cv2.imshow(f"threshim {j}", st[j,:, :])
            print(f"nnz: {nnz}, num_fg: {cv2.countNonZero(self._fgim)} num_new: {num_new}, new_t: {new_t}, tims_full : {self._tims.full()}")
        if new_t:
            self._tims.add(self._fgim)
        return new_t

class CircularBuffer:
    def __init__(self, length, init_data):
        imsize = init_data.shape
        dtype = init_data.dtype
        self.storage = np.zeros((length, *imsize), dtype=dtype)
        for j in range(length):
            self.storage[j] = init_data
        self._length = length
        self._current_ind = 0
        self._num_ims = 0

    def full(self):
        return self._num_ims >= self._length


    def add(self, im):
        self._num_ims = np.max((self._num_ims, self._current_ind+1))
        self.storage[self._current_ind] = im
        self._current_ind = (self._current_ind + 1)%self._length

    def get_element(self, ind):
        return self.storage[(ind + self._current_ind)%self._length]

    def get_nth_most_recent_element(self, n):
        return self.storage[(self._current_ind - 1 -n)%self._length]

    def get_stack(self):
        return self.storage[:self._num_ims]