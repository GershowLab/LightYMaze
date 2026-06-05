#TODO: logging instead of printf debugs
#TODO: parameters saved in file

import os

import numpy as np

import cv2

from imagestabilizer import ImageStabilizer
from mazedispatcher import MazeDispatcher
from trainingprotocol import TrainingProtocol, TemporalTrainingProtocol
from ymazegeometry import YMazeGeometry
from pathlib import Path
from lightcontroller import LightController
from datetime import datetime



class LiveTracker:
	def __init__(self, basedir = Path.home(), cap = None):
		if cap is None:
			from cameracapture import CameraCapture
			self.cap = CameraCapture()
		else:
			self.cap = cap
		self.basedir = basedir
		self.text_dir = ''
		self.video_dir = ''
		self.lens_position = 1/.0768
		self.default_win_size = (640, 480)
		self.ymg = None
		self.light_controller = LightController()
		self.brightness = 9
		self.light_controller.set_global_brightness(self.brightness)
		self.experiment_duration = 3600
		self.time_stamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
		self.md = None
		self.t0 = 0
		self.barrel_alpha = -0.000032 #todo this should not be hardcoded this way
		self.imstab = None
		self.stabilizer_alpha = 0.01

	def __del__(self):
		pass


	def full_conditioning_experiment(self, paired = True):
		if paired:
			protocol = TemporalTrainingProtocol.standard_paired_protocol()
		else:
			protocol = TemporalTrainingProtocol.standard_unpaired_protocol()

		self.focus(aruco = True)
		if not self.calibrate_mazes_aruco():
			self.calibrate_mazes()

		while True:
			if self.verify_mazes():
				break
			self.calibrate_mazes()
		self.focus()
		self.setup_experiment()
		try:
			aborted = self.run_experiment()
			if not aborted:
				aborted = self.run_protocol(protocol)
			if not aborted:
				self.run_experiment()
		finally:
			self.end_experiment()

	def focus(self, aruco = False):
		self.cap.set_focus(self.lens_position)
		if aruco:
			self.cap.aruco_focus_window()
		else:
			self.cap.focus_window()
		self.lens_position = self.cap.get_lens_position()

	def create_data_directories(self):
		text_basedir = Path.home() / 'ymaze-text-data'
		video_basedir = Path.home() / 'ymaze-video-data'
		self.time_stamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
		self.text_dir = text_basedir / self.time_stamp
		self.video_dir = video_basedir / self.time_stamp
		self.text_dir.mkdir(parents=True, exist_ok=True)
		self.video_dir.mkdir(parents=True, exist_ok=True)
		if not os.path.exists(self.text_dir):
			print("did not create data directory")
			quit()

	def calibrate_mazes_aruco(self):
		self.cap.reset_bounding_box()
		self.ymg = YMazeGeometry()
		self.ymg.set_image_size((self.cap.h, self.cap.w))
		self.ymg.set_barrel_distortion((self.cap.w / 2, self.cap.h / 2), self.barrel_alpha)
		im, _ = self.cap.capture_frame()
		if self.ymg.calibrate_geometry_aruco(im):
			x, y, w, h = self.ymg.clip_to_mazes(10)
			self.cap.set_bounding_box_from_im_coordinates(x, y, w, h)
			return True
		return False

	def calibrate_mazes(self):
		self.cap.reset_bounding_box()
		self.ymg = YMazeGeometry()
		self.ymg.set_image_size((self.cap.h, self.cap.w))
		self.ymg.set_barrel_distortion((self.cap.w/2, self.cap.h/2), self.barrel_alpha)
		im, _ = self.cap.capture_frame()
		self.ymg.calibrate_geometry_from_image_fiducials(im)
		self.ymg.align_mazes_to_im(im)
		x, y, w, h = self.ymg.clip_to_mazes(10)
		self.cap.set_bounding_box_from_im_coordinates(x, y, w, h)

	def verify_mazes(self, timeout = 20):
		im, _ = self.cap.capture_frame()
		cv2.namedWindow('clipped mazes', cv2.WINDOW_KEEPRATIO)
		img = self.ymg.diagnostic_image(im)
		cv2.imshow('clipped mazes', img)
		cv2.resizeWindow('clipped mazes', self.default_win_size)
		print("Are you satisfied with the maze locations? y/n q to quit")
		accepted = True
		for i in range(timeout*10):
			key = cv2.waitKey(100) & 0xFF
			if key == ord('q'):
				quit()
			if key == ord('n'):
				accepted = False
				break
			if key == ord('y'):
				accepted = True
				break
		return accepted

	def create_stabilizer(self, frame):
		self.imstab = ImageStabilizer(frame)
		for j in range(1, 10):
			self.imstab.add_roi(self.ymg.get_bounding_rect(j, percent_scale=50))

	def illumination_response_test(self, active_maze = 5, cstart = np.array([0, 0, 0]), cend = np.array([255, 0, 0])):
		self.create_data_directories()
		self.light_controller.set_global_brightness(self.brightness)
		im,ts = self.cap.capture_frame()
		self.t0 = ts
		vidfilename = self.video_dir / f"{self.time_stamp} illumination response.mp4"
		fourcc = cv2.VideoWriter_fourcc(*'mp4v')
		h,w = im.shape[:2]
		vid_writer = cv2.VideoWriter(vidfilename, fourcc, 30.0, (w,h), True)
		intensity = cstart
		cv2.namedWindow('all mazes', cv2.WINDOW_NORMAL)
		cv2.resizeWindow('all mazes', self.default_win_size)
		while ts-self.t0 < self.experiment_duration:
			img = cv2.cvtColor(im,cv2.COLOR_GRAY2BGR)
			cv2.putText(img, f"{intensity}", (5, h - 5), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255),
						1, bottomLeftOrigin=False)
			intensity = ((cend-cstart)*np.minimum((ts-self.t0)/ self.experiment_duration,1) + cstart).astype(np.uint8)
			for c in range(3):
				self.light_controller.set_led(active_maze, c, *intensity)
			self.light_controller.update_leds()
			vid_writer.write(img)
			cv2.imshow('all mazes', img)
			if cv2.waitKey(100) & 0xFF == ord('q'): #limit frame rate
				quit()
			im, ts = self.cap.capture_frame(flush=True)
		vid_writer.release()

	def setup_experiment(self):
		self.md = MazeDispatcher(self.ymg, light_controller=self.light_controller)
		self.create_data_directories()
		_,self.t0 = self.cap.last_frame_number_and_time()
		self.md.set_save_raw(True)
		self.md.open_video(self.video_dir / f"{self.time_stamp} maze")

	def run_protocol(self, protocol : TrainingProtocol):
		#im,tstart = self.cap.capture_frame()
		im,tstart = self.capture_stabilized()
		frame_num, frame_time = self.cap.last_frame_number_and_time()
		tt = None
		cv2.namedWindow('all mazes', cv2.WINDOW_NORMAL)
		cv2.resizeWindow('all mazes', self.default_win_size)
		protocol.start()
		self.md.enable_stim_manager(False)
		self.md.enable_background_update(False)
		self.md.enable_tracking(False)

		old_ledval = None
		self.light_controller.set_global_brightness(9) #max allowed - could go higher and maybe fry board?
		aborted = False
		while not protocol.finished():
			ledval, update = protocol.led_value_and_update()
			if old_ledval is not None:
				update = update and any(np.asarray(old_ledval) != np.asarray(ledval))
			if update:
				self.md.set_all_leds(ledval)
				old_ledval = ledval
				print (f"{frame_time - tstart}: new ledval: {ledval}")
			ready_for_new_frame = True
			if tt is not None:
				ready_for_new_frame = not any([t.is_alive() for t in tt])
				if ready_for_new_frame:
					self.md.write_video()
					cv2.imshow('all mazes', self.md.get_composite_image())
					cv2.waitKey(1)
					if self.experiment_display_window():
						aborted = True
						break
			if ready_for_new_frame:
				tt = self.md.new_frame(im, frame_number=frame_num, frame_time=frame_time - self.t0,
									   wait_for_completion=False, multi_thread=True)
			#im,_ = self.cap.capture_frame()
			im,_ = self.capture_stabilized()
			frame_num, frame_time = self.cap.last_frame_number_and_time()
		self.md.set_all_leds((0,0,0))
		return aborted

	# noinspection PyDefaultArgument
	def experiment_display_window(self, state={'display_maze': 0, 'old_maze': -1}):
		display_maze = state['display_maze']
		if display_maze >= 0:
			win = self.md._maze_minions[display_maze].debug_display()
			if display_maze != state['old_maze']:
				cv2.resizeWindow(win, self.default_win_size)
				state['old_maze'] = display_maze
		else:
			win = None
		k = cv2.waitKey(1) & 0xFF
		if k == ord('q'):
			return True
		if ord('0') <= k <= ord('9'):
			state['old_maze'] = display_maze
			display_maze = k - ord('1')
			if display_maze >= 0 and display_maze != state['old_maze']:
				if win is not None:
					cv2.destroyWindow(win)
			state['display_maze'] = display_maze
		if k == ord('t') and display_maze >= 0:
			self.md._maze_minions[display_maze]._maze_controller.decrease_threshold()
		if k == ord('u') and display_maze >= 0:
			self.md._maze_minions[display_maze]._maze_controller.increase_threshold()
		return False

	def capture_stabilized(self):
		im, ts = self.cap.capture_frame()
		if self.imstab is None:
			self.create_stabilizer(im)
		im = self.imstab.register(im, self.stabilizer_alpha)
		return im, ts

	def run_experiment(self, experiment_duration = None):
		self.light_controller.set_global_brightness(self.brightness)
		cv2.namedWindow('all mazes', cv2.WINDOW_NORMAL)
		cv2.resizeWindow('all mazes', self.default_win_size)
		if experiment_duration is None:
			experiment_duration = self.experiment_duration
		elapsed_time = 0
		#im, t_start = self.cap.capture_frame()
		im, t_start = self.capture_stabilized()

		tt = None
		frame_num, frame_time = self.cap.last_frame_number_and_time()
		self.md.enable_stim_manager(True)
		self.md.enable_background_update(True)
		self.md.enable_tracking(True)
		aborted = False
		while elapsed_time < experiment_duration:
			if self.experiment_display_window():
				aborted = True
				break
			#wait for previous frame to finish processing
			if tt is not None:
				for t in tt:
					t.join()
				self.md.write_video()
				cv2.imshow('all mazes', self.md.make_composite_image())
				cv2.waitKey(1)

			num_choices = np.sum(np.asarray(self.md.num_choices()), axis=0)
			elapsed_time = frame_time - t_start
			print(f"frame: {frame_num}, elapsed time: {elapsed_time}, to light: {num_choices[0]}, to dark: {num_choices[1]}, null: {num_choices[2]}")
			tt = self.md.new_frame(im, frame_number=frame_num, frame_time=frame_time - self.t0, wait_for_completion=False, multi_thread=True)
			#im = self.cap.capture_frame()[0]
			im,_ = self.capture_stabilized()
			frame_num, frame_time = self.cap.last_frame_number_and_time()
		if tt is not None:
			for t in tt:
				t.join()
		self.light_controller.turn_off_leds()
		return aborted

	def end_experiment(self):
		filepath = self.text_dir / f"{self.time_stamp} results.csv"
		if self.md is not None:
			self.md.get_data_frame().to_csv(f"{filepath}")
			print("experiment completed, make sure to run rclone")
			print(f"rclone -copy {self.text_dir} ugns:pi5 --verbose")
		if self.light_controller is not None:
			self.light_controller.turn_off_leds()

#TODO argparse
if __name__ == "__main__":
	lt = LiveTracker()
	lt.experiment_duration = 3600
	lt.full_conditioning_experiment()