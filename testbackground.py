import cv2
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import skimage as ski

#https://opencv.org/reading-and-writing-videos-using-opencv/#h-read-an-image-sequence
basedir = Path('/Users/gershow/Library/CloudStorage/GoogleDrive-mhg4@nyu.edu/')
#basedir = Path('G:\\')
fstub = basedir / 'Shared drives' / 'ugns-larval-behavior' / 'pi5' / '2026-04-08_15-25-27' / '2026-04-08_15-25-27 maze1.mp4'

print(f"{fstub} exists? {fstub.exists()}")
vc = cv2.VideoCapture(str(fstub))


mog2 = cv2.createBackgroundSubtractorMOG2(history=60, detectShadows=False, varThreshold=60)
cap = cv2.VideoCapture(str(fstub))

for f in range(10000):
    ret, frame = vc.read()
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
  #  fg2 = ski.segmentation.morphological_chan_vese(fgmask, num_iter=100, smoothing=1)
    cv2.imshow('mog2', fgmask)

  #  cv2.imshow('knn',fgmaskknn)
    cv2.imshow('mog2-erode-dilate',cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)))


    k = cv2.waitKey(1) & 0xFF
    if k == ord('q'):
        break

vc.release()
cv2.destroyAllWindows()