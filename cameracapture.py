#to install for windows/mac debugging
#windows: set READTHEDOCS=True
#unix: export READTHEDOCS=True
#then pip install picamera2 --no-deps

from picamera2 import Picamera2, Metadata
from libcamera import Transform, controls
import cv2

class CameraCapture:
    def __init__(self):
        Picamera2.set_logging(Picamera2.ERROR)
        self._cam : Picamera2 = Picamera2()
        self.started = False
        paa = self._cam.camera_properties["PixelArrayActiveAreas"][0]
        paa = [0,0, paa[2], paa[3]]
        self.default_bounding_box = paa
        #print(paa)
        self.w = paa[2]
        self.h = paa[3]
        self.x0 = paa[0]
        self.y0 = paa[1]
        self.main_configuration = self._cam.create_still_configuration({"format": "BGR888", "size":paa})
        self.ae_on = False
        self.set_bounding_box(*paa)
        self.exposure = 20000
        self.gain = 2
        self.set_exposure()
        self.hflip = False
        self.vflip = True
        self.set_exposure()
      #  self.auto_exposure(False)
        self._lens_position = 0.0
        #self.cam.start()
        self._last_frame_time = 0
        self._frame_number = 0

    def get_lens_position(self):
        return self._lens_position

    def autofocus_once(self):
        self.start()
        self._cam.set_controls({"AfMode": controls.AfModeEnum.Auto})
        success = self._cam.autofocus_cycle()
        if success:
            with self._cam.captured_request(flush=True) as request:
                metadata = request.get_metadata()
                self._lens_position = metadata['LensPosition']
                self._cam.set_controls({"AfMode": controls.AfModeEnum.Auto, "LensPosition": self._lens_position})
                print(f"autofocus succeded - new focal distance = {1 / self._lens_position}")
        return success

    def focus_towards(self):
        self.set_focus(self._lens_position * 1.05)
      #  self._cam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": self.lens_position})


    def focus_away(self):
        self.set_focus(self._lens_position * 0.95)
        # self.lens_position *= 0.95
        # self._cam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": self.lens_position})

    def set_focus(self, lens_position):
        self._lens_position = lens_position
        self._cam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": self._lens_position})
        print(f"new focal power = {self._lens_position}, implied distance = {1 / self._lens_position}")

    def move_focus(self, distance):
        if self._lens_position  > 0:
            self.set_focus(1 / (1 / self._lens_position + distance))
        else:
            self.set_focus(10) #10 cm

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
        if self.started and not enable:
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

    def print_metadata(self):
        with self._cam.captured_request(flush=False) as request:
            print(request.get_metadata())


    def stop(self):
        if self.started:
            self.started = False
            self._cam.stop()

    def last_frame_number_and_time(self):
        return self._frame_number, self._last_frame_time

    def capture_frame(self, channels = (2,), flush=True):
        self.start()
        im, ts = self.capture_color_frame(flush=flush)
        if ts > self._last_frame_time:
            self._last_frame_time = ts
            self._frame_number += 1
        ret = [im[:,:,c] for c in channels]
        ret.append(ts)
        return ret
        # ret = []
        # with self._cam.captured_request(flush=flush) as request:
        #     for ch in channels:
        #         if self.hflip and self.vflip:
        #             im = request.make_array("main")[self.h-1::-1, self.w-1::-1,ch]
        #         else:
        #             if self.hflip:
        #                 im = request.make_array("main")[:self.h, self.w - 1::-1,ch]
        #             else:
        #                 if self.vflip:
        #                     im = request.make_array("main")[self.h - 1::-1, :self.w,ch]
        #                 else:
        #                     im = request.make_array("main")[:self.h, :self.w,ch]
        #         ret.append(im)
        #     metadata = request.get_metadata()
        #     timestamp = metadata['SensorTimestamp'] / 1e9
        #     ret.append(timestamp)
        # return ret
    def capture_color_frame(self, flush = True):
        self.start()
        with self._cam.captured_request(flush=flush) as request:
            if self.hflip and self.vflip:
                im = request.make_array("main")[self.h-1::-1, self.w-1::-1,:]
            else:
                if self.hflip:
                    im = request.make_array("main")[:self.h, self.w - 1::-1,:]
                else:
                    if self.vflip:
                        im = request.make_array("main")[self.h - 1::-1, :self.w,:]
                    else:
                        im = request.make_array("main")[:self.h, :self.w,:]
            metadata = request.get_metadata()
            timestamp = metadata['SensorTimestamp'] / 1e9
        return im,timestamp

    def focus_window(self):
        winname = 'focus - c to continue'
        cv2.namedWindow(winname, cv2.WINDOW_KEEPRATIO)
        while True:
            im, ts = self.capture_frame()
            cv2.imshow(winname, im)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('c'):
                break
            if key == ord('-'):
                self.dimmer()
            if key == ord('+') or key == ord('='):
                self.brighter()

            if key == ord('h'):
                self.hflip = not self.hflip

            if key == ord('v'):
                self.vflip = not self.vflip

            if key == ord('a'):
                self.auto_exposure()


            if key == ord('T'):
                self.focus_towards()

            if key == ord('t'):
                self.move_focus(-0.0005) #move focus 0.5 mm closer

            if key == ord('w'):
                self.move_focus(0.0005) #move focus 0.5 mm farther
                print('w')

            if key == ord('f'):
                self.autofocus_once()

            if key == ord('W'):
                self.focus_away()
                print('W')

            if key == ord('q'):
                quit()
        cv2.destroyWindow(winname)

    def reset_bounding_box(self):
        self.set_bounding_box(*self.default_bounding_box)

    def set_bounding_box_from_im_coordinates(self, x0, y0, w, h):
        print(f"old bounding box = {(self.x0, self.y0, self.w, self.h)}")
        print(f"new bounding box im coordinates = {(x0, y0, w, h)}")

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
        self.main_configuration["controls"]["Sharpness"] = 0
        self.main_configuration["controls"]["AeEnable"] = self.ae_on
        self.stop()
        self._cam.configure(self.main_configuration)
        print(f"new bounding box = {(x0,y0,w,h)}")
        if was_started:
            self.start()

