from ymazegeometry import YMazeGeometry
from mazedispatcher import MazeDispatcher
import cv2
import numpy as np
#https://opencv.org/reading-and-writing-videos-using-opencv/#h-read-an-image-sequence

fstub = 'G:\\Shared drives\\ugns-larval-behavior\\y-maze pictures\\y-maze feb 26\\Basler_acA1920-150um__21902780__20260226_125212812_%4d.tiff'
vc = cv2.VideoCapture(fstub)
ret, frame = vc.read()
if not ret:
    print("did not open video")
    quit()
print("calibrating geometry")
ymg = YMazeGeometry()
ymg.two_point_rotation_and_scaling(np.array((1046, 614)),np.array((909, 1033)))
#ymg.calibrate_geometry_from_image(frame)

fstub = 'G:\\Shared drives\\ugns-larval-behavior\\y-maze pictures\\y-maze feb 26\\python test\\test100'
mc = MazeDispatcher(ymg)
mc.open_csv(fstub)
mc.open_video(fstub)
for j in range(200):
    print(f"processing frame {j}")
    [ret,frame] = vc.read()
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if not ret:
        print("could not read frame " + j)
        break
    mc.new_frame(frame, wait_for_completion=True)
mc.close_csv()
mc.close_video()