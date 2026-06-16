import livetracker
import cv2
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

import videocapture
from imagestabilizer import ImageStabilizer
from ymazegeometry import YMazeGeometry

#https://opencv.org/reading-and-writing-videos-using-opencv/#h-read-an-image-sequence
basedir = Path('/Users/gershow/Library/CloudStorage/GoogleDrive-mhg4@nyu.edu/')
#basedir = Path('G:\\')
#date = '2026-05-26_11-59-05'
#date = '2026-06-04_10-47-54' #rotates, old arucos
#date = '2026-06-09_12-32-47'
date = '2026-06-12_11-02-16' #bright background
fstub = basedir / 'Shared drives' / 'ugns-larval-behavior' / 'pi5' / date / (date + ' maze all mazes.mp4')
cap = videocapture.VideoCapture(fstub)

lt = livetracker.LiveTracker(Path.home()/'deleteme', cap)
# lt.experiment_duration = 600
# lt.illumination_response_test()
# quit()
ymg = YMazeGeometry()
ymg.set_image_size((cap.h, cap.w))
ymg._cam_center = (cap.w/2, cap.h/2 -200)
ymg._barrel_alpha = -0.00001*3.2
im,ts = cap.capture_frame()

ymg.calibrate_geometry_aruco(im)

lt.ymg = ymg
lt.setup_experiment()
lt.run_experiment(7000)

quit()
ymg = YMazeGeometry()
ymg.set_image_size((cap.h, cap.w))
ymg._cam_center = (cap.w/2, cap.h/2 -200)
ymg._barrel_alpha = -0.00001*3.2
im,ts = cap.capture_frame()
im = cv2.flip(im,0)

ymg.calibrate_geometry_aruco(im)
#
# t = 1/60
# H = np.array(((np.cos(t), -np.sin(t), 1), (np.sin(t), np.cos(t), 3)))
# im2 = cv2.warpAffine(im,H,(im.shape[1],im.shape[0]))
im0 = im.copy()
imstab = ImageStabilizer(im)
for j in range(1,10):
    imstab.add_roi(ymg.get_bounding_rect(j,percent_scale=50))

for j in range(cap.total_frames()-2):
    im,ts = cap.capture_frame()
    im = cv2.flip(im,0)
    if j%100 == 0:
        imunreg = cv2.merge((im0.astype(np.uint8), im.astype(np.uint8), im0.astype(np.uint8)))
        cv2.imshow('unreg', imunreg)

        im = imstab.register(im,0.01)
        imtest = cv2.merge((im0.astype(np.uint8), im.astype(np.uint8), imstab.template.astype(np.uint8)))
        cv2.imshow('test', imtest)
        if cv2.waitKey(1) == ord('q'):
            quit()




quit()

mask = cv2.morphologyEx(ymg.aruco_mask(), cv2.MORPH_DILATE, np.ones((3, 3), np.uint8), iterations = 20)
im2 = cv2.bitwise_and(im,mask)
cv2.imshow('just aruco', im2)
cv2.waitKey(0)

ymg.calibrate_geometry_aruco(im2)
img = ymg.diagnostic_image(im)
cv2.imshow('clipped mazes', img)
cv2.waitKey(0)
quit()

im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
im[:,:,0] = ymg.aruco_mask()
cv2.namedWindow('aruco mask', cv2.WINDOW_KEEPRATIO)
cv2.imshow('aruco mask', im)
cv2.waitKey(0)
quit()

numid, corners,ids, flip, invert,rej = YMazeGeometry.find_arucos(im)
if ids is not None:
    print(f"Found markers: {ids}, rejected markers: {rej}")
    print(f"flip, invert = {flip},{invert}")
    im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
    cv2.aruco.drawDetectedMarkers(im, corners, ids)
    cv2.imshow('Detected Markers', im)
    cv2.waitKey(0)
quit()
lt = livetracker.LiveTracker(Path.home()/'deleteme', cap)
lt.full_conditioning_experiment()
quit()
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