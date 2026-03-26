import time

import pandas as pd

from lightcontroller import LightController
from ymazegeometry import YMazeGeometry
from mazecontroller import MazeController
import cv2
import numpy as np
from threading import Thread
import matplotlib.pyplot as plt

class MazeDispatcher:
    def __init__(self, ymg:YMazeGeometry, light_controller:LightController = None):
        self._ymg = ymg
        self._maze_mask, self._region_mask = ymg.get_maze_mask()
        self._light_controller = light_controller
        self._maze_minions = [MazeMinion(i, self._maze_mask, self._region_mask, ymg.generate_connectivity_matrix(0.01), self._light_controller) for i in range(1,1+np.max(self._maze_mask).astype(int))]
        self._frame_number = 0

    # def open_csv(self, fstub):
    #     for mm in self._maze_minions:
    #         mm.open_csv(fstub)

    def open_video(self, fstub):
        for mm in self._maze_minions:
            mm.open_video(fstub)

    # def close_csv(self):
    #     for mm in self._maze_minions:
    #         mm.close_csv()

    def close_video(self):
        for mm in self._maze_minions:
            mm.close_video()

    # def save_regions(self,fstub):
    #     for mm in self._maze_minions:
    #         mm.save_region_sums(fstub)

    def get_data_frame(self):
        df = [mm.get_dataframe() for mm in self._maze_minions]
        return pd.concat(df)

    def new_frame(self, img:np.ndarray,frame_number:int = None, frame_time:float = None, wait_for_completion = False, multi_thread = True):
        if frame_number is None:
            self._frame_number += 1
        else:
            self._frame_number = frame_number
        if frame_time is None:
            frame_time = time.monotonic()
        #print(f"maze dispatcher img shape = {img.shape}")
        if multi_thread:
            tt = [mm.new_frame(img, frame_number,frame_time) for mm in self._maze_minions]
            if wait_for_completion:
                for t in tt:
                    t.join()
        else:
            for mm in self._maze_minions:
                mm.new_frame_nothread(img, frame_number, frame_time)
            tt = None
        if  self._light_controller is not None:
            self._light_controller.update_leds()
        return tt






class MazeMinion:
    def __init__(self, maze_id, maze_mask, region_mask, transition_probs, light_controller = None):
        self._x, self._y, self._w, self._h = cv2.boundingRect(((maze_mask == maze_id) * 255).astype(np.uint8))
        self._maze_id = maze_id
        self._maze_controller = MazeController(light_controller, self.get_subim(region_mask).copy(), transition_probs, maze_id)

    def get_subim(self, img):
        return img[self._y:(self._y+self._h), self._x:(self._x + self._w)]

    def new_frame_nothread(self, img, frame_number = None, frame_time = None):
        roi = self.get_subim(img).copy()
        #print(f'maze minion {self._maze_id} roi.shape = {roi.shape}')
        self._maze_controller.new_image(roi, frame_number, frame_time)
    def new_frame(self, img, frame_number = None, frame_time = None):
        roi = self.get_subim(img).copy()
        t = Thread(target=self._maze_controller.new_image, args=(roi, frame_number, frame_time))
        t.start() # maze_controller.new_image returns immediately if processing another frame
        return t

    def save_region_sums(self, fstub):
        np.savetxt(f"{fstub}{self._maze_id}regions.txt",self._maze_controller._region_sums)
    # def open_csv(self, fstub):
    #     self._maze_controller.open_csv(f"{fstub}{self._maze_id}.csv")
    #
    # def close_csv(self):
    #     self._maze_controller.close_csv()

    def get_dataframe(self) -> pd.DataFrame:
        return self._maze_controller.get_dataframe()

    def open_video(self, fstub):
        self._maze_controller.open_video_out(f"{fstub}{self._maze_id}.mp4")

    def close_video(self):
        self._maze_controller.close_video_out()

    def debug_display(self):
        winname = f"Maze{self._maze_id} Debug"
        cv2.namedWindow(winname, cv2.WINDOW_NORMAL)
        img = self._maze_controller.debug_montage()
        cv2.imshow(winname, img)
        return winname



