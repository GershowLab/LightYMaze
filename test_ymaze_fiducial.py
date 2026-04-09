import cv2
from ymazegeometry import YMazeGeometry
from pathlib import Path

basedir = Path('G:\\')
fpath = basedir / 'Shared drives' / 'ugns-larval-behavior' / 'Pi5-calibrations' / '2026-04-07_16-11-31' /'LED 0.jpg'
print (f"{fpath} exists? {fpath.exists()}")
im = cv2.imread(fpath)
img = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)

ymg = YMazeGeometry();
ymg.set_image_size(img.shape)
ymg.calibrate_geometry_from_image_fiducials(img)
im = ymg.diagnostic_image(img)

cv2.namedWindow('diagnostic image', cv2.WINDOW_KEEPRATIO)
cv2.imshow('diagnostic image', im)

cv2.waitKey(30000)
