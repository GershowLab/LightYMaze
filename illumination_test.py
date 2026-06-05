from livetracker import LiveTracker

lt = LiveTracker()
lt.experiment_duration = 600
lt.focus(aruco = True)
lt.calibrate_mazes_aruco()
while True:
    if lt.verify_mazes():
        break
    lt.calibrate_mazes()
lt.focus()
lt.illumination_response_test()