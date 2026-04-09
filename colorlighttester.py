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
basedir = Path.home() / 'ymaze_calibration'
nowstr = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
datadir = basedir / nowstr
datadir.mkdir(parents=True, exist_ok=True)
print (f"data dir = {datadir}")

print("boot")
cap = CameraCapture()
print(f"camera setup - {time.monotonic() - tstart}")


print("focus")
cap.focus_window()

#
# winname = 'Select ROI'
# im,_ = cap.capture_frame()
# cv2.imshow(winname, im)
# x, y, w, h = cv2.getWindowImageRect(winname)
# cap.set_bounding_box_from_im_coordinates(x, y, w, h)

while True:
	print ("ymaze geometry")
	ymg = YMazeGeometry()
	print ("set image size")
	ymg.set_image_size((cap.h, cap.w))
	print ("capture frame")
	im,_ = cap.capture_frame()
	print ("calibrate geometry from image")
	ymg.calibrate_geometry_from_image(im)
	x,y,w,h = ymg.clip_to_mazes(10)
	cap.set_bounding_box_from_im_coordinates(x,y,w,h)
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

light_controller = LightController()
#
winname = 'led correspondence test - remove filter'
cv2.namedWindow(winname, cv2.WINDOW_NORMAL)
cv2.resizeWindow(winname, (960,720))
bright = 10
light_controller.set_global_brightness(5)
for led in range(27):
	print(f"setting led {led}")
	light_controller.set_led_direct(led, bright, bright, bright)
	light_controller.update_leds()
	time.sleep(0.5)
	b, g, r, ts = cap.capture_frame((0, 1, 2))
	light_controller.turn_off_leds()
	for im,col in zip((b,g,r), ('blue', 'green', 'red')):
		img = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
		#img = ymg.diagnostic_image(im)
		cv2.putText(img, f"LED {led} {col}", np.array((0, 20)), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
		cv2.imshow(winname, img)
		cv2.waitKey(1)
		print (str(datadir / f"led {led} {str}.jpg"))
		cv2.imwrite(str(datadir / f"LED {led}.jpg"), img)
	if cv2.waitKey(100) & 0xFF == ord('q'):
		quit()
for c in range(1,4):
	print(f"setting channel {c} (on diagnostic 1 = r, 2 = g, 3 = b)")
	for m in range(1,10):
		light_controller.set_led(m, c, bright, bright, bright)
		light_controller.update_leds()
	time.sleep(0.5)
	b, g, r, ts = cap.capture_frame((0, 1, 2))
	light_controller.turn_off_leds()
	for im,col in zip((b,g,r), ('blue', 'green', 'red')):
		img = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
		#img = ymg.diagnostic_image(im)
		cv2.putText(img, f"all LED {col} channel{c}", np.array((0, 20)), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
		cv2.imshow(winname, img)
		cv2.waitKey(1)
		cv2.imwrite(str(datadir / f"all led channel {c} {col}.jpg"),img)
		if cv2.waitKey(100) & 0xFF == ord('q'):
			quit()
	if cv2.waitKey(100) & 0xFF == ord('q'):
		quit()
