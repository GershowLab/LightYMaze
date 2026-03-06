from typing import List

import cv2
import numpy as np
from numpy import ndarray

from BakCreator import BakCreator
from statemachine import StateMachine
from lightcontroller import LightController

import csv
import _csv

import time

from threading import Lock

class MazeController:
    _vid_writer: cv2.VideoWriter

    def __init__(self, light_controller: LightController, region_map: ndarray, maze_ID):
        self._maze_ID = maze_ID
        self._bak:BakCreator = None
        self._light_controller = light_controller
        self._region_map = region_map
        self._w, self._h = self._region_map.shape
        [self._x, self._y] = np.meshgrid(np.arange(self._w), np.arange(self._h))
        self._num_regions = np.max(region_map).astype(int)
        locs = self._get_region_centers()
        self._state_machine = StateMachine(locs[0], locs)
        self._stack_len = 60
        self._num_frames_to_initialize =  self._stack_len
        self._threshold = 30
        self._larva_loc:ndarray = np.array([-1,-1])
        self._csvfile = None
        self._csvwriter: '_csv._writer' = None
        self._frame_number = 0
        self._vid_writer: cv2.VideoWriter = None
        self._img = None
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
        self._lock = Lock()

    def _get_region_centers(self):
        locs: list[ndarray] = []
        for j in range(self._num_regions):
            x = np.mean(self._x[self._region_map == j])
            y = np.mean(self._y[self._region_map == j])
            locs.append(np.array([x, y]))
        return locs

    def new_image(self, img, frame_number = None, capture_time = None):
        if self._lock.acquire(blocking=False):
            self._img = img # pass a copy to new_image
            if frame_number is None:
                self._frame_number += 1
            else:
                self._frame_number = frame_number
            if capture_time is None:
                self._stats["FrameTime"] = time.monotonic()
            else:
                self._stats["FrameTime"]  = capture_time
            if self._bak is None:
                self._bak = BakCreator(self._stack_len, 0.02, img)
            #during initialization period, just update background
            if (self._num_frames_to_initialize > 0):
                self._bak.updageBackground(img)
                self._num_frames_to_initialize -= 1
                return
            thresh = self._bak.getThresholdedImage(img)
            self._bak.updageBackground(img, thresh)
            self._stats["Frame"] = self._frame_number
            self._updateLarva(thresh)
            self._write_video()
            self._write_data()
            self._lock.release()

    def _updateLarva(self, thresh):
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            thresh, connectivity=8
        ) # , ltype=cv2.CV_32S
        area = [stats[i, cv2.CC_STAT_AREA] for i in range(1,num_labels)]
        larva_ind = np.argmax(area) + 1
        self._larva_loc = centroids[larva_ind]
        self._larva_mask = (labels == larva_ind)
        prevnumber, number, nextnum = self._state_machine.on_input(self._larva_loc)
        self._stats["Region"] = number
        self._stats["LarvaX"],self._stats["LarvaY"] = self._larva_loc

    def open_csv(self, filename):
        self._csvfile = open(filename, 'w', newline='')
        self._csvwriter = csv.writer(self._csvfile, delimiter=', ')
        self._csvwriter.writerow(self._stats.keys())

    def close_csv(self):
        self._csvfile.close()
        self._csvwriter = None
        self._csvfile = None

    def _write_state_to_text(self):
        if self._csvwriter is not None:
            self._csvwriter.writerow(self._stats.values())

    def _set_leds(self, led1rgb = None, led2rgb = None, led3rgb = None):
        if led1rgb is not None:
            self._set_led(1, led1rgb[0], led1rgb[1],led1rgb[2])
        if led2rgb is not None:
            self._set_led(2, led2rgb[0], led2rgb[1], led2rgb[2])
        if led3rgb is not None:
            self._set_led(3, led3rgb[0], led3rgb[1], led3rgb[2])

    def _set_led(self, led_ind, red, green, blue, bright_pct = 100):
        self._stats["LED"+led_ind+"R"] = red
        self._stats["LED" + led_ind + "G"] = green
        self._stats["LED" + led_ind + "B"] = blue
        self._stats["LED" + led_ind + "PCT"] = bright_pct
        if self._light_controller is not None:
            self._light_controller.set_led(self._maze_ID, led_ind, red, green, blue, bright_pct)

    def open_video_out(self, vidfilename):
        fourcc = cv2.VideoWriter_fourcc('MP4V')
        self._vid_writer = cv2.VideoWriter(vidfilename, fourcc, 30.0, (self._w, self._h), False)

    def close_video_out(self):
        self._vid_writer.release()
        self._vid_writer = None

    def _write_video(self):
        if self._vid_writer is not None:
            self._vid_writer.write(self._img)
        #TODO annotate

    def _write_data(self):
        self._write_state_to_text()
        self._write_video()










