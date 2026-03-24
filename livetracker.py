#from picamera.array import PiRGBArray

import time
import cv2
import numpy as np
from mazedispatcher import MazeDispatcher
from ymazegeometry import YMazeGeometry

from cameracapture import CameraCapture

print("boot")
cap = CameraCapture()

print("cam cap")
cv2.namedWindow('focus - c to continue', cv2.WINDOW_NORMAL)

print("focus")
while False: #should be True, changed to speed up testing
	#try:
	im,ts = cap.capture_frame()
	cv2.imshow('focus - c to continue', im)
	key = cv2.waitKey(1) & 0xFF
	if key == ord('c'):
		break
#except:
	#	print("error")
cv2.destroyAllWindows()


ymg = YMazeGeometry()
ymg.set_image_size((cap.w, cap.h))
while True:
	cv2.namedWindow('mazes', cv2.WINDOW_KEEPRATIO)
	im,ts = cap.capture_frame()
#	img = ymg.calibrate_geometry_from_image(im)
	cv2.imshow('mazes', im)
	cv2.waitKey(1)
	ymg.two_point_rotation_and_scaling((1763,1349), (1055,2116))
	img = ymg.diagnostic_image(im.copy())
	# x,y,w,h = ymg.clip_to_mazes(10)
	# cap.set_bounding_box(x,y,w,h)
	# im,ts = cap.capture_frame()
	cv2.imshow('mazes', img)
	key = cv2.waitKey(1) & 0xFF
	if key == ord('q'):
		quit()
	response = input("Are you satisfied with the maze locations? (yes/no)")
	if response == "yes":
		break
#cv2.destroyAllWindows()

md = MazeDispatcher(ymg)

frame_num = 0
t0 = ts
tt = None

while True:
	im,ts = cap.capture_frame()
	frame_num += 1
	frame_time = ts - t0

	#wait for previous frame to finish processing
	if tt is not None:
		for t in tt:
			t.join()

	tt = md.new_frame(img, frame_number=frame_num, frame_time=frame_time, wait_for_completion=False)
	cv2.imshow('background', im)
	key= cv2.waitKey(1) & 0xFF
	if key == ord('q'):
		break
