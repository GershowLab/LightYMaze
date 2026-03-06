import time

import lightcontroller
import ymazegeometry
from mazecontroller import MazeController
import cv2
import numpy as np
from dataclasses import dataclass
from threading import Thread

class MazeDispatcher:
    def __init__(self, ymg:ymazegeometry.YMazeGeometry, light_controller:lightcontroller.LightController = None):
        self._ymg = ymg
        self._maze_mask, self._region_mask = ymg.generate_maze_mask()
        self._maze_minions = [MazeMinion(i, self._maze_mask, self._region_mask, self._light_controller) for i in range(1,np.max(self._maze_mask))]
        self._frame_number = 0

    def open_csv(self, fstub):
        for mm in self._maze_minions:
            mm.open_csv(fstub)

    def open_video(self, fstub):
        for mm in self._maze_minions:
            mm.open_video(fstub)

    def close_csv(self):
        for mm in self._maze_minions:
            mm.close_csv()

    def close_video(self):
        for mm in self._maze_minions:
            mm.close_video()

    def new_frame(self, img:np.ndarray,frame_number:int = None, frame_time:float = None):
        if frame_number is None:
            self._frame_number += 1
        else:
            self._frame_number = frame_number
        if frame_time is None:
            frame_time = time.monotonic()
        for mm in self._maze_minions:
            mm.new_frame(img, frame_number,frame_time)



class MazeMinion:
    def __init__(self, maze_id, maze_mask, region_mask, light_controller = None):
        self._x, self._y, self._w, self._h = cv2.boundingRect(maze_mask == maze_id)
        self._maze_id = maze_id
        self._maze_controller = MazeController(light_controller, self.get_subim(region_mask).copy(), maze_id)

    def get_subim(self, img):
        return img[self._y:(self._y+self._h), self._x:(self._x + self._w)]
    def new_frame(self, img, frame_number = None, frame_time = None):
        roi = self.get_subim(img).copy()
        t = Thread(target=self._maze_controller.new_image, args=(roi, frame_number, frame_time))
        t.start() # maze_controller.new_image returs immediately if processing another frame

    def open_csv(self, fstub):
        self._maze_controller.open_csv(fstub + self._maze_id + ".csv")

    def close_csv(self):
        self._maze_controller.close_csv()

    def open_video(self, fstub):
        self._maze_controller.open_video_out(fstub + self._maze_id + ".mp4")

    def close_video(self):
        self._maze_controller.close_video_out()



@dataclass
class img_cap:
    img : np.ndarray
    frame_number : int
    frame_time : float


