from typing import List

import cv2
import numpy as np
import pandas as pd

from BakCreator import BakCreator
from statemachine import StateMachine
from lightcontroller import LightController
from viterbi import Viterbi
from ymazegeometry import MazePart
from pathlib import Path

import csv
import _csv

import time

from threading import Lock

import matplotlib.pyplot as plt


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
        locs = self._get_region_centers()
        self._state_machine = StateMachine(locs[0], locs)
        self._stack_len = 60
        self._num_frames_to_initialize = self._stack_len
        self._threshold = 20
        self._larva_loc: np.ndarray = np.array([-1, -1])
        self._csvfile = None
        self._csvwriter: '_csv._writer' = None
        self._frame_number = 0
        self._vid_writer: cv2.VideoWriter = None
        self._img = np.zeros_like(self._region_map)
        self._larva_mask = np.zeros_like(self._region_map)
        self._region_sums = []
        self._region_baseline = np.zeros(self._num_regions)
        self._transition_probs = transition_probabilities
        self._state_history = None
        self._im_min = None
        self._larva_region: MazePart = MazePart.INTERSECTION
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
            "Led3PCT": 100
        }
        self._df = pd.DataFrame(columns=self._stats.keys())
        self._lock = Lock()

    def get_dataframe(self):
        return self._df

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

                self._calc_region_sums(img)
                # during initialization period, just update background
                if self._num_frames_to_initialize > 0:
                    self._bak.update_background(img)
                    self._num_frames_to_initialize -= 1
                    # print(f"{self._maze_ID}: frames left to initialize = {self._num_frames_to_initialize}")
                else:
                    thresh = cv2.bitwise_and(self._bak.get_thresholded_image(img, self._threshold), self._maze_mask)
                    self._bak.update_background(img, thresh, self._larva_mask)
                    self._updateLarva(thresh)
                self._write_video()
                self._df.loc[len(self._df)] = self._stats
            finally:
                self._lock.release()

    def _calc_region_sums(self, img):
        pxsum = np.zeros(self._num_regions + 1)
        for j in range(1, self._num_regions + 1):
            pxsum[j] = np.sum(img[self._region_map == j])
        self._region_sums.append(pxsum)

    def _calc_region_baseline(self, state_history=None):
        self._baseline = np.median(self._region_sums, axis=1)
        if state_history is None:
            return
        for i in range(1, self._num_regions + 1):
            rs = self._region_sums[i]
            v = self._transition_probs[i, state_history] == 0  # larva is known to be in a non-adjoining region
            if len(v) > 10:
                self._baseline[i] = np.median(rs[v])

    def calc_prob_sequence(self, debug=False):
        pobs = np.array(self._region_sums) - self._baseline[:, np.newaxis]
        pobs = np.clip(pobs, 0, np.inf)
        pdiv = np.sum(pobs, axis=1)
        pobs = pobs / pdiv[:, np.newaxis]
        pobs[:, 0] = 0
        v = Viterbi(self._transition_probs)
        pseq = v.decode(pobs)
        if debug:
            plt.subplot(3, 1, 1)
            plt.plot(np.arange(len(pseq)), self._region_sums - self._baseline[:, np.newaxis])
            plt.subplot(3, 1, 2)
            plt.plot(np.arange(len(pseq)), pobs)
            plt.subplot(3, 1, 3)
            plt.plot(np.arange(len(pseq)), pseq)

        return pseq

    def _updateLarva(self, thresh):
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            thresh, connectivity=8
        )
        area = [stats[i, cv2.CC_STAT_AREA] for i in range(1, num_labels)]
        try:
            larva_ind = np.argmax(area) + 1
            self._larva_loc = centroids[larva_ind]
            self._larva_mask = (labels == larva_ind).astype(np.uint8) * 255
            self._stats["LarvaArea"] = float(area[larva_ind - 1])
        except:
            larva_ind = 1
            self._larva_loc = np.array([-1, -1])

        # self._calc_region_baseline(self._state_history)
        # self._state_history = self.calc_prob_sequence()
        # self._stats["Region"] = self._state_history[-1]

        prevnumber, number, nextnum = self._state_machine.on_input(
            self._larva_loc)  # state numbers differ from region numbers by 1 in statemachine/regions vs. pdf
        self._stats["Region"] = number + 1
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
        r = self._img.copy()
        r[self._larva_mask > 0] = 255
        b = self._img.copy()
        b[self._region_map == self._stats["Region"]] = 255
        img_annotate = cv2.merge((b, self._img, r))
        current_region = self._stats["Region"]
        cv2.putText(img_annotate, f"{current_region}", self._larva_loc.astype(int), cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (255, 255, 0), 2)
        for j in range(len(self._state_machine.locs)):
            rr = self._state_machine.locs[j].astype(int)
            cv2.putText(img_annotate, f"{j + 1}", rr, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(img_annotate, f"{self._frame_number}", (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        return img_annotate

    def debug_plots(self):
        plt.subplot(3, 1, 1)
        plt.plot(self._region_sums)
        plt.subplot(3, 1, 1)
        plt.plot(self._cal)

    # def open_csv(self, filename):
    #     self._csvfile = open(filename, 'w', newline='')
    #     self._csvwriter = csv.writer(self._csvfile, delimiter='\t')
    #     self._csvwriter.writerow(self._stats.keys())
    #
    # def close_csv(self):
    #     self._csvwriter = None
    #     self._csvfile = None
    #
    # def _write_state_to_text(self):
    #     if self._csvwriter is not None:
    #         try:
    #             self._csvwriter.writerow(self._stats.values())
    #         except TimeoutError:
    #             pass # nothing
    def set_leds(self, led1rgb=None, led2rgb=None, led3rgb=None):
        self.set_ledrgbpct(1, led1rgb)
        self.set_ledrgbpct(2,led2rgb)
        self.set_ledrgbpct(3,led3rgb)
        # if led1rgb is not None:
        #     if len(led1rgb > 3):
        #         self.set_led(1, led1rgb[0], led1rgb[1], led1rgb[2], led1rgb[3])
        #     else:
        #         self.set_led(1, led1rgb[0], led1rgb[1], led1rgb[2])
        # if led2rgb is not None:
        #     if len(led2rgb > 3):
        #         self.set_led(2, led2rgb[0], led2rgb[1], led2rgb[2], led2rgb[3])
        #     else:
        #         self.set_led(2, led2rgb[0], led2rgb[1], led2rgb[2])
        # if led3rgb is not None:
        #     if len(led3rgb > 3):
        #         self.set_led(3, led3rgb[0], led3rgb[1], led3rgb[2], led3rgb[3])
        #     else:
        #         self.set_led(3, led3rgb[0], led3rgb[1], led3rgb[2])

    def set_led(self, led_ind, red, green, blue, bright_pct=100):
        self._stats["LED" + led_ind + "R"] = red
        self._stats["LED" + led_ind + "G"] = green
        self._stats["LED" + led_ind + "B"] = blue
        self._stats["LED" + led_ind + "PCT"] = bright_pct
        if self._light_controller is not None:
            self._light_controller.set_led(self._maze_ID, led_ind, red, green, blue, bright_pct)

    def set_ledrgbpct(self, led_ind, rgbpct):
        if rgbpct is None:
            return
        if len(rgbpct > 3):
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
        self._vid_writer.release()
        self._vid_writer = None

    def _write_video(self):
        if self._vid_writer is not None:
            self._vid_writer.write(self.debug_image())
