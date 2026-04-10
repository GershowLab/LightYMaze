from ymazegeometry import MazePart
from enum import Enum
import mazecontroller
import numpy as np
import time

class State(Enum):
    OFF = 0
    CHOOSE1 = 1
    CHOOSE2 = 2
    CHOOSE3 = 3
    PREDECISION_ANY = 4
    PREDECISION1 = 5
    PREDECISION2 = 6
    PREDECISION3 = 7

class StimulusManager:
    current_location: MazePart
    current_state: State

    def __init__(self, maze_controller):
        self.current_state = State.PREDECISION_ANY
        self.origin_location = MazePart.INTERSECTION
        self.current_location = MazePart.INTERSECTION
        self._message = ''
        self._has_message = False
        self._last_action_time = time.monotonic()
        self._watchdog_interval = 120
        self.actions = [
            ActionChooseCircle(self, State.CHOOSE1),
            ActionChooseCircle(self, State.CHOOSE2),
            ActionChooseCircle(self, State.CHOOSE3),
            ActionLeaveCircle(self, MazePart.CIRCLE1),
            ActionLeaveCircle(self, MazePart.CIRCLE2),
            ActionLeaveCircle(self, MazePart.CIRCLE3),
            ActionFirstChannelChoice(self, State.PREDECISION1),
            ActionFirstChannelChoice(self, State.PREDECISION2),
            ActionFirstChannelChoice(self, State.PREDECISION3),
            ActionChangedMind(self, State.CHOOSE1),
            ActionChangedMind(self, State.CHOOSE2),
            ActionChangedMind(self, State.CHOOSE3),
        ]
        self.maze_controller = maze_controller


    def turn_off(self):
        self.current_state = State.OFF

    def turn_on(self):
        self.current_state = State.PREDECISION_ANY

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
        for a in self.actions:
            a.poll(old_location, new_location)
        self.watchdog()

    def reset_watchdog(self):
        self._last_action_time = time.monotonic()

    def watchdog(self):
        if (time.monotonic() - self._last_action_time) > self._watchdog_interval:
            self.current_state = State.PREDECISION_ANY
            self.maze_controller.set_leds((0,0,0),(0,0,0),(0,0,0))
            self.set_message('RESET')
            self.reset_watchdog()


class Action:
    def __init__(self, stimulus_manager: StimulusManager,
                 from_states = (State.PREDECISION_ANY, State.PREDECISION1, State.PREDECISION2, State.PREDECISION3, State.CHOOSE1, State.CHOOSE2, State.CHOOSE3),
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
            self.stimulus_manager.reset_watchdog()
            self.action()

#enter circle after making a choice
class ActionChooseCircle(Action):
    def __init__(self, stimulus_manager: StimulusManager,
                 state: State):
        super().__init__(stimulus_manager, from_states=(state,))
        if state == State.CHOOSE1:
            self.to_parts = (MazePart.CIRCLE1,)
            self.msg = "CONF1"
            self.next_state = State.PREDECISION_ANY
        if state == State.CHOOSE2:
            self.to_parts = (MazePart.CIRCLE2,)
            self.msg = "CONF2"
            self.next_state = State.PREDECISION_ANY
        if state == State.CHOOSE3:
            self.to_parts = (MazePart.CIRCLE3,)
            self.msg = "CONF3"
            self.next_state = State.PREDECISION_ANY

    def action(self):
        self.stimulus_manager.maze_controller.set_leds((0,0,0),(0,0,0),(0,0,0))
        self.stimulus_manager.current_state = self.next_state
        self.stimulus_manager.set_message(self.msg)
        self.stimulus_manager.origin_location = self.to_parts[0]

#leave circle - need to turn on a LED
class ActionLeaveCircle(Action):
    def __init__(self, stimulus_manager: StimulusManager, from_part : MazePart,
                 offrgb=(0, 0, 0), choice1rgb=(0, 0, 0), choice2rgb=(0, 0, 255)):
        super().__init__(stimulus_manager, from_states=(State.PREDECISION_ANY,))
        self.offrgb = offrgb
        self.choice1rgb = choice1rgb
        self.choice2rgb = choice2rgb
        self.from_parts = (from_part,)
       # self.to_parts = (MazePart.CHANNEL1, MazePart.INTERSECTION)
        if from_part == MazePart.CIRCLE1:
            self.next_state = State.PREDECISION1
        #    self.to_parts = (MazePart.CHANNEL1, MazePart.INTERSECTION)
            self.ledOff = 1
            self.ledChoices = (2, 3)
            self.msg = "FROM1"
        if from_part == MazePart.CIRCLE2:
            self.next_state = State.PREDECISION2
       #     self.to_parts = (MazePart.CHANNEL2, MazePart.INTERSECTION)
            self.ledOff = 2
            self.ledChoices = (1, 3)
            self.msg = "FROM2"
        if from_part == MazePart.CIRCLE3:
            self.next_state = State.PREDECISION3
      #      self.to_parts = (MazePart.CHANNEL3, MazePart.INTERSECTION)
            self.ledOff = 3
            self.ledChoices = (2, 1)
            self.msg = "FROM3"

    def action(self):
        self.stimulus_manager.maze_controller.set_ledrgbpct(self.ledOff, self.offrgb)
        for ind, val in zip(np.random.permutation(self.ledChoices), (self.choice1rgb, self.choice2rgb)):
            self.stimulus_manager.maze_controller.set_ledrgbpct(ind, val)
        self.stimulus_manager.set_message(self.msg)
        self.stimulus_manager.origin_location = self.to_parts[0]
        self.stimulus_manager.current_state = self.next_state


class ActionFirstChannelChoice(Action):
    def __init__(self, stimulus_manager: StimulusManager, state: State):
        super().__init__(stimulus_manager, from_states=(state,State.PREDECISION_ANY))
        if state == State.PREDECISION1:
            self.from_parts = (MazePart.CHANNEL1, MazePart.INTERSECTION)
            self.to_parts = (MazePart.CHANNEL2, MazePart.CHANNEL3)
        if state == State.PREDECISION2:
            self.from_parts = (MazePart.CHANNEL2, MazePart.INTERSECTION)
            self.to_parts = (MazePart.CHANNEL1, MazePart.CHANNEL3)
        if state == State.PREDECISION3:
            self.from_parts = (MazePart.CHANNEL3, MazePart.INTERSECTION)
            self.to_parts = (MazePart.CHANNEL2, MazePart.CHANNEL2)

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
                self.stimulus_manager.set_message(msg)
                self.stimulus_manager.origin_location = cl



