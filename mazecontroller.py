from typing import List

import numpy as np
from numpy import ndarray

from BakCreator import BakCreator
from statemachine import StateMachine


class MazeController:
    def __init__(self, light_controller, region_map):
        self._bak = None
        self._light_controller = light_controller
        self._region_map = region_map
        self._w, self._h = self._region_map.shape
        [self._x, self._y] = np.meshgrid(np.arange(self._w), np.arange(self._h))
        self._num_regions = np.max(region_map)
        locs = self._get_region_centers()
        self._state_machine = StateMachine(locs[0], locs)
        self._output

    def _get_region_centers(self):
        locs: list[ndarray] = []
        for j in range(self._num_regions):
            x = np.mean(self._x(self._region_map == j))
            y = np.mean(self._y(self._region_map == j))
            locs.append(np.array([x, y]))
        return locs

    def newImage(self, img):
        if self._bak is None:
            self._bak = BakCreator()