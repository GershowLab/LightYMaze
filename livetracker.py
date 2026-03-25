import os
import time
tstart = time.monotonic()

import cv2
from mazedispatcher import MazeDispatcher
from ymazegeometry import YMazeGeometry
from pathlib import Path
from lightcontroller import LightController
from datetime import datetime

print(f"import most libaries - {time.monotonic() - tstart}")
from cameracapture import CameraCapture
print(f"import CameraCapture - {time.monotonic() - tstart}")


print("creating data directory")
basedir = Path('/home/pi/ymaze_data')
nowstr = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
datadir = basedir / nowstr
datadir.mkdir(parents=True, exist_ok=True)


print("boot")
cap = CameraCapture()
print(f"camera setup - {time.monotonic() - tstart}")
express = False
c = (1764,1345)
m4 = (1053, 2101)

print("testing leds")
light_controller = LightController()
light_controller.test_leds(0.2)
print("test done")
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
		im,_ = cap.capture_frame()
		img = ymg.calibrate_geometry_from_image(im)
		cv2.imshow('mazes', img)
		cv2.waitKey(1)
		x,y,w,h = ymg.clip_to_mazes(10)
		cap.set_bounding_box(x,y,w,h)
		im,_ = cap.capture_frame()
		cv2.namedWindow('clipped mazes', cv2.WINDOW_NORMAL)
		img = ymg.diagnostic_image(im)
		cv2.imshow('clipped mazes', img)


		key = cv2.waitKey(1) & 0xFF
		if key == ord('q'):
			quit()
		response = input("Are you satisfied with the maze locations? (yes/no)")
		if response == "yes":
			break

md = MazeDispatcher(ymg)
print(f"created maze dispatcher - {time.monotonic() - tstart}")

im, t0 = cap.capture_frame()
frame_num = 0
frame_time = 0
tt = None
print(f"captured first frame - {time.monotonic() - tstart}")
display_maze = 0
experiment_duration = 3600 #seconds
try:
	while frame_time < experiment_duration:
		print(f"frame: {frame_num}, elapsed time: {frame_time}, imsize: {im.shape}")
		#wait for previous frame to finish processing
		if tt is not None:
			for t in tt:
				t.join()


		tt = md.new_frame(im, frame_number=frame_num, frame_time=frame_time, wait_for_completion=False, multi_thread=True)
		#cv2.imshow('background', im)
		#key= cv2.waitKey(1) & 0xFF
		#if key == ord('q'):
		#	break
		if display_maze >= 0:
			win = md._maze_minions[display_maze].debug_display()
		else:
			win = None
		k = cv2.waitKey(1) & 0xFF
		if k == ord('q'):
			break
		if ord('0') <= k <= ord('9'):
			old_maze = display_maze
			display_maze = k-ord('1')
			if display_maze != old_maze:
				if win is not None:
					cv2.destroyWindow(win)

		im,ts = cap.capture_frame()
		frame_num += 1
		frame_time = ts - t0
	if tt is not None:
		for t in tt:
			t.join()
finally:
	filepath = datadir / f"{nowstr} results.csv"
	md.get_data_frame().to_csv(f"{filepath}")


