from ymazegeometry import YMazeGeometry
from mazedispatcher import MazeDispatcher
import cv2
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

#https://opencv.org/reading-and-writing-videos-using-opencv/#h-read-an-image-sequence
basedir = Path('/Users/gershow/Library/CloudStorage/GoogleDrive-mhg4@nyu.edu/')
fstub = basedir / 'Shared drives' / 'ugns-larval-behavior' / 'y-maze pictures' / 'y-maze feb 26' / 'Basler_acA1920-150um__21902780__20260226_125212812_%04d.tiff'



#fstub = '/Users/gershow/Library/CloudStorage/GoogleDrive-mhg4@nyu.edu/Shared drives/ugns-larval-behavior/y-maze pictures/y-maze feb 26/Basler_acA1920-150um__21902780__20260226_125212812_%4d.tiff'

#fstub = 'G:\\Shared drives\\ugns-larval-behavior\\y-maze pictures\\y-maze feb 26\\Basler_acA1920-150um__21902780__20260226_125212812_%4d.tiff'
vc = cv2.VideoCapture(fstub, cv2.CAP_IMAGES)
ret, frame = vc.read()
if not ret:
    print("did not open video")
    quit()
print("calibrating geometry")
ymg = YMazeGeometry()
ymg.set_image_size(frame.shape)
ymg.two_point_rotation_and_scaling(np.array((1046, 614)),np.array((909, 1033)))
ymg.generate_coordinates()
#ymg.calibrate_geometry_from_image(frame)

#fstub = 'G:\\Shared drives\\ugns-larval-behavior\\y-maze pictures\\y-maze feb 26\\python test\\test100'
fstub = fstub.parents[0] / 'python test' / 'test100'
md = MazeDispatcher(ymg)
md.open_csv(fstub)
md.open_video(fstub)
tt = None
for j in range(1000):
    print(f"processing frame {j}")
    [ret,frame] = vc.read()
    if frame.ndim == 3:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if not ret:
        print("could not read frame " + j)
        break
    if tt is not None:
        for t in tt:
            t.join()
    md.new_frame(frame, multi_thread=False)
    md._maze_minions[1].debug_display()
    cv2.waitKey(100)
md.close_csv()
md.close_video()