import numpy as np
import cv2
from collections import deque
from threading import Lock


class BakCreator:
    _lock: Lock

    def __init__(self, stacklen, alpha, bgim):
        self._stack_len = stacklen
        self._alpha = alpha  # alpha = percent change
        self._bgim = bgim  # initialize bgim with initial background image
        self._Ims = FIFO(self._stack_len, 'Ims')  # stack of images used to create background
        self._Tims = FIFO(10,
                         'Tims')  # thresholded images - used to detect periods of no motion so background does not update
        self._updatetime = 0
        self._lock = Lock()

    def _or_stack(self, stack):
        a = stack[0].copy()
        for i in range(1,len(stack)):
            a = cv2.bitwise_or(a,stack[i],a)
        return a

    def _update(self, newIm, fgthresh = None, larvathresh = None):
        if larvathresh is not None:
            li = cv2.morphologyEx(larvathresh, cv2.MORPH_DILATE, np.ones((5, 5), np.uint8)) > 0
            ni = newIm.copy()
            ni[li] = self._bgim[li]
            self._Ims.add(ni)
        else:
            self._Ims.add(newIm)
        if not (fgthresh is None):
            self._Tims.add(fgthresh)
        self._bgim = np.min(self._Ims.stack, axis=0).astype(dtype=np.uint8) #changed from median to min
        self._updatetime = 0

    def _check_thresh_movement(self, fgthresh = None):
        if fgthresh is None:
            return True #do update
        if self._Tims.loading:
            return True #change from previous behavior where bg was not updated until tims loaded
        tmask = self._or_stack(self._Tims.stack) # or of recently added thresholded images
        nnz = 0
        for ti in self._Tims.stack:
            nnz += cv2.countNonZero(ti)
        nnz /= len(self._Tims.stack)
        nnew = cv2.countNonZero(cv2.bitwise_and(cv2.bitwise_not(tmask), fgthresh))
        return nnew >= self._alpha*nnz
    def update_background(self, newIm, fgthresh = None, larvathresh = None):
        with self._lock:
            if self._check_thresh_movement(fgthresh):
                self._update(newIm, fgthresh, larvathresh)
            else:
                self._updatetime += 1
    def get_background(self):
        return self._bgim
    def get_foreground(self, im):
        return cv2.subtract(im, self.get_background())
    def get_thresholded_image(self, im, thresh):
        _, fgthresh = cv2.threshold(self.get_foreground(im), thresh, 255, cv2.THRESH_BINARY)
        fgthresh = cv2.morphologyEx(fgthresh, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        fgthresh = cv2.morphologyEx(fgthresh, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        return fgthresh
class FIFO:
    def __init__(self, maxlength, name):
        self.maxlength = maxlength
        self.name = name
        self.stack = deque()
        self.loading = True

    def getLength(self):
        return len(self.stack)

    def add(self, im):
        length = self.getLength()
        if length < self.maxlength:
            self.stack.append(im)
        else:
            self.loading = False
            self.stack.popleft()
            self.stack.append(im)
