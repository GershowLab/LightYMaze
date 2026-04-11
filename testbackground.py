import cv2
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import skimage as ski
from BakCreator import BakCreator

#https://opencv.org/reading-and-writing-videos-using-opencv/#h-read-an-image-sequence
basedir = Path('/Users/gershow/Library/CloudStorage/GoogleDrive-mhg4@nyu.edu/')
#basedir = Path('G:\\')
fstub = basedir / 'Shared drives' / 'ugns-larval-behavior' / 'pi5'
# datecode =  '2026-04-08_15-25-27'
# mazenum = 1
datecode = '2026-04-10_10-32-30'
mazenum = 3
fstub = fstub / datecode / f"{datecode} maze{mazenum}.mp4"
print(f"{fstub} exists? {fstub.exists()}")
vc = cv2.VideoCapture(str(fstub))


mog2 = cv2.createBackgroundSubtractorMOG2(history=60, detectShadows=False, varThreshold=30)
cap = cv2.VideoCapture(str(fstub))

ret, frame = vc.read()
bak = BakCreator(30,frame)
bak.set_threshold(30)
bak.set_update_intervals(update_time_interval=-1, update_frame_interval=10)
for f in range(20000):
    if not ret:
        print("did not open video")
        break

    if f%10 == 0:
        fgmask = mog2.apply(frame)
      #  fgmaskknn = knn.apply(frame)
    else:
        fgmask = mog2.apply(frame,learningRate=0)
       # fgmaskknn = knn.apply(frame,learningRate=0)
    print(f)
    bak.update_background(frame, frame_num=f)

  #  fg2 = ski.segmentation.morphological_chan_vese(fgmask, num_iter=100, smoothing=1)
    cv2.imshow('bak', bak.get_thresholded_image())
    fgmask = cv2.morphologyEx(cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)),
                              cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
  #  cv2.imshow('knn',fgmaskknn)
    cv2.imshow('im', frame)
    cv2.imshow('mog2-open',fgmask)


    k = cv2.waitKey(1) & 0xFF
    if k == ord('q'):
        break
    ret, frame = vc.read()

vc.release()
cv2.destroyAllWindows()