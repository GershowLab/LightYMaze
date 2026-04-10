#TODO: make sure csv outputs no matter what, viterbi path exceptions
#affine transformation
#faster region map creation
#parameters saved in file
#window sizes
import os

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
basedir = Path.home() / 'ymaze-data'
#basedir = Path('/home/pi/ymaze_data')
nowstr = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
datadir = basedir / nowstr
datadir.mkdir(parents=True, exist_ok=True)

print(f"datadir = {datadir}")
if not os.path.exists(datadir):
	print ("did not create data directory")
	quit()

print("boot")
cap = CameraCapture()
print(f"camera setup - {time.monotonic() - tstart}")
cap.focus_window()

while True:
	ymg = YMazeGeometry()
	ymg.set_image_size((cap.h, cap.w))
	im,_ = cap.capture_frame()
	ymg.calibrate_geometry_from_image(im)
	x,y,w,h = ymg.clip_to_mazes(10)
	cap.set_bounding_box_from_im_coordinates(x, y, w, h)
	im,_ = cap.capture_frame()
	cv2.namedWindow('clipped mazes', cv2.WINDOW_KEEPRATIO)
	img = ymg.diagnostic_image(im)
	cv2.imshow('clipped mazes', img)
	cv2.resizeWindow('clipped widow', default_win_size)


	print("Are you satisfied with the maze locations? y/n q to quit")
	redo = False
	for i in range(200):
		key = cv2.waitKey(100) & 0xFF
		if key == ord('q'):
			quit()
		if key == ord('n'):
			redo = True
			break
		if key == ord('y'):
			redo = False
			break
	if not redo:
		break
	cap.reset_bounding_box()

cap.focus_window()

brightness = 9
light_controller = LightController()
light_controller.set_global_brightness(brightness)
#
# winname = 'led correspondence test - remove filter'
# cv2.namedWindow(winname, cv2.WINDOW_NORMAL)
# for c in range(3):
# 	print(f"setting channel {c} (on diagnostic 1 = r, 2 = g, 3 = b)")
# 	for m in range(1,10):
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
print(f"opening video")
fstub = datadir / f"{nowstr} maze"
md.open_video(fstub)

cv2.namedWindow('all mazes', cv2.WINDOW_NORMAL)
cv2.resizeWindow('all mazes', default_win_size)
try:
	while frame_time < experiment_duration:
		print(f"frame: {frame_num}, elapsed time: {frame_time}, imsize: {im.shape}")
		#wait for previous frame to finish processing
		if tt is not None:
			for t in tt:
				t.join()
			md.write_video()
			cv2.imshow('all mazes', md.get_composite_image())
			cv2.waitKey(1)


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
		if k == ord('t') and display_maze >= 0:
			md._maze_minions[display_maze]._maze_controller.decrease_threshold()
		if k == ord('u') and display_maze >= 0:
			md._maze_minions[display_maze]._maze_controller.increase_threshold()
		im,ts = cap.capture_frame()
		frame_num += 1
		frame_time = ts - t0
	if tt is not None:
		for t in tt:
			t.join()
	light_controller.turn_off_leds()
finally:
	filepath = datadir / f"{nowstr} results.csv"
	md.get_data_frame().to_csv(f"{filepath}")
	if light_controller is not None:
		light_controller.turn_off_leds()


