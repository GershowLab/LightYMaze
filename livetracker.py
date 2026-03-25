import time
tstart = time.monotonic()

import cv2
import numpy as np
from mazedispatcher import MazeDispatcher
from ymazegeometry import YMazeGeometry

print(f"import most libaries - {time.monotonic() - tstart}")
from cameracapture import CameraCapture
print(f"import CameraCapture - {time.monotonic() - tstart}")

print("boot")
cap = CameraCapture()
print(f"camera setup - {time.monotonic() - tstart}")
express = True
c = (1764,1345)
m4 = (1053, 2101)
if express:
	print("express setup")
	print(f"capture w = {cap.w}, capture h = {cap.h}")
	ymg = YMazeGeometry()
	ymg.set_image_size((cap.h, cap.w))
	ymg.two_point_rotation_and_scaling(c, m4)
	ymg.generate_coordinates()
	print(f"ymaze geometry created - {time.monotonic() - tstart}")
	x, y, w, h = ymg.clip_to_mazes(10)
	print(f"ymaze geometry clipped - {time.monotonic() - tstart}")

	cap.set_bounding_box(x, y, w, h)
	print(f"bounding box set - {time.monotonic() - tstart}")

	print(w,y,w,h)
	im, ts = cap.capture_frame()
	cv2.namedWindow('clipped mazes', cv2.WINDOW_KEEPRATIO)
	img = ymg.diagnostic_image(im)
	cv2.imshow('clipped mazes', img)
	print(f"debug image captured created - {time.monotonic() - tstart}")
	cv2.waitKey(0)
# 	ymg = YMazeGeometry()
# 	ymg.set_image_size((cap.h, cap.w))
# 	cv2.namedWindow('mazes', cv2.WINDOW_KEEPRATIO)
# 	im, ts = cap.capture_frame()
# 	print(f"ymg.im_size_px = {ymg.im_size_px}, im.shape = {im.shape}")
# #	img = ymg.calibrate_geometry_from_image(im)
# 	ymg.set_image_size(im.shape)
# 	print(f"ymg.im_size_px = {ymg.im_size_px}, im.shape = {im.shape}")
# 	ymg.two_point_rotation_and_scaling(c, m4)
# 	ymg.generate_coordinates()
# 	img = ymg.diagnostic_image(im)
# 	cv2.imshow('mazes', img)
# 	cv2.waitKey(1)
# 	x, y, w, h = ymg.clip_to_mazes(10)
# 	cap.set_bounding_box(x, y, w, h)
# 	im, ts = cap.capture_frame()
# 	cv2.namedWindow('clipped mazes', cv2.WINDOW_NORMAL)
# 	img = ymg.diagnostic_image(im)
# 	cv2.imshow('clipped mazes', img)

else:
	print("cam cap")
	cv2.namedWindow('focus - c to continue', cv2.WINDOW_NORMAL)

	print("focus")
	while True: #should be True, changed to speed up testing
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
	ymg.set_image_size((cap.h, cap.w))
	while True:
		cv2.namedWindow('mazes', cv2.WINDOW_KEEPRATIO)
		im,ts = cap.capture_frame()
		img = ymg.calibrate_geometry_from_image(im)
	#	cv2.imshow('mazes', im)
	#	cv2.waitKey(1)
	#	ymg.two_point_rotation_and_scaling((1763,1349), (1055,2116))
	#	img = ymg.diagnostic_image(im.copy())

		# im,ts = cap.capture_frame()
		cv2.imshow('mazes', img)
		cv2.waitKey(1)
		x,y,w,h = ymg.clip_to_mazes(10)
		cap.set_bounding_box(x,y,w,h)
		im,ts = cap.capture_frame()
		cv2.namedWindow('clipped mazes', cv2.WINDOW_NORMAL)
		img = ymg.diagnostic_image(im)
		cv2.imshow('clipped mazes', img)


		key = cv2.waitKey(1) & 0xFF
		if key == ord('q'):
			quit()
		response = input("Are you satisfied with the maze locations? (yes/no)")
		if response == "yes":
			break
	#cv2.destroyAllWindows()
#print ("creating maze dispatcher")
print(f"ymaze geometry imsize = {ymg.im_size_px}")
md = MazeDispatcher(ymg)
print(f"created maze dispatcher - {time.monotonic() - tstart}")

#print ("capturing first frame")
im, ts = cap.capture_frame()
frame_num = 0
t0 = ts
tt = None
print(f"captured first frame - {time.monotonic() - tstart}")

while True:
	frame_time = ts - t0
	print(f"frame: {frame_num}, elapsed time: {frame_time}")
	#wait for previous frame to finish processing
	if tt is not None:
		for t in tt:
			t.join()

	tt = md.new_frame(img, frame_number=frame_num, frame_time=frame_time, wait_for_completion=False)
	cv2.imshow('background', im)
	key= cv2.waitKey(1) & 0xFF
	if key == ord('q'):
		break
	im,ts = cap.capture_frame()
	frame_num += 1


