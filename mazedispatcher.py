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
    def __init__(self, ymg:YMazeGeometry, light_controller:LightController = None, choice1rgb = (0,0,0), choice2rgb = (0,0,255)):
        self._ymg = ymg
        self._maze_mask, self._region_mask = ymg.get_maze_mask()
        self._light_controller = light_controller
        self._maze_minions = [MazeMinion(i, self._maze_mask, self._region_mask, ymg.generate_connectivity_matrix(0.01), self._light_controller, choice1rgb, choice2rgb) for i in range(1,1+np.max(self._maze_mask).astype(int))]
        self._frame_number = 0
        self._composite = None
        self._img = None
        [self._img_h, self._img_w] = np.asarray(ymg.im_size_px, np.uint16)
        self._composite_w = -1
        self._composite_h = -1
        self._panel_w = -1
        self._panel_h = -1
        self._composite_ncol = np.uint16(3)
        self._composite_nrow = np.uint16(3)
        self._vid_writer = None
        self._save_raw = False

    def set_save_raw(self, save_raw):
        if self._vid_writer is None:
            self._save_raw = save_raw
        else:
            print ("Warning: can't change raw/composite option once vid writer is open")

    def set_composite_dimensions(self):
        #we will reduce the number of pixels in the image to make it go faster
        dims = np.array([mm.get_dimensions() for mm in self._maze_minions], np.uint16)
        self._panel_w,self._panel_h = np.ceil(np.max(dims, axis=0)/2)
        self._composite_nrow = np.uint16(np.ceil(len(self._maze_minions) / self._composite_ncol))
        self._composite_w = np.uint16(self._panel_w*self._composite_ncol)
        self._composite_h = np.uint16(self._panel_h*self._composite_nrow)

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
            img = self._maze_minions[j].get_debug_im(decimate=2,show_frame=False)
            imh,imw = img.shape[:2]
            self._composite[y0:(y0+imh),x0:(x0+imw),:] = img
        return self._composite

    def enable_stim_manager(self, enable):
        [mm.enable_stim_manager(enable) for mm in self._maze_minions]

    def enable_background_update(self, enable):
        [mm.enable_background_update(enable) for mm in self._maze_minions]

    def enable_tracking(self, enable):
        [mm.enable_tracking(enable) for mm in self._maze_minions]

    def set_all_leds(self, rgbpct):
        self.set_leds_all_mazes(rgbpct,rgbpct,rgbpct)

    def set_leds_all_mazes(self, led1rgbpct, led2rgbpct, led3rgbpct):
        [mm.set_leds(led1rgbpct,led2rgbpct,led3rgbpct) for mm in self._maze_minions]
        if self._light_controller is not None:
            self._light_controller.update_leds()

    def set_leds_one_maze(self, maze_id, led1rgbpct, led2rgbpct, led3rgbpct, update = True):
        for mm in self._maze_minions:
            if mm._maze_id == maze_id:
                mm.set_leds(led1rgbpct, led2rgbpct, led3rgbpct)
        if update and self._light_controller is not None:
            self._light_controller.update_leds()

    def open_video(self, fstub):
        for mm in self._maze_minions:
            mm.open_video(fstub)
        vidfilename = f"{fstub} all mazes.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        if self._composite_w <= 0:
            self.set_composite_dimensions()
        if self._save_raw:
            print (f"self._img_w, self._img_h = {self._img_w, self._img_h}")
            self._vid_writer = cv2.VideoWriter(vidfilename, fourcc, 30.0, (self._img_w, self._img_h), True)
        else:
            self._vid_writer = cv2.VideoWriter(vidfilename, fourcc, 30.0, (self._composite_w, self._composite_h), True)
        if self._vid_writer is not None:
            print(
                f"{vidfilename} writer open: {self._vid_writer.isOpened()}")  # , backend = {self._vid_writer.getBackendName()}")
            print (f"vid writer size = {self._vid_writer.get(cv2.CAP_PROP_FRAME_WIDTH),self._vid_writer.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
        else:
            print(f"failed to open {vidfilename}")

    def write_video(self):
        if self._save_raw:
            img = cv2.cvtColor(np.asarray(self._img, np.uint8), cv2.COLOR_GRAY2BGR)
            print (f"saving video img size (h,w) = {img.shape[:2]}")
        else:
            img = self.make_composite_image()
        if self._vid_writer is not None:
            self._vid_writer.write(img)
        else:
            print ("vid writer is not open")


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

    def num_choices(self):
        return [mm.num_choices() for mm in self._maze_minions]

    def new_frame(self, img:np.ndarray,frame_number:int = None, frame_time:float = None, wait_for_completion = False, multi_thread = True):
        if frame_number is None:
            self._frame_number += 1
        else:
            self._frame_number = frame_number
        if frame_time is None:
            frame_time = time.monotonic()
        if self._img is None:
            self._img = img.copy()
        else:
            self._img[:] = img
        if multi_thread:
            tt = [mm.new_frame(self._img, frame_number=frame_number,frame_time=frame_time) for mm in self._maze_minions]
            if wait_for_completion:
                for t in tt:
                    t.join()
        else:
            for mm in self._maze_minions:
                mm.new_frame_nothread(self._img, frame_number=frame_number, frame_time=frame_time)
            tt = None
        if  self._light_controller is not None:
            self._light_controller.update_leds()
        return tt






class MazeMinion:
    def __init__(self, maze_id, maze_mask, region_mask, transition_probs, light_controller = None, choice1rgb = (0,0,0), choice2rgb = (0,0,255)):
        self._pad = 12
        x,y,w,h = cv2.boundingRect(((maze_mask == maze_id) * 255).astype(np.uint8))
        self._x = np.clip(x-self._pad,0,None)
        self._y = np.clip(y-self._pad,0,None)
        self._w = np.clip(w+2*self._pad,None,maze_mask.shape[1]-self._x)
        self._h = np.clip(h+2*self._pad,None,maze_mask.shape[0]-self._y)
        self._maze_id = maze_id
        self._maze_controller = MazeController(light_controller, self.get_subim(region_mask).copy(), transition_probs, maze_id, self._pad, choice1rgb, choice2rgb=choice2rgb)

    def enable_stim_manager(self, enable):
        self._maze_controller.enable_stim_manager(enable)

    def enable_background_update(self, enable):
        self._maze_controller.enable_background_update(enable)

    def enable_tracking(self, enable):
        self._maze_controller.enable_tracking(enable)

    def get_dimensions(self):
        return (self._w, self._h)

    def get_subim(self, img):
        return img[self._y:(self._y+self._h), self._x:(self._x + self._w)]

    def get_debug_im(self, decimate = 1, show_frame = True):
        img = self._maze_controller.debug_image(decimate, show_frame)
        text = f"M{self._maze_id}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1/decimate
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
        self._maze_controller.new_image(roi, frame_number, frame_time)
    def new_frame(self, img, frame_number = None, frame_time = None):
        roi = self.get_subim(img).copy()
        t = Thread(target=self._maze_controller.new_image, args=(roi, frame_number, frame_time))
        t.start() # maze_controller.new_image returns immediately if processing another frame
        return t

    def save_region_sums(self, fstub):
        np.savetxt(f"{fstub}{self._maze_id}regions.txt",self._maze_controller._region_sums)

    def get_dataframe(self) -> pd.DataFrame:
        return self._maze_controller.get_dataframe()

    def open_video(self, fstub):
        self._maze_controller.open_video_out(f"{fstub}{self._maze_id}.mp4")

    def close_video(self):
        self._maze_controller.close_video_out()

    def num_choices(self):
        return self._maze_controller.num_choices()

    def set_leds(self, led1rgb=None, led2rgb=None, led3rgb=None):
        self._maze_controller.set_leds(led1rgb, led2rgb, led3rgb)

    def debug_display(self):
        if self._maze_controller.initialized():
            winname = f"Maze{self._maze_id} Debug"
            cv2.namedWindow(winname, cv2.WINDOW_NORMAL)
            img = self._maze_controller.debug_montage()
            h,w = img.shape[:2]
            cv2.imshow(winname, img)
            return winname, np.array((w,h))
        else:
            return None, np.array((0,0))



