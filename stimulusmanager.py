from ymazegeometry import MazePart
from enum import Enum
from mazecontroller import MazeController
class StimulusManager:
    _currentLocation:MazePart
    _currentState:State

    def __init__(self):

    def update(self, loc:MazePart):
        if (loc == self._currentLocation):
            return


class Action:
    def __init__(self, maze_controller:MazeController, stimulus_manager:StimulusManager,
                 from_state:State = (State.PREDECISION, STATE.POSTDECISION), to_parts = MazePart.all_parts(), from_parts = MazePart.all_parts()):
        self.maze_controller = maze_controller
        self.stimulus_manager = stimulus_manager
        self.from_state = from_state
        self.to_parts = to_parts
        self.from_parts = from_parts
        self.action = None

    def condition_satisfied(self, prev_loc, new_loc):
        cs = any(self.stimulus_manager._currentState == self.from_state)
        cs = cs and any(prev_loc == self.from_parts) and any(new_loc == self.to_parts)
        return cs

    def poll(self, prev_loc, new_loc):
        if self.condition_satisfied(prev_loc, new_loc):
            self.action()




class State(Enum):
    OFF = 0
    CHOOSE1 = 1
    CHOOSE2 = 2
    CHOOSE3 = 3
    PREDECISION = 4


