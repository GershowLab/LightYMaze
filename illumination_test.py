from livetracker import LiveTracker
import numpy as np
lt = LiveTracker()
lt.experiment_duration = 100
lt.brightness = 5
lt.focus()
cvals = np.array(([0, 0, 0], [25,0,0],[128,0,0],[255,0,0],[0,0,0]))
timestep = 10
active_maze = (1,3,5,7,9)
lt.illumination_response_test_discrete(active_maze=active_maze, timestep=timestep, cvals=cvals)

# lt.cap.reset_bounding_box()
# w = lt.cap.w
# h = lt.cap.h
# lt.cap.set_bounding_box_from_im_coordinates((w-h)/2,0,h,h)
# lt.focus(aruco = True)
# lt.calibrate_mazes_aruco()
# while True:
#     if lt.verify_mazes():
#         break
#     lt.calibrate_mazes()