import numpy as np
import cv2
from collections import deque
from threading import BoundedSemaphore


class BakCreator:
    _semaphore: BoundedSemaphore

    def __init__(self, stacklen, alpha, bgim):
        self._stack_len = stacklen
        self._alpha = alpha  # alpha = percent change
        self._bgim = bgim  # initialize bgim with initial background image
        self._Ims = FIFO(self._stack_len, 'Ims')  # stack of images used to create background
        self._Tims = FIFO(10,
                         'Tims')  # thresholded images - used to detect periods of no motion so background does not update
        self._updatetime = 0
        self._semaphore = BoundedSemaphore(1)

    def _or_stack(self, stack):
        if stack:
            if len(stack) == 1:
                print("Premature Stack")
                return stack[0]
            else:
                a = stack[0]
                for i in range(len(stack) - 1):
                    or_i = cv2.bitwise_or(a, stack[i + 1])
                    a = or_i
                return or_i
        else:
            print("Problem wih orStack: input stack is empty")

    # def makeORStack(self):
    #     self._timsOR = self.orStack(self._Tims)
    #     print("Initial OR stack created")

    def _update(self, newIm, fgthresh):
        self._Ims.add(newIm)
        self._Tims.add(fgthresh)
        if self._Ims.loading == False:
            self._bgim = np.median(self._Ims.stack, axis=0).astype(dtype=np.uint8)

    def updageBackground(self, newIm, fgthresh):
		if (self._semaphore.acquire(blocking=False)):
			if self._Tims.loading:
				self._Tims.add(fgthresh)
			else:
				self._timsOR = self._or_stack(self._Tims.stack)
				numNewPix = cv2.countNonZero(cv2.bitwise_and(fgthresh, cv2.bitwise_not(self._timsOR)))
				if numNewPix > (self._alpha * cv2.countNonZero(fgthresh)):
					self._update(newIm, fgthresh)
					self._updatetime = 0
				else:
					self._updatetime += 1
			self._semaphore.release()

	def getBackground(self: object) -> object:
        return self._bgim


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
