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
ymg.calibrate_geometry_from_image(current)

locs = []

for frame in camera.capture_continuous(rawCapture, format = 'bgr', use_video_port = True):
	image = frame.array
	cv2.imshow('Frame', image)
	key= cv2.waitKey(1) & 0xFF
	rawCapture.truncate(0)
	if len(locs) == number_of_regions:
		response = input("Are you satisfied with the regions you have selected? (yes/no)")
		if response == "yes":
			break
		if response == "no":
			locs = []
	if key == ord('q'):
		break

for frame in camera.capture_continuous(rawCapture, format = 'bgr', use_video_port = True):
	image = frame.array
	cv2.imshow('Frame', image)
	key= cv2.waitKey(1) & 0xFF
	rawCapture.truncate(0)
	if len(locs) == number_of_regions:
		response = input("Are you satisfied with the regions you have selected? (yes/no)")
		if response == "yes":
			break
		if response == "no":
			locs = []
	if key == ord('q'):
		break
############################################################################################
################################STATE MACHINE INITIALIZATION################################
initial = locs[0]
statemachine = StateMachine(initial,locs)

############################################################################################
####################################GPIO INITIALIZATION#####################################
#GPIO.setmode(GPIO.BCM)
#GPIO.setwarnings(False)

red = 12
ir = 13
v1 = 4
v2 = 17
v3 = 27
v4 = 22
v5 = 5
v6= 6
GPIO.setup(red, GPIO.OUT)
GPIO.setup(ir, GPIO.OUT)
GPIO.setup(v1, GPIO.OUT)
GPIO.setup(v2, GPIO.OUT)
GPIO.setup(v3, GPIO.OUT)
GPIO.setup(v4, GPIO.OUT)
GPIO.setup(v5, GPIO.OUT)
GPIO.setup(v6, GPIO.OUT)

lightsvalves = LightsValves(red,ir,v1,v2,v3,v4,v5,v6)
lightsvalves.offall()

############################################################################################
###################################EXPERIMENT###############################################


########BUILD UP BACKGROUND IMAGE####################################

fps = 10 #frame rate
rawCapture = PiRGBArray(camera, size=(resx,resy))
rawCapture_0 = PiRGBArray(camera, size=(resx,resy))
frame_0 = readImage(rawCapture_0)
Ims = deque()                   #set up FIFO data structure for video frames
Ims.append(frame_0)
N = 1                           #N keeps track of how many frames have gone by
window = 60                     #sets the length of the window over which mean is calculated

print('Building Background')

for frame in camera.capture_continuous(rawCapture, format = 'bgr', use_video_port = True):
    im = frame.array
    im=cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    if N == fps:            #add a new frame to kernel each second
            Ims.append(im)
            N = 1
    if len(Ims)==window:
            bgim = np.median(Ims, axis=0).astype(dtype = np.uint8)
            break
    N +=1
    cv2.imshow('background', im)
    key= cv2.waitKey(1) & 0xFF
    rawCapture.truncate(0)
    if key == ord('q'):
	    break
