#TODO: make sure csv outputs no matter what, viterbi path exceptions
#affine transformation
#faster region map creation
#parameters saved in file
#window sizes

default_win_size = (640, 480)

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
		cv2.resizeWindow('focus - c to continue', default_win_size)
		key = cv2.waitKey(1) & 0xFF
		if key == ord('c'):
			break
		if key == ord('-'):
			cap.dimmer()
		if key == ord('+') or key == ord('='):
			cap.brighter()
	#except:
		#	print("error")
	cv2.destroyAllWindows()



	while True:
		ymg = YMazeGeometry()
		ymg.set_image_size((cap.h, cap.w))
		im,_ = cap.capture_frame()
		ymg.calibrate_geometry_from_image(im)
		# cv2.namedWindow('mazes', cv2.WINDOW_KEEPRATIO)
		# cv2.imshow('mazes', img)
		# cv2.resizeWindow('mazes', default_win_size)
		# cv2.waitKey(1)
		x,y,w,h = ymg.clip_to_mazes(10)
		cap.set_bounding_box(x,y,w,h)
		im,_ = cap.capture_frame()
		cv2.namedWindow('clipped mazes', cv2.WINDOW_NORMAL)
		img = ymg.diagnostic_image(im)
		cv2.imshow('clipped mazes', img)
		cv2.resizeWindow('clipped widow', default_win_size)



		key = cv2.waitKey(1) & 0xFF
		if key == ord('q'):
			quit()
		response = input("Are you satisfied with the maze locations? (yes/no)")
		if response == "yes":
			break
		cap.reset_bounding_box()

light_controller = LightController()
#
# winname = 'led correspondence test - remove filter'
# cv2.namedWindow(winname, cv2.WINDOW_NORMAL)
# for c in range(3):
# 	print(f"setting channel {c} (on diagnostic 1 = r, 2 = g, 3 = b)")
# 	for m in range(9):
# 		print(f"setting maze {m}")
# 		light_controller.set_led(m,c,255,255,255)
# 		light_controller.update_leds()
# 		if cv2.waitKey(1000) & 0xFF == ord('q'):
# 			break
# 		im,ts = cap.capture_frame()
# 		light_controller.set_led(m,c,0,0,0)
# 		light_controller.update_leds()
# 		img = ymg.diagnostic_image(im)
# 		cv2.imshow(winname, img)
# 		if cv2.waitKey(2000) & 0xFF == ord('q'):
# 			break
#

md = MazeDispatcher(ymg, light_controller=light_controller)
print(f"created maze dispatcher - {time.monotonic() - tstart}")

im, t0 = cap.capture_frame()
frame_num = 0
frame_time = 0
tt = None
print(f"captured first frame - {time.monotonic() - tstart}")
display_maze = 0
old_maze = -1
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
			if display_maze != old_maze:
				cv2.resizeWindow(win, default_win_size)
				old_maze = display_maze
		else:
			win = None
		k = cv2.waitKey(1) & 0xFF
		if k == ord('q'):
			break
		if ord('0') <= k <= ord('9'):
			old_maze = display_maze
			display_maze = k-ord('1')
			if  display_maze > 0 and display_maze != old_maze:
				if win is not None:
					cv2.destroyWindow(win)
		if k == ord('t') and display_maze > 0:
			md._maze_minions[display_maze]._maze_controller.decrease_threshold()
		if k == ord('T') and display_maze > 0:
			md._maze_minions[display_maze]._maze_controller.increase_threshold()

		im,ts = cap.capture_frame()
		frame_num += 1
		frame_time = ts - t0
	if tt is not None:
		for t in tt:
			t.join()
finally:
	filepath = datadir / f"{nowstr} results.csv"
	md.get_data_frame().to_csv(f"{filepath}")
	for m in range(9):
		for c in range(3):
			light_controller.set_led(m,c,0,0,0)
	light_controller.update_leds()


