#to install for windows/mac debugging
#windows: set READTHEDOCS=True
#unix: export READTHEDOCS=True
#then pip install picamera2 --no-deps

from picamera2 import Picamera2, Metadata
from libcamera import Transform

class CameraCapture:
    def __init__(self):
        self.cam : Picamera2 = Picamera2()
        paa = self.cam.camera_properties["PixelArrayActiveAreas"][0]
        print(paa)
        self.w = paa[2]
        self.h = paa[3]
        self.x0 = paa[0]
        self.y0 = paa[1]
        self.main_configuration = self.cam.create_still_configuration({"format": 'YUV420', "size":paa})
        self.set_bounding_box(*paa)
        self.cam.start()

    def capture_frame(self):
        im = self.cam.capture_array()[:self.h, :self.w]
        timestamp = self.cam.capture_metadata()['SensorTimestamp'] / 1e9
        return im, timestamp

    def set_bounding_box(self, x0, y0, w, h):
        #self.cam.stop()
        self.w = w
        self.h = h
        self.x0 = x0
        self.y0 = y0
        self.main_configuration = self.cam.create_still_configuration({"format": 'YUV420', "size": (self.w, self.h)}) #,"Transform": Transform(hflip=True)})
        self.main_configuration["controls"]["ScalerCrop"] = (x0,y0,w,h)
        self.cam.configure(self.main_configuration)

