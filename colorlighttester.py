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


winname = 'Select ROI'
im,_ = cap.capture_frame()
cv2.imshow(winname, im)
x, y, w, h = cv2.getWindowImageRect('winname')
cap.set_bounding_box_from_im_coordinates(x, y, w, h)

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
	b, g, r, ts = cap.capture_frame((1, 2, 3))
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
	b, g, r, ts = cap.capture_frame((1, 2, 3))
	light_controller.turn_off_leds()
	for im,col in zip((b,g,r), ('blue', 'green', 'red')):
		img = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
		#img = ymg.diagnostic_image(im)
		cv2.putText(img, f"all LED {col} channel{c}", np.array((0, 20)), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
		cv2.imshow(winname, img)
		cv2.waitKey(1)
		cv2.imwrite(str(datadir / f"all led channel {c} {col}.jpg"),img)
		if cv2.waitKey(2000) & 0xFF == ord('q'):
			quit()
	if cv2.waitKey(100) & 0xFF == ord('q'):
		quit()
