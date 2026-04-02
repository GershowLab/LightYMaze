from ymazegeometry import YMazeGeometry
from mazedispatcher import MazeDispatcher
import cv2
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

#https://opencv.org/reading-and-writing-videos-using-opencv/#h-read-an-image-sequence
basedir = Path('/Users/gershow/Library/CloudStorage/GoogleDrive-mhg4@nyu.edu/')
#basedir = Path('G:\\')
fstub = basedir / 'Shared drives' / 'ugns-larval-behavior' / 'y-maze pictures' / 'y-maze feb 26' / 'Basler_acA1920-150um__21902780__20260226_125212812_%04d.tiff'

print(fstub)

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
ymg.calibrate_geometry_from_image(frame)
#ymg.two_point_rotation_and_scaling(np.array((1046, 614)),np.array((909, 1033)))
#ymg.generate_coordinates()
testim = ymg.diagnostic_image(frame)

cv2.namedWindow('mazes', cv2.WINDOW_KEEPRATIO)
cv2.imshow('mazes', testim)
cv2.waitKey(0)

x,y,w,h = ymg.clip_to_mazes(10)

cv2.namedWindow('clipped mazes', cv2.WINDOW_KEEPRATIO)
clip_inds = np.ix_(y + range(h), x + range(w))
clipim = ymg.diagnostic_image(frame[clip_inds])
cv2.imshow('clipped mazes', clipim)

cv2.waitKey(0)
# for j in range(1000):
#     testim = ymg.calibrate_geometry_from_image(frame)
#     cv2.imshow('mazes', testim)
#     key= cv2.waitKey(1) & 0xFF
#     if key == ord('q'):
#         break
#     response = input("Are you satisfied with the regions you have selected? (yes/no)")
#     if response == "yes":
#         break

#fstub = 'G:\\Shared drives\\ugns-larval-behavior\\y-maze pictures\\y-maze feb 26\\python test\\tesfstub = fstub.parents[0] / 'python test' / 'test'
md = MazeDispatcher(ymg)
#md.open_video(fstub)
tt = None
#written assuming you've already got a frame from above
#try:
cv2.namedWindow('montage', cv2.WINDOW_KEEPRATIO)
for j in range(3600):
    print(f"processing frame {j}")
    if frame.ndim == 3:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if not ret:
        print("could not read frame " + j)
        break
    frame = frame[clip_inds]
    if tt is not None:
        for t in tt:
            t.join()
    tt = md.new_frame(frame, multi_thread=True)
    img = md.make_composite_image()
    md._maze_minions[2].debug_display()
    cv2.imshow('montage', img)
    cv2.waitKey(1)
    [ret, frame] = vc.read()
    if not ret:
        break
#finally:
 #   md.get_data_frame().to_csv(f"{fstub} data.csv")
  #  md.close_video()