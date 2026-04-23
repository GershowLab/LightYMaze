#TODO: make sure csv outputs no matter what, viterbi path exceptions
#affine transformation
#faster region map creation
#parameters saved in file
#window sizes
import os

import numpy as np

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

print("boot")
cap = CameraCapture()
print ("autofocusing")
#success =  cap.autofocus_once()
cap.set_focus(1/.0833)
print(f"camera setup - {time.monotonic() - tstart}")
cap.focus_window()

print("creating data directory")
text_basedir = Path.home() / 'ymaze-text-data'
video_basedir = Path.home() / 'ymaze-video-data'
#basedir = Path('/home/pi/ymaze_data')
nowstr = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
text_datadir = text_basedir / nowstr
video_datadir = video_basedir / nowstr


while True:
	ymg = YMazeGeometry()
	ymg.set_image_size((cap.h, cap.w))
	im,_ = cap.capture_frame()
	ymg.calibrate_geometry_from_image_fiducials(im)
#	print (f"fiducial centers: {ymg.get_fiducial_centers_px()}")
	ymg.align_mazes_to_im(im)
#	print (f"after alignment to im: fiducial centers: {ymg.get_fiducial_centers_px()}")

	x,y,w,h = ymg.clip_to_mazes(10)
#	print(f"ymg clip instructions: {(x,y,w,h)}")
#	print (f"after clipping to maze: fiducial centers: {ymg.get_fiducial_centers_px()}")

	cap.print_metadata()

	cap.set_bounding_box_from_im_coordinates(x, y, w, h)
	im,_ = cap.capture_frame()

	cap.print_metadata()

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

text_datadir.mkdir(parents=True, exist_ok=True)
video_datadir.mkdir(parents=True, exist_ok=True)

print(f"text datadir = {text_datadir}")
if not os.path.exists(text_datadir):
	print ("did not create data directory")
	quit()

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
fstub = video_datadir / f"{nowstr} maze"
md.open_video(fstub)

cv2.namedWindow('all mazes', cv2.WINDOW_NORMAL)
cv2.resizeWindow('all mazes', default_win_size)
try:
	while frame_time < experiment_duration:
		num_choices = np.sum(np.asarray(md.num_choices()),axis=0)
		print(f"frame: {frame_num}, elapsed time: {frame_time}, to light: {num_choices[0]}, to dark: {num_choices[1]}, null: {num_choices[2]}")
		#wait for previous frame to finish processing
		if tt is not None:
			for t in tt:
				t.join()
			md.write_video()
			cv2.imshow('all mazes', md.get_composite_image())
			cv2.waitKey(1)


		tt = md.new_frame(im, frame_number=frame_num, frame_time=frame_time, wait_for_completion=False, multi_thread=True)

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
	filepath = text_datadir / f"{nowstr} results.csv"
	md.get_data_frame().to_csv(f"{filepath}")
	print("experiment completed, make sure to run rclone")
	print(f"rclone -copy {text_basedir} ugns:pi5 --verbose")
	if light_controller is not None:
		light_controller.turn_off_leds()


