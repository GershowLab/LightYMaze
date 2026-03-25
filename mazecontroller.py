
import cv2
import numpy as np
import pandas as pd

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
                 maze_ID: int):
        self._maze_ID = maze_ID
        self._bak: BakCreator = None
        self._light_controller = light_controller
        self._region_map = region_map.astype(np.uint8)
        self._maze_mask = 255 * (self._region_map > 0).astype(
            np.uint8)  # cv2.morphologyEx((self._region_map > 0).astype(np.uint8), cv2.MORPH_DILATE, np.ones((5,5), np.uint8))
        self._h, self._w = self._region_map.shape  # row x col
        [self._x, self._y] = np.meshgrid(np.arange(self._w), np.arange(self._h))
        self._num_regions = np.max(region_map).astype(np.uint8)
        # locs = self._get_region_centers()
        # self._state_machine = StateMachine(locs[0], locs)
        self._stack_len = 10
        self._bak_initialized = False
        self._threshold = 20
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
            "Message":""
        }
        self._df = pd.DataFrame(columns=self._stats.keys())
        self._lock = Lock()
        self._stimulus_manager = stimulusmanager.StimulusManager(self)
        self._last_msg_frame = -1000
        self._last_msg = "no message"
        self._set_regions()
        self._led_update = False

    def get_dataframe(self):
        df = self._df.copy()
        #try:
        path = self._viterbi.most_likely_path()
        p = np.zeros_like(df['Frame'])
        p[-(len(path)+1):-1] = np.asarray(path)+1
        df['viterbi_path'] = p
        #finally:
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

    def new_image(self, img, frame_number=None, capture_time=None):
        if self._lock.acquire(blocking=False):
            try:
                self._img = img  # pass a copy to new_image
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
                    self._bak = BakCreator(self._stack_len, 0.1, img)
                    self._bak.set_update_intervals(self._update_frame_interval, self._update_time_interval)

                # during initialization period, just update background
                if not self._bak_initialized:
                    self._bak_initialized = self._bak.update_background(img)
                else:
                    thresh = cv2.bitwise_and(self._bak.get_thresholded_image(img, self._threshold), self._maze_mask)
                    self._bak.update_background(img, thresh, self._larva_mask)
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
                if self._led_update and self._light_controller is not None:
                    self._light_controller.update_leds()
                    self._led_update = False
            finally:
                self._lock.release()

    def _update_larva(self, thresh):
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            thresh, connectivity=8
        )
        area = [stats[i, cv2.CC_STAT_AREA] for i in range(1, num_labels)]
        try:
            larva_ind = np.argmax(area) + 1
            self._larva_loc = centroids[larva_ind]
            self._larva_mask = (labels == larva_ind).astype(np.uint8) * 255
            self._stats["LarvaArea"] = float(area[larva_ind - 1])
            log_p_obs = [r.logP(self._larva_loc) for r in self._regions]
            self._larva_region = self._viterbi.new_obs(log_p_obs) + 1
        except:
            self._larva_loc = np.array([-1, -1])
        self._stats["Region"] = self._larva_region
        self._stats["LarvaX"] = float(self._larva_loc[0])
        self._stats["LarvaY"] = float(self._larva_loc[1])


    def get_larva_region(self):
        return self._larva_region

    def debug_montage(self):
        img = cv2.cvtColor(self._img, cv2.COLOR_GRAY2BGR)
        bak = cv2.cvtColor(self._bak.get_background(), cv2.COLOR_GRAY2BGR)
        thresh = cv2.cvtColor(self._bak.get_thresholded_image(self._img, self._threshold), cv2.COLOR_GRAY2BGR)
        img_annotate = self.debug_image()
        montage = np.vstack((np.hstack((img, bak)), np.hstack((thresh, img_annotate))))
        return montage

    def debug_image(self):
        r = self._img.copy().astype(np.uint16)
        r[self._larva_mask > 0] = 255
        b = self._img.copy().astype(np.uint16)
        g = self._img.copy().astype(np.uint16)

        h,w = self._img.shape
        for reg,led in zip((MazePart.CIRCLE1, MazePart.CIRCLE2, MazePart.CIRCLE3),
                  (1,2,3)):
            for im, suf in zip((r,g,b),("R","G","B")):
                valid = self._region_map == reg
                im[valid] = np.clip(im[valid]+self._stats[f"Led{led}{suf}"], 0, 255)

        #b[self._region_map == self._stats["Region"]] = 255

        img_annotate = cv2.merge((b.astype(np.uint8), g.astype(np.uint8), r.astype(np.uint8)))
        current_region = self._stats["Region"]
        cv2.putText(img_annotate, f"{current_region}", self._larva_loc.astype(int), cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (255, 255, 0), 2)
        if self._frame_number < self._last_msg_frame + 30:
            cv2.putText(img_annotate, self._last_msg, (5, h-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255),
                        1, bottomLeftOrigin=False)

        for r in self._regions:
            cv2.putText(img_annotate, f"{int(r.part)}", r.loc.astype(int), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(img_annotate, f"{self._frame_number}", (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        return img_annotate


    def set_leds(self, led1rgb=None, led2rgb=None, led3rgb=None):
        self.set_ledrgbpct(1,led1rgb)
        self.set_ledrgbpct(2,led2rgb)
        self.set_ledrgbpct(3,led3rgb)


    def set_led(self, led_ind, red, green, blue, bright_pct=100):
        self._stats[f"Led{led_ind}R"] = red
        self._stats[f"Led{led_ind}G"] = green
        self._stats[f"Led{led_ind}B"] = blue
        self._stats[f"Led{led_ind}PCT"] = bright_pct
        if self._light_controller is not None:
            self._light_controller.set_led(self._maze_ID, led_ind, red, green, blue, bright_pct)
            self._led_update = True

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
            self._vid_writer.write(self.debug_image())
