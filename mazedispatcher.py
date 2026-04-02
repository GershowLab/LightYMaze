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
        self._composite = None
        self._composite_w = -1
        self._composite_h = -1
        self._panel_w = -1
        self._panel_h = -1
        self._composite_ncol = np.uint16(3)
        self._composite_nrow = np.uint16(3)
        self._vid_writer = None

    def set_composite_dimensions(self):
        dims = np.array([mm.get_dimensions() for mm in self._maze_minions], np.uint8)
        self._panel_w,self._panel_h = np.max(dims, axis=0)
        self._composite_nrow = np.uint16(np.ceil(len(self._maze_minions) / self._composite_ncol))
        self._composite_w = self._panel_w*self._composite_ncol
        self._composite_h = self._panel_h*self._composite_nrow

    def get_composite_image(self):
        return self._composite

    def make_composite_image(self):

        if self._composite_w <= 0:
            self.set_composite_dimensions()

        if self._composite is None:
            self._composite = np.zeros((self._composite_h, self._composite_w,3), np.uint8)
        for j in range(len(self._maze_minions)):
            x0 = np.uint16((j%self._composite_ncol)*self._panel_w)
            y0 = np.uint16(np.floor(j/self._composite_ncol)*self._panel_h)
            img = self._maze_minions[j].get_debug_im()
            imh,imw = img.shape[:2]
            #print(f"im{j+1} {imw},{imh}")
            self._composite[y0:(y0+imh),x0:(x0+imw),:] = img
        return self._composite


    # def open_csv(self, fstub):
    #     for mm in self._maze_minions:
    #         mm.open_csv(fstub)

    def open_video(self, fstub):
        for mm in self._maze_minions:
            mm.open_video(fstub)
        vidfilename = f"{fstub} all mazes.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        if self._composite_w <= 0:
            self.set_composite_dimensions()
        self._vid_writer = cv2.VideoWriter(vidfilename, fourcc, 30.0, (self._composite_w, self._composite_h), True)
        if self._vid_writer is not None:
            print(
                f"{vidfilename} writer open: {self._vid_writer.isOpened()}")  # , backend = {self._vid_writer.getBackendName()}")
        else:
            print(f"failed to open {vidfilename}")

    def write_video(self):
        img = self.make_composite_image()
        if self._vid_writer is not None:
            self._vid_writer.write(img)

    def close_video(self):
        for mm in self._maze_minions:
            mm.close_video()
        if self._vid_writer is not None:
            self._vid_writer.release()
            self._vid_writer = None
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
        self._pad = 12
        x,y,w,h = cv2.boundingRect(((maze_mask == maze_id) * 255).astype(np.uint8))
        self._x = np.clip(x-self._pad,0,None)
        self._y = np.clip(y-self._pad,0,None)
        self._w = np.clip(w+2*self._pad,None,maze_mask.shape[1]-self._x)
        self._h = np.clip(h+2*self._pad,None,maze_mask.shape[0]-self._y)
        self._maze_id = maze_id
        self._maze_controller = MazeController(light_controller, self.get_subim(region_mask).copy(), transition_probs, maze_id, self._pad)


    def get_dimensions(self):
        return (self._w, self._h)

    def get_subim(self, img):
        return img[self._y:(self._y+self._h), self._x:(self._x + self._w)]

    def get_debug_im(self):
        img = self._maze_controller.debug_image()
        text = f"M{self._maze_id}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1
        thickness = 1
        (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        h,w = img.shape[:2]
        x = w - text_w - 2
        y = text_h + 2
        # Draw text
        cv2.putText(img, text, (x, y), font, font_scale, (255, 255, 255), thickness)
        return img

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



