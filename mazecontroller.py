from typing import List

import cv2
import numpy as np
from numpy import ndarray

from BakCreator import BakCreator
from statemachine import StateMachine
from lightcontroller import LightController

import csv
import _csv
class MazeController:
    def __init__(self, light_controller: LightController, region_map: ndarray):
        self._bak:BakCreator = None
        self._light_controller = light_controller
        self._region_map = region_map
        self._w, self._h = self._region_map.shape
        [self._x, self._y] = np.meshgrid(np.arange(self._w), np.arange(self._h))
        self._num_regions = np.max(region_map)
        locs = self._get_region_centers()
        self._state_machine = StateMachine(locs[0], locs)
        self._num_frames_to_initialize = 100
        self._threshold = 30
        self._larva_loc:ndarray = np.array([-1,-1])
        self._csvfile = None
        self._csvwriter: '_csv._writer' = None
        self._stats = {
            "Frame": 0,
            "LarvaX": -1,
            "LarvaY": -1,
            "LarvaArea": -1,
            "Region": -1,
            "Led1R": 0,
            "Led1G": 0,
            "Led1B": 0,
            "Led2R": 0,
            "Led2G": 0,
            "Led2B": 0,
            "Led3R": 0,
            "Led3G": 0,
            "Led3B": 0
        }
    def _get_region_centers(self):
        locs: list[ndarray] = []
        for j in range(self._num_regions):
            x = np.mean(self._x(self._region_map == j))
            y = np.mean(self._y(self._region_map == j))
            locs.append(np.array([x, y]))
        return locs

    def newImage(self, img):
        if self._bak is None:
            self._bak = BakCreator(img)
        #during initialization period, just update background
        if (self._num_frames_to_initialize > 0):
            self._bak.updageBackground(img)
            self._num_frames_to_initialize -= 1
            return
        thresh = self._bak.getThresholdedImage(img)
        self._bak.updageBackground(img, thresh)
        self._updateLarva(thresh)
    def _updateLarva(self, thresh):
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            thresh, connectivity=8, ltype=cv2.CV_32S
        )
        area = [stats[i, cv2.CC_STAT_AREA] for i in range(1,num_labels)]
        larva_ind = np.argmax(area) + 1
        self._larva_loc = centroids[larva_ind]
        self._larva_mask = (labels == larva_ind)
        prevnumber, number, nextnum = self._state_machine.on_input(self._larva_loc)
        self._stats["Region"] = number
        self._stats["LarvaX"],self._stats["LarvaY"] = self._larva_loc
    def openCSV(self, filename):
        self._csvfile = open(filename, 'w', newline='')
        self._csvwriter = csv.writer(self._csvfile, delimiter=', ')
        self._csvwriter.writerow(self._stats.keys())


    def closeCSV(self):
        self._csvfile.close()
        self._csvwriter = None
        self._csvfile = None
    def _writeStateToText(self):
        if self._csvwriter is not None:
            self._csvwriter.writerow(self._stats.values())





