import livetracker
import cv2
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

import videocapture
from ymazegeometry import YMazeGeometry

#https://opencv.org/reading-and-writing-videos-using-opencv/#h-read-an-image-sequence
basedir = Path('/Users/gershow/Library/CloudStorage/GoogleDrive-mhg4@nyu.edu/')
#basedir = Path('G:\\')
fstub = basedir / 'Shared drives' / 'ugns-larval-behavior' / 'pi5' / '2026-05-26_11-59-05' / '2026-05-26_11-59-05 maze all mazes.mp4'
cap = videocapture.VideoCapture(fstub)

im,ts = cap.capture_frame()

cap.reset_bounding_box()
ymg = YMazeGeometry()
ymg.set_image_size((cap.h, cap.w))
ymg._cam_center = (cap.w/2, cap.h/2 -200)
ymg._barrel_alpha = -0.00001*3.2
ymg.calibrate_geometry_aruco(im)
cv2.namedWindow('clipped mazes', cv2.WINDOW_KEEPRATIO)
img = ymg.diagnostic_image(im)
cv2.imshow('clipped mazes', img)
cv2.waitKey(0)
quit()
#https://www.geeksforgeeks.org/computer-vision/detecting-aruco-markers-with-opencv-and-python-1/

aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
parameters = cv2.aruco.DetectorParameters()


detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
# Detect the markers
corners, ids, rejected = detector.detectMarkers(cv2.bitwise_not(im))
# Print the detected markers
print("Detected markers:", ids)
print("corners:", corners)
if ids is not None:
    im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
    cv2.aruco.drawDetectedMarkers(im, corners, ids)
    cv2.imshow('Detected Markers', im)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
quit()
lt = livetracker.LiveTracker(Path.home()/'deleteme', cap)
lt.full_conditioning_experiment()