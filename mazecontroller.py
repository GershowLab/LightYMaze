
import cv2
import numpy as np
import pandas as pd
from fontTools.merge.util import bitwise_and

import ymazegeometry
from BakCreator import BakCreator
from lightcontroller import LightController
from viterbi import Viterbi
from ymazegeometry import MazePart
import stimulusmanager


import time

from threading import Lock



class MazeController:
    _vid_writer: cv2.VideoWriter

    def __init__(self, light_controller: LightController, region_map: np.ndarray, transition_probabilities: np.ndarray,
                 maze_ID: int, padding : int, choice1rgb = (0,0,0), choice2rgb = (0,0,255), register_images = True):
        self._maze_ID = maze_ID
        self._bak: BakCreator = None
        self._light_controller = light_controller
        self._region_map = region_map.astype(np.uint8)
        self._region_color = None
        self._maze_mask = cv2.morphologyEx(255 * (self._region_map > 0).astype(np.uint8), cv2.MORPH_DILATE, np.ones((3,3), np.uint8), iterations=padding)
        # 255*cv2.morphologyEx((self._region_map > 0).astype(np.uint8), cv2.MORPH_DILATE, np.ones((5,5), np.uint8))
        self._h, self._w = self._region_map.shape  # row x col
        [self._x, self._y] = np.meshgrid(np.arange(self._w), np.arange(self._h))
        self._num_regions = np.max(region_map).astype(np.uint8)
        # locs = self._get_region_centers()
        # self._state_machine = StateMachine(locs[0], locs)
        self._stack_len = 100
        self._threshold = 32
        self._larva_loc: np.ndarray = np.array([-1, -1])
        self._frame_number = 0
        self._vid_writer: cv2.VideoWriter = None
        self._img = np.zeros_like(self._region_map)
        self._larva_mask = np.zeros_like(self._region_map)
        self._viterbi = Viterbi(transition_probabilities)
        self._larva_region: MazePart = MazePart.INTERSECTION
        self._update_frame_interval = None
        self._update_time_interval = 3
        self._stats = {
            "MazeID": self._maze_ID,
            "Frame": 0,
            "FrameTime": 0,
            "LarvaX": -1,
            "LarvaY": -1,
            "LarvaArea": -1,
            "LarvaMeanArea": -1,
            "LarvaStdArea": -1,
            "Region": -1,
            "Led1R": 0,
            "Led1G": 0,
            "Led1B": 0,
            "Led1PCT": 100,
            "Led2R": 0,
            "Led2G": 0,
            "Led2B": 0,
            "Led2PCT": 100,
            "Led3R": 0,
            "Led3G": 0,
            "Led3B": 0,
            "Led3PCT": 100,
            "Message":"",
            "Decision":""
        }
        self._df = pd.DataFrame(columns=self._stats.keys())
        self._lock = Lock()
        self._choice1rgb = choice1rgb
        self._choice2rgb = choice2rgb
        self._stimulus_manager = stimulusmanager.StimulusManager(self, choice1rgb=self._choice1rgb, choice2rgb=self._choice2rgb)
        self._last_msg_frame = -1000
        self._last_msg = "no message"
        self._set_regions()
        self._led_update = False
        self._led_on_max_time = 300 #seconds
        self._last_led_update = time.monotonic()

        self._min_larva_area = 400
        self._sum_larva_area = 0
        self._sum_sq_larva_area = 0
        self._num_larva_area = 0
        self._initialized = False
        self._decisions = {"dark":0,"light":0,"null":0}
        self._led_settings = [[0,0,0,0],[0,0,0,0],[0,0,0,0]]
        self._tracking_enabled = True
        self._phase_align_incoming = register_images
        self._hw_align = None
        self._img_shift = np.array((0,0))

    def enable_stim_manager (self, enable):
        if enable:
            self._stimulus_manager.turn_on()
        else:
            self._stimulus_manager.turn_off()

    def enable_background_update (self, enable):
        if self._bak is not None:
            self._bak.enable_bg_update(enable)

    def enable_tracking(self, enable):
        self._tracking_enabled = enable

    def enable_image_registration(self, enable):
        self._phase_align_incoming = enable
        if not enable:
            self._img_shift = np.array((0,0))

    def set_threshold(self, threshold):
        if threshold < 5:
            threshold = 5
        if threshold > 200:
            threshold = 200
        print(f"{self._maze_ID}: changing threshold to {threshold}")
        self._threshold = threshold
        if self._bak is not None:
            self._bak.set_threshold(self._threshold)

    def set_update_intervals(self, update_frame_interval=None, update_time_interval=None):
        if update_frame_interval is not None:
            self._update_frame_interval = update_frame_interval
        if update_time_interval is not None:
            self._update_time_interval = update_time_interval
        if self._bak is not None:
            self._bak.set_update_intervals(self._update_frame_interval, self._update_time_interval)

    def increase_threshold(self):
        self.set_threshold(self._threshold + 5)

    def decrease_threshold(self):
        self.set_threshold(self._threshold - 5)

    def get_viterbi_path(self):
        return np.asarray(self._viterbi.most_likely_path())+1

    def get_dataframe(self):
        df = self._df.copy()
        try:
            path = self._viterbi.most_likely_path()
            p = np.zeros_like(df['Frame'])
            p[-(len(path)+1):-1] = np.asarray(path)+1
            df['viterbi_path'] = p
        finally:
            return df

    def _set_regions(self):
        self._regions = ymazegeometry.Region.all_regions(self._region_map)

    def _get_region_centers(self):
        locs: list[np.ndarray] = []
        for j in range(1, self._num_regions + 1):
            x = np.mean(self._x[self._region_map == j])
            y = np.mean(self._y[self._region_map == j])
            locs.append(np.array([x, y]))
        return locs

    def _align_image_to_background (self, img):
        if self._bak is None:
            return img,np.array((0,0))
        bgim = self._bak.get_background()
        h, w = bgim.shape
        if self._hw_align is None:
            self._hw_align = cv2.createHanningWindow((w,h), cv2.CV_32F)
        shift,_ = cv2.phaseCorrelate(np.asarray(bgim, np.float32), np.asarray(img, np.float32)) #how much the input image is shifted relative to background
        transform_matrix = np.float32([[1, 0, -shift[0]], [0, 1, -shift[1]]])
        img = cv2.warpAffine(img, transform_matrix, (w,h))
        return img,shift

    def get_shift(self):
        return np.asarray(self._img_shift)

    def new_image(self, img, frame_number=None, capture_time=None):
        newshift = False
        if self._lock.acquire(blocking=False):
            try:
                #self._img = img  # pass a copy to new_image
                #print (f"img shape = {img.shape}")
                if frame_number is None:
                    self._frame_number += 1
                else:
                    self._frame_number = frame_number
                self._stats["Frame"] = self._frame_number
                if capture_time is None:
                    self._stats["FrameTime"] = time.monotonic()
                else:
                    self._stats["FrameTime"] = capture_time
                if self._bak is None:
                    self._bak = BakCreator(self._stack_len, bgim = img)
                    self._bak.set_threshold(self._threshold)
                    self._bak.set_update_intervals(self._update_frame_interval, self._update_time_interval)
                    self._initialized = True
                if self._phase_align_incoming:
                    img,self._img_shift = self._align_image_to_background(img)
                    newshift = True
                self._img = img

                init = self._bak.update_background(img, frame_num=frame_number, frame_time=capture_time)
                # during initialization period, just update background
                if self._tracking_enabled and init:
                    thresh = self._bak.get_thresholded_image()
                    thresh = cv2.bitwise_and(thresh, self._maze_mask)
                    self._update_larva(thresh)
                    self._stimulus_manager.update()
                    msg,hasmsg = self._stimulus_manager.get_message(mark_read=True)
                    if hasmsg:
                        self._last_msg = msg
                        self._last_msg_frame = self._frame_number
                        self._stats["Message"] = msg
                    else:
                        self._stats["Message"] = ""
                self._write_video()
                self._df.loc[len(self._df)] = self._stats
                if (time.monotonic() - self._last_led_update) > self._led_on_max_time:
                    self.set_leds((0,0,0),(0,0,0),(0,0,0))
                if self._led_update and self._light_controller is not None:
                    self._light_controller.update_leds()
                    self._led_update = False
            finally:
                self._lock.release()
        return newshift
    def initialized(self):
        return self._initialized

    def _update_larva(self, thresh):
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            thresh, connectivity=8
        )
        if num_labels > 1:
            area = [stats[i, cv2.CC_STAT_AREA] for i in range(1, num_labels)]
            #print(area)
            try:
                larva_ind = np.argmax(area) + 1
                #print (larva_ind)
                self._larva_loc = centroids[larva_ind]
                self._larva_mask = (labels == larva_ind).astype(np.uint8) * 255
                la = float(area[larva_ind - 1])
                self._stats["LarvaArea"] = la
               # print(la)
                log_p_obs = np.array([-np.log(len(self._regions)) for r in self._regions])
                if la > self._min_larva_area:
                    self._sum_larva_area += la
                    self._sum_sq_larva_area += la ** 2
                    self._num_larva_area += 1
                    u = self._sum_larva_area/self._num_larva_area
                    v = self._sum_sq_larva_area/self._num_larva_area - u ** 2
                    self._stats["LarvaMeanArea"] = u
                    self._stats["LarvaStdArea"] = np.sqrt(v)
                    reg_fracs = np.array([r.fraction_covered(self._larva_mask) for r in self._regions])
                    p = reg_fracs/np.sum(reg_fracs) + 1e-6
                    # if np.argmax(p) == 0:
                    #     print (f"{self._maze_ID}: most prob = center")
                    log_p_obs = np.log(p)
                    # if True or la > u - 3*np.sqrt(v):
                    #     log_p_obs = [r.logP(self._larva_loc) for r in self._regions]
                    #     log_p_obs = np.array(log_p_obs) - np.log(np.sum(np.exp(log_p_obs)))
                self._larva_region = self._viterbi.new_obs(log_p_obs) + 1
            except Exception as e:
                print(e)
                self._larva_loc = np.array([-1, -1])
        self._stats["Region"] = self._larva_region
        self._stats["LarvaX"] = float(self._larva_loc[0])
        self._stats["LarvaY"] = float(self._larva_loc[1])


    def get_larva_region(self):
        return self._larva_region

    def region_image(self, mask = None):
        # center = 1 white
        # 2 = red
        # 3 = blue
        # 4 = green
        # 5 = cyan
        # 6 = yellow
        # 7 = magenta
        if self._region_color is None:
        #    r = np.zeros_like(self._region_map)
         #   g = np.zeros_like(self._region_map)
          #  b = np.zeros_like(self._region_map)
            inr = (1, 2, 6, 7)
            ing = (1, 4, 5, 6)
            inb = (1, 3, 5, 7)
            inr = np.isin(self._region_map, inr).astype(np.uint8)*255
            ing = np.isin(self._region_map, ing).astype(np.uint8)*255
            inb = np.isin(self._region_map, inb).astype(np.uint8)*255
            self._region_color = cv2.merge((inb,ing,inr))

        if mask is None:
            return self._region_color
        else:
            return cv2.bitwise_xor(self._region_color, cv2.merge((mask,mask,mask)))
            return cv2.bitwise_and(self._region_color, (128,128,128), mask=mask)
            return cv2.bitwise_and(self._region_color,mask)*value + cv2.bitwise_and(self._region_color,~mask)*altvalue
            vim = np.zeros_like(self._region_map)
            vim[mask] = value
            vim[~mask] = alt_value
            return cv2.multiply(self._region_color, cv2.merge((vim,vim,vim)))
            #return cv2.merge((vim*self._region_color[:,:,0],vim*self._region_color[:,:,1],vim*self._region_color[:,:,2]))

        if mask is not None:
            r[np.logical_and(mask, inr)] = value
            r[np.logical_and(~mask, inr)] = alt_value
            g[np.logical_and(mask, ing)] = value
            g[np.logical_and(~mask, ing)] = alt_value
            b[np.logical_and(mask, inb)] = value
            b[np.logical_and(~mask, inb)] = alt_value
        else:
            r[inr] = value
            g[ing] = value
            b[inb] = value


        return cv2.merge((r,g,b))

    def debug_montage(self):
        img = cv2.cvtColor(self._img, cv2.COLOR_GRAY2BGR)
        #bak = cv2.cvtColor(self._bak.get_background(), cv2.COLOR_GRAY2BGR)
        b = self._bak.get_background()
        bak = cv2.merge((b, self._img, b))
        thresh = self._bak.get_thresholded_image()
        thresh = self.region_image(thresh)
#
# #        thresh = self._bak.get_zscore_image(self._img)
#
#         g = thresh.copy()
#         g[self._maze_mask == 0] = 255
#        thresh = cv2.merge((thresh.astype(np.uint8),g.astype(np.uint8),thresh.astype(np.uint8)))
        img_annotate = self.debug_image()
        montage = np.vstack((np.hstack((img, bak)), np.hstack((thresh, img_annotate))))
        return montage

    def debug_image(self, decimate = 1, show_frame = True):
        r = self._img.copy().astype(np.uint16)
        r[self._larva_mask > 0] = 255
        b = self._img.copy().astype(np.uint16)
        g = self._img.copy().astype(np.uint16)

        for reg,led in zip((MazePart.CIRCLE1, MazePart.CIRCLE2, MazePart.CIRCLE3),
                  (1,2,3)):
            for im, suf in zip((r,g,b),("R","G","B")):
                valid = self._region_map == reg
                im[valid] = np.clip(im[valid]+self._stats[f"Led{led}{suf}"], 0, 255)

        #b[self._region_map == self._stats["Region"]] = 255

        img_annotate = cv2.merge((b[::decimate,::decimate].astype(np.uint8), g[::decimate,::decimate].astype(np.uint8), r[::decimate,::decimate].astype(np.uint8)))
        h,w = img_annotate.shape[:2]

        current_region = self._stats["Region"]
        cv2.putText(img_annotate, f"{current_region}", (self._larva_loc/decimate).astype(int), cv2.FONT_HERSHEY_SIMPLEX, 1/decimate,
                    (255, 255, 0), 2)

        msg = f"L{self._decisions['light']} / D{self._decisions['dark']} / N{self._decisions['null']} ({self._last_msg_frame}: {self._last_msg})"
        cv2.putText(img_annotate, msg, (5, h - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5 / decimate, (255, 255, 255),
                    1, bottomLeftOrigin=False)

        #commented out area overlay to speed up processing
        # msg = f"area = {self._stats['LarvaArea']:.0f}"
        # msg2 = f"{self._stats['LarvaMeanArea']:.0f} +/- {self._stats['LarvaStdArea']:.1f}"
        # (text_width, text_height), baseline = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX, 0.5 / decimate, 1)
        # (text_width2, text_height), baseline = cv2.getTextSize(msg2, cv2.FONT_HERSHEY_SIMPLEX, 0.5 / decimate, 1)
        # cv2.putText(img_annotate, msg, np.array((w-text_width-5, baseline+text_height),dtype=np.uint16), cv2.FONT_HERSHEY_SIMPLEX, 0.5 / decimate, (255, 255, 255),1, bottomLeftOrigin=False)
        #
        # cv2.putText(img_annotate, msg2, np.array((w-text_width2-5, 2*baseline+2*text_height),dtype=np.uint16), cv2.FONT_HERSHEY_SIMPLEX, 0.5 / decimate, (255, 255, 255),1, bottomLeftOrigin=False)

        for r in self._regions:
            cv2.putText(img_annotate, f"{int(r.part)}", (r.loc/decimate).astype(int), cv2.FONT_HERSHEY_SIMPLEX, 0.5/decimate, (255, 255, 255), 1)
        if show_frame:
            cv2.putText(img_annotate, f"{self._frame_number}", (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5/decimate, (255, 255, 255), 1)
        return img_annotate

    def leds_on(self):
        return [np.any(np.asarray(l[0:3])>0) and l[3]>0 for l in self._led_settings]

    def mark_choice(self, channel):
        led_on = self.leds_on()
        if led_on[channel - 1]:
            choice = "light"
        else:
            if np.any(np.asarray(led_on)):
                choice = "dark"
            else:
                choice = "null"
        self._decisions[choice] += 1
        print(f"{self._maze_ID}: led states = {self.leds_on()}, channel chosen = {channel}, choice = {choice}")


    def num_choices(self):
        return self._decisions["light"], self._decisions["dark"], self._decisions["null"]

    def set_leds(self, led1rgb=None, led2rgb=None, led3rgb=None):
        self.set_ledrgbpct(1,led1rgb)
        self.set_ledrgbpct(2,led2rgb)
        self.set_ledrgbpct(3,led3rgb)


    def set_led(self, led_ind, red, green, blue, bright_pct=100):
        self._stats[f"Led{led_ind}R"] = red
        self._stats[f"Led{led_ind}G"] = green
        self._stats[f"Led{led_ind}B"] = blue
        self._stats[f"Led{led_ind}PCT"] = bright_pct
        self._led_settings[led_ind-1] = [red, green, blue, bright_pct]

        if self._light_controller is not None:
            self._light_controller.set_led(self._maze_ID, led_ind, red, green, blue, bright_pct)
            self._led_update = True
        self._last_led_update = time.monotonic()

    def set_ledrgbpct(self, led_ind, rgbpct):
        if rgbpct is None:
            return
        if len(rgbpct) > 3:
            self.set_led(led_ind, rgbpct[0], rgbpct[1], rgbpct[2], rgbpct[3])
        else:
            self.set_led(led_ind, rgbpct[0], rgbpct[1], rgbpct[2])

    def open_video_out(self, vidfilename):
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self._vid_writer = cv2.VideoWriter(vidfilename, fourcc, 30.0, (self._w, self._h), True)
        if self._vid_writer is not None:
            print(
                f"{vidfilename} writer open: {self._vid_writer.isOpened()}")  # , backend = {self._vid_writer.getBackendName()}")
        else:
            print(f"failed to open {vidfilename}")

    def close_video_out(self):
        if self._vid_writer is not None:
            self._vid_writer.release()
            self._vid_writer = None

    def _write_video(self):
        if self._vid_writer is not None:
            self._vid_writer.write(cv2.cvtColor(self._img, cv2.COLOR_GRAY2BGR))
