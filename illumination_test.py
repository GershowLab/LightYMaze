from livetracker import LiveTracker

lt = LiveTracker()
lt.experiment_duration = 300
lt.brightness = 9
w = lt.cap.w
h = lt.cap.h
lt.cap.set_bounding_box_from_im_coordinates((w-h)/2,0,h,h)
# lt.focus(aruco = True)
# lt.calibrate_mazes_aruco()
# while True:
#     if lt.verify_mazes():
#         break
#     lt.calibrate_mazes()
lt.focus()
lt.illumination_response_test()