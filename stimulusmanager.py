from ymazegeometry import MazePart
from enum import Enum
from mazecontroller import MazeController
import numpy as np


class StimulusManager:
    current_location: MazePart
    current_state: State
    maze_controller: MazeController

    def __init__(self, maze_controller: MazeController):
        current_state = State.PREDECISION
        self.maze_controller = maze_controller
        self.current_location = maze_controller.get_larva_region()
        self.actions = []

    def update(self):
        new_location = self.maze_controller.get_larva_region()
        if new_location == self.current_location:
            return
        old_location = self.current_location
        self.current_location = new_location
        for a in self.actions:
            a.poll(old_location, new_location)


class Action:
    def __init__(self, stimulus_manager: StimulusManager,
                 from_states: State = (State.PREDECISION, State.CHOOSE1, State.CHOOSE2, State.CHOOSE3),
                 to_parts=MazePart.all_parts(), from_parts=MazePart.all_parts()):
        self.maze_controller = maze_controller
        self.stimulus_manager = stimulus_manager
        self.from_states = from_states
        self.to_parts = to_parts
        self.from_parts = from_parts

    def action(self):
        pass

    def condition_satisfied(self, prev_loc, new_loc):
        return self.stimulus_manager.current_state in self.from_states and prev_loc in self.from_parts and new_loc in self.to_parts

    def poll(self, prev_loc, new_loc):
        if self.condition_satisfied(prev_loc, new_loc):
            self.action()


class ActionSetLedPostDecision(Action):
    def __init__(self, stimulus_manager: StimulusManager,
                 state: State, offrgb=(0, 0, 0), choice1rgb=(0, 0, 0), choice2rgb=(0, 0, 255)):
        super().__init__(stimulus_manager, from_states=state)
        self.offrgb = offrgb
        self.choice1rgb = choice1rgb
        self.choice2rgb = choice2rgb
        if state == State.CHOOSE1:
            self.to_parts = (MazePart.CIRCLE1,)
            self.ledOff = 1
            self.ledChoices = (2, 3)
        if state == State.CHOOSE2:
            self.to_parts = (MazePart.CIRCLE2,)
            self.ledOff = 2
            self.ledChoices = (1, 3)
        if state == State.CHOOSE3:
            self.to_parts = (MazePart.CIRCLE3,)
            self.ledOff = 3
            self.ledChoices = (2, 1)

    def action(self):
        self.stimulus_manager.maze_controller.set_ledrgbpct(self.ledOff, self.offrgb)
        for ind, val in np.random.permutation(self.ledChoices), (self.choice1rgb, self.choice2rgb):
            self.stimulus_manager.maze_controller.set_ledrgbpct(ind, val)


class State(Enum):
    OFF = 0
    CHOOSE1 = 1
    CHOOSE2 = 2
    CHOOSE3 = 3
    PREDECISION = 4
