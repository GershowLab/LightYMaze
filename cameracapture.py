#to install for windows/mac debugging
#windows: set READTHEDOCS=True
#unix: export READTHEDOCS=True
#then pip install picamera2 --no-deps

from picamera2 import Picamera2, Metadata
from libcamera import Transform

class CameraCapture:
    def __init__(self):
        Picamera2.set_logging(Picamera2.ERROR)
        self._cam : Picamera2 = Picamera2()
        self.started = False
        paa = self._cam.camera_properties["PixelArrayActiveAreas"][0]
        self.default_bounding_box = paa
        #print(paa)
        self.w = paa[2]
        self.h = paa[3]
        self.x0 = paa[0]
        self.y0 = paa[1]
        self.main_configuration = self._cam.create_still_configuration({"format": "BGR888", "size":paa})
        self.set_bounding_box(*paa)
        self.exposure = 6000
        self.gain = 2
        self.set_exposure()
        self.hflip = False
        self.vflip = True
        self.set_exposure()
        self.ae_on = False
        #self.cam.start()

    def set_exposure(self, exposure = None, gain = None):
        if exposure is not None:
            self.exposure = exposure
        if gain is not None:
            self.gain = gain
        if self.gain < 0:
            self.gain = 0
        if self.exposure < 100:
            self.exposure = 100
        if self.exposure > 1e6:
            self.exposure = 1e6
        self.exposure = int(self.exposure)

        print(f"exposure: {self.exposure}, gain: {self.gain}")
        self._cam.set_controls({"AeEnable": False, "ExposureTime": self.exposure, "AnalogueGain": self.gain})

    def auto_exposure(self, enable = None):
        if enable is None:
            enable = not self.ae_on
        self.ae_on = enable
        self._cam.set_controls({"AeEnable": enable})
        if not enable:
            metadata = self._cam.capture_metadata()
            self.exposure = metadata["ExposureTime"]
        print(f"auto_exposure is {self.ae_on}")

    def brighter(self):
        self.set_exposure(self.exposure*1.2, self.gain)

    def dimmer(self):
        self.set_exposure(self.exposure/1.2, self.gain)


    def start(self):
        if not self.started:
            self.started = True
            self._cam.start()

    def stop(self):
        if self.started:
            self.started = False
            self._cam.stop()
    def capture_frame(self):
        self.start()
        ch = 2
        with self._cam.captured_request(flush=True) as request:
            if self.hflip and self.vflip:
                im = request.make_array("main")[self.h-1::-1, self.w-1::-1,ch]
            else:
                if self.hflip:
                    im = request.make_array("main")[:self.h, self.w - 1::-1,ch]
                else:
                    if self.vflip:
                        im = request.make_array("main")[self.h - 1::-1, :self.w,ch]
                    else:
                        im = request.make_array("main")[:self.h, :self.w,ch]

            metadata = request.get_metadata()
            timestamp = metadata['SensorTimestamp'] / 1e9
        #im = self._cam.capture_array()[:self.h, :self.w]
        #timestamp = self._cam.capture_metadata()['SensorTimestamp'] / 1e9
        #print(f"image captured - size = {im.shape}, timestamp = {timestamp}")
        return im, timestamp

    def reset_bounding_box(self):
        self.set_bounding_box(*self.default_bounding_box)

    def set_bounding_box_from_im_coordinates(self, x0, y0, w, h):
        if self.hflip:
            #image ran from x0 to x0+w
            #reversed to x0+w to x0
            #subset runs from (x0+w-x') to (x0 + w - x' - w')
            x0 = self.x0 + self.w - x0 - w
        else:
            x0 = self.x0 + x0
        if self.vflip:
            y0 = self.y0 + self.h - y0 - h
        else:
            y0 = self.y0 + y0
        self.set_bounding_box(x0, y0, w, h)

    def set_bounding_box(self, x0, y0, w, h):
        was_started = self.started
        #self.cam.stop()
        self.w = w
        self.h = h
        self.x0 = x0
        self.y0 = y0
        self.main_configuration = self._cam.create_still_configuration({"format": "BGR888", "size": (self.w, self.h)}) #,"Transform": Transform(hflip=True)})
        self.main_configuration["controls"]["ScalerCrop"] = (x0,y0,w,h)
        self.main_configuration["controls"]["Brightness"] = -0.5
        self.main_configuration["controls"]["AwbEnable"] = False
        self.main_configuration["controls"]["Contrast"] = 2
        self.main_configuration["controls"]["Saturation"] = 1
        self.main_configuration["controls"]["Sharpness"] = 20
        self.stop()
        self._cam.configure(self.main_configuration)
        if was_started:
            self.start()

