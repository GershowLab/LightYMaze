#TODO: make sure csv outputs no matter what, viterbi path exceptions
#affine transformation
#faster region map creation
#parameters saved in file
#window sizes
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


print("creating data directory")
basedir = Path('/home/pi/ymaze_calibration')
nowstr = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
datadir = basedir / nowstr
datadir.mkdir(parents=True, exist_ok=True)


print("boot")
cap = CameraCapture()
print(f"camera setup - {time.monotonic() - tstart}")
express = False
c = (1764,1345)
m4 = (1053, 2101)

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
	cv2.namedWindow('clipped mazes', cv2.WINDOW_KEEPRATIO)
	img = ymg.diagnostic_image(im)
	cv2.imshow('clipped mazes', img)
	cv2.resizeWindow('clipped widow', default_win_size)



	key = cv2.waitKey(1) & 0xFF
	break
	# if key == ord('q'):
	# 	quit()
	# response = input("Are you satisfied with the maze locations? (yes/no)")
	# if response == "yes":
	# 	break
	# cap.reset_bounding_box()

light_controller = LightController()
#
winname = 'led correspondence test - remove filter'
cv2.namedWindow(winname, cv2.WINDOW_NORMAL)
cv2.resizeWindow(winname, (960,720))
bright = 10
for led in range(27):
	print(f"setting led {led}")
	light_controller.set_led_direct(led, bright, bright, bright)
	light_controller.update_leds()
	time.sleep(0.5)
	im, ts = cap.capture_frame()
	light_controller.set_led_direct(led, 0, 0, 0)
	light_controller.update_leds()
	img = ymg.diagnostic_image(im)
	cv2.putText(img, f"LED {led}", np.array((0, 20)), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
	cv2.imshow(winname, img)
	cv2.waitKey(1)
	cv2.imwrite(datadir / f"LED {led}.jpg", img)
	if cv2.waitKey(2000) & 0xFF == ord('q'):
		break
for c in range(3):
	print(f"setting channel {c} (on diagnostic 1 = r, 2 = g, 3 = b)")
	for m in range(1,10):
		print(f"setting maze {m}")
		light_controller.set_led(m,c,bright,bright,bright)
		light_controller.update_leds()
		time.sleep(0.5)
		im,ts = cap.capture_frame()
		light_controller.set_led(m,c,0,0,0)
		light_controller.update_leds()
		img = ymg.diagnostic_image(im)
		cv2.putText(img, f"maze {m}, channel {c}", np.array((0,20)), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
		cv2.imshow(winname, img)
		cv2.imwrite(datadir / f"maze {m} channel {c}.jpg", img)
		if cv2.waitKey(2000) & 0xFF == ord('q'):
			break
