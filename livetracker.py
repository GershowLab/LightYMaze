from picamera.array import PiRGBArray
from picamera import PiCamera
import time
import cv2
import numpy as np
from mazedispatcher import MazeDispatcher
from ymazegeometry import YMazeGeometry


def readImage(cap):
	im = camera.capture(cap, format = 'bgr')
	im = cap.array
	im = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
	return im

resx,resy = 2464,2464
camera = PiCamera()
camera.resolution = (resx,resy)
camera.framerate = 20

#getting the first frame
rawCapture = PiRGBArray(camera, size=(resx,resy))
rawCapture_0 = PiRGBArray(camera, size=(resx,resy))

current = readImage(rawCapture_0)

ymg = YMazeGeometry()
while True:
	img = ymg.calibrate_geometry_from_image(current)
	cv2.imshow('mazes', img)
	key = cv2.waitKey(1) & 0xFF
	if key == ord('q'):
		quit()
	response = input("Are you satisfied with the maze locations? (yes/no)")
	if response == "yes":
		break

md = MazeDispatcher(ymg)

frame_num = 0
t0 = time.monotonic()
tt = None
#was use_video_port = True, but False may allow more resolution choices
for frame in camera.capture_continuous(rawCapture, format = 'bgr', use_video_port = False):
	im = frame.array
	im=cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
	frame_num += 1
	frame_time = time.monotonic() - t0

	#wait for previous frame to finish processing
	if tt is not None:
		for t in tt:
			t.join()

	tt = md.new_frame(img, frame_number=frame_num, frame_time=frame_time, wait_for_completion=False)
	cv2.imshow('background', im)
	key= cv2.waitKey(1) & 0xFF
	rawCapture.truncate(0)
	if key == ord('q'):
		break
