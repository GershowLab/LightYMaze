from ymazegeometry import MazePart
from enum import Enum
import mazecontroller
import numpy as np

class State(Enum):
    OFF = 0
    CHOOSE1 = 1
    CHOOSE2 = 2
    CHOOSE3 = 3
    PREDECISION = 4

class StimulusManager:
    current_location: MazePart
    current_state: State

    def __init__(self, maze_controller):
        self.current_state = State.PREDECISION
        self.origin_location = MazePart.INTERSECTION
        self.current_location = MazePart.INTERSECTION
        self._message = ''
        self._has_message = False
        self.actions = [
            ActionDecisionMade(self),
            ActionSetLedPostDecision(self, State.CHOOSE1),
            ActionSetLedPostDecision(self, State.CHOOSE2),
            ActionSetLedPostDecision(self, State.CHOOSE3),
            ActionChangedMind(self, State.CHOOSE1),
            ActionChangedMind(self, State.CHOOSE2),
            ActionChangedMind(self, State.CHOOSE3),
        ]
        self.maze_controller = maze_controller


    def turn_off(self):
        self.current_state = State.OFF

    def turn_on(self):
        self.current_state = State.PREDECISION

    def set_message(self, message):
        self._message = message
        self._has_message = True

    def get_message(self, mark_read = True):
        if self._has_message:
            self._has_message = not mark_read
            return self._message, True
        else:
            return '',False

    def has_message(self):
        return self._has_message

    def update(self):
        new_location = self.maze_controller.get_larva_region()
        if new_location == self.current_location:
            return
        old_location = self.current_location
        self.current_location = new_location
        print (f"{self.current_state} from {old_location} to {new_location}")
        for a in self.actions:
            a.poll(old_location, new_location)



class Action:
    def __init__(self, stimulus_manager: StimulusManager,
                 from_states = (State.PREDECISION, State.CHOOSE1, State.CHOOSE2, State.CHOOSE3),
                 to_parts=MazePart.all_parts(), from_parts=MazePart.all_parts()):
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
        super().__init__(stimulus_manager, from_states=(state,))
        self.offrgb = offrgb
        self.choice1rgb = choice1rgb
        self.choice2rgb = choice2rgb
        if state == State.CHOOSE1:
            self.to_parts = (MazePart.CIRCLE1,)
            self.ledOff = 1
            self.ledChoices = (2, 3)
            self.msg = "CONF1"
        if state == State.CHOOSE2:
            self.to_parts = (MazePart.CIRCLE2,)
            self.ledOff = 2
            self.ledChoices = (1, 3)
            self.msg = "CONF2"
        if state == State.CHOOSE3:
            self.to_parts = (MazePart.CIRCLE3,)
            self.ledOff = 3
            self.ledChoices = (2, 1)
            self.msg = "CONF3"


    def action(self):
        self.stimulus_manager.maze_controller.set_ledrgbpct(self.ledOff, self.offrgb)
        for ind, val in zip(np.random.permutation(self.ledChoices), (self.choice1rgb, self.choice2rgb)):
            self.stimulus_manager.maze_controller.set_ledrgbpct(ind, val)
        self.stimulus_manager.current_state = State.PREDECISION
        self.stimulus_manager.set_message(self.msg)
        self.stimulus_manager.origin_location = self.to_parts[0]

class ActionDecisionMade(Action):
    def __init__(self, stimulus_manager: StimulusManager):
        super().__init__(stimulus_manager)
        self.from_states = (State.PREDECISION,)
        self.from_parts = (MazePart.CHANNEL1, MazePart.CHANNEL2, MazePart.CHANNEL3, MazePart.INTERSECTION)
        self.to_parts = (MazePart.CHANNEL1, MazePart.CHANNEL2, MazePart.CHANNEL3)

    #if in a new channel that is not connected to the origin circle, register as a choice
    def action(self):
        for cl, ol, ns, msg in zip(
                (MazePart.CHANNEL1, MazePart.CHANNEL2, MazePart.CHANNEL3),
                (MazePart.CIRCLE1, MazePart.CIRCLE2, MazePart.CIRCLE3),
                (State.CHOOSE1, State.CHOOSE2, State.CHOOSE3),
                ("CHOOSE1","CHOOSE2","CHOOSE3")):
            if self.stimulus_manager.current_location == cl and self.stimulus_manager.origin_location != ol:
                self.stimulus_manager.current_state = ns
                self.stimulus_manager.set_message(msg)

class ActionChangedMind(Action):
    def __init__(self, stimulus_manager: StimulusManager, from_state: State):
        super().__init__(stimulus_manager, (from_state, ))
        if from_state == State.CHOOSE1:
            self.from_parts = (MazePart.CHANNEL1, MazePart.INTERSECTION)
            self.to_parts = (MazePart.CHANNEL2, MazePart.CHANNEL3)
        if from_state == State.CHOOSE2:
            self.from_parts = (MazePart.CHANNEL2, MazePart.INTERSECTION)
            self.to_parts = (MazePart.CHANNEL1, MazePart.CHANNEL3)
        if from_state == State.CHOOSE3:
            self.from_parts = (MazePart.CHANNEL3, MazePart.INTERSECTION)
            self.to_parts = (MazePart.CHANNEL1, MazePart.CHANNEL2)

    def action(self):
        for cl, ns,msg in zip((MazePart.CHANNEL1, MazePart.CHANNEL2, MazePart.CHANNEL3),
                           (State.CHOOSE1, State.CHOOSE2, State.CHOOSE3),
                           ("CHANGE1", "CHANGE2", "CHANGE3")):
            if self.stimulus_manager.current_location == cl:
                self.stimulus_manager.current_state = ns


