import numpy as np
import cv2
from threading import Lock


class BakCreator:
    _lock: Lock

    def __init__(self, stacklen, alpha, bgim):
        self._stack_len = stacklen
        self._alpha = alpha  # alpha = percent change
        self._bgim = bgim  # initialize bgim with initial background image
        self._Ims = CircularBuffer(self._stack_len, bgim)
        self._Tims = CircularBuffer(3,np.zeros_like(bgim))  # thresholded images - used to detect periods of no motion so background does not update
        self._last_update_time = -1000
        self._last_update_frame = -1000
        self._update_frame_interval = -1
        self._update_time_interval = -1
        self._lock = Lock()
        self._mean_im = np.zeros_like(bgim)
        self._std_im = np.zeros_like(bgim)
        self._threshold = 30

    def set_update_intervals(self, update_frame_interval = None, update_time_interval = None):
        if update_frame_interval is not None:
            self._update_frame_interval = update_frame_interval
        if update_time_interval is not None:
            self._update_time_interval = update_time_interval

    # def _or_stack(self, stack):
    #     a = stack[0].copy()
    #     for i in range(1,len(stack)):
    #         a = cv2.bitwise_or(a,stack[i],a)
    #     return a

    def _update(self, new_im, fgthresh = None, larvathresh = None, frame_num = None, frame_time = None):
        if (frame_num is not None) and (self._update_frame_interval > 0) and (frame_num - self._last_update_frame < self._update_frame_interval):
            return
        if (frame_time is not None) and (self._update_time_interval > 0) and (frame_time - self._last_update_time < self._update_frame_interval):
            return
        if larvathresh is not None:
            li = cv2.morphologyEx(larvathresh, cv2.MORPH_DILATE, np.ones((5, 5), np.uint8)) > 0
            ni = new_im.copy()
            ni[li] = self._bgim[li]
            self._Ims.add(ni)
        else:
            self._Ims.add(new_im)
        if not (fgthresh is None):
            self._Tims.add(fgthresh)
        self._bgim = np.min(self._Ims.get_stack(), axis=0).astype(dtype=np.uint8) #changed from median to min
        self._mean_im = np.mean(self._Ims.get_stack(), axis=0).astype(dtype=np.uint8)  # changed from median to min
        self._std_im = np.clip(np.std(self._Ims.get_stack(), axis=0).astype(dtype=np.uint8),1,None)

        if frame_num is not None:
            self._last_update_frame = frame_num
        if frame_time is not None:
            self._last_update_time = frame_time

    def _check_thresh_movement(self, fgthresh = None):
        if fgthresh is None:
            return True #do update
        if not self._Tims.full():
            return True
        # if self._Tims.loading:
        #     return True #change from previous behavior where bg was not updated until tims loaded
        t_mask = np.any(self._Tims.get_stack(), axis=0)
        nnz = np.count_nonzero(self._Tims.get_stack())/self._Tims.get_stack().shape[0]
        num_new = np.count_nonzero(np.bitwise_and(np.bitwise_not(t_mask), fgthresh))
        return num_new >= self._alpha*nnz

    def set_threshold(self, threshold):
        self._threshold = threshold
    #returns true if full complement of background images
    def update_background(self, new_im, fg_thresh = None, larva_thresh = None, frame_num = None, frame_time = None):
        with self._lock:
            if self._Ims.full():
                fg_thresh = self.get_thresholded_image(fg_thresh)
                mc = self._check_thresh_movement(fg_thresh)
            else:
                mc = True
            if mc:
                self._update(new_im, fg_thresh, larva_thresh, frame_num, frame_time)
            return self._Ims.full()

    def get_background(self):
        return self._bgim

    def get_foreground(self, im):
        return cv2.subtract(im, self.get_background())

    def get_thresholded_image(self, im):
        _, fgthresh = cv2.threshold(self.get_foreground(im), self._threshold, 255, cv2.THRESH_BINARY)
        fgthresh = cv2.morphologyEx(fgthresh, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        fgthresh = cv2.morphologyEx(fgthresh, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        return fgthresh

    def get_zscore_image(self, im):
        return np.clip((8*(im - self._mean_im)/self._std_im).astype(np.uint8), 0, 255)


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


# class FIFO:
#     def __init__(self, maxlength, name):
#         self.maxlength = maxlength
#         self.name = name
#         self.stack = deque()
#         self.loading = True
#
#     def getLength(self):
#         return len(self.stack)
#
#     def add(self, im):
#         length = self.getLength()
#         if length < self.maxlength:
#             self.stack.append(im)
#         else:
#             self.loading = False
#             self.stack.popleft()
#             self.stack.append(im)
