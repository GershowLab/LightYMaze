import warnings
from dataclasses import dataclass, asdict, field
import numpy as np

@dataclass
class BaseParameterClass:

    def to_dict(self):
        return asdict(self)

    def has_param(self, param):
        return hasattr(self, param)

    def set_param(self, key, value):
        if self.has_param(key):
            current_value = getattr(self, key)
            if isinstance(current_value, np.ndarray):
                value = np.array(value)
            setattr(self, key, value)

    def set_params(self, param_dict):
        for key, value in param_dict.items():
            self.set_param (key, value)

    def apply_param(self, obj, param):
        if self.has_param(param) and hasattr(obj, param):
            setattr(obj, param, getattr(self, param))

    def apply_params(self, obj):
        for key in vars(self).keys():
            self.apply_param (obj, key)



@dataclass
class LedChoiceParameters(BaseParameterClass):
    choice1rgb : list[int] = field(default_factory=lambda: (0, 0, 0))
    choice2rgb : list[int] = field(default_factory=lambda: (0, 0, 255))
    overall_brightness : int = 5

@dataclass
class ExperimentParameters(BaseParameterClass):
    genotype : str = "genotype_not_specified"
    atr : str = ""
    other_dir_text : str = ""
    experimenter_name : str = "The Phantom Gourmet"
    duration_pre_train : float = 3600
    duration_post_train : float = 3600
    stabilize_images : bool = False
    stabilizer_alpha : float = 0.1
    register_maze_images : bool = True

@dataclass
class CameraParameters(BaseParameterClass):
  #  center_pixel : list[int] = field(default_factory=lambda:(2304, 1296))
    barrel_alpha : float = -0.000032
    lens_position : float  = 1/.0768
    exposure : int = 9000
    gain : int = 2
    hflip : bool = False
    vflip : bool = True

@dataclass
class TrainingParameters(BaseParameterClass):
    period : float = 30
    n_reps : int = 20
    cs_rgbpct :list[int] = field(default_factory=lambda:(0, 0, 25))
    us_rgbpct : list[int] = field(default_factory=lambda:(255, 0, 0))
    cs_tr : list[float] = field(default_factory=lambda:(0, 15))
    us_tr : list[float] = field(default_factory=lambda:(0, 15))

@dataclass
class YMazeParameters(BaseParameterClass):
    aruco_centers : list[list[float]] = field(default_factory=lambda:[[-18, 9], [0, -9], [9, 0]])  # mm
    aruco_corners : list[list[float]] = field(default_factory=lambda:((-2, -2), (2, -2), (2, 2), (-2, 2)))

class LiveTrackerParameters:
    def __init__(self):
        self.led_choice_parameters = LedChoiceParameters()
        self.experiment_parameters = ExperimentParameters()
        self.camera_parameters = CameraParameters()
        self.training_parameters = TrainingParameters()
        self.ymaze_parameters = YMazeParameters()

    def param_list(self):
        plist = [list(vars(value).keys()) for value in vars(self).values()]
        plist_flat = [item for sublist in plist for item in sublist] #suggeted by google AI
        seen = set()
        duplicates = set()
        for item in plist_flat:
            if item in seen:
                duplicates.add(item)
            else:
                seen.add(item)
        valid_keys = seen.difference(duplicates)
        return valid_keys,duplicates

    def to_dict(self):
         return {key: asdict(value) for key, value in self.__dict__.items()}

    def get_major_params(self):
        return {'genotype' : self.experiment_parameters.genotype,
                'atr' : self.experiment_parameters.atr,
                'choice2rgb' : self.led_choice_parameters.choice2rgb
                }

    def set_major_params(self, maj_dict):
        self.experiment_parameters.genotype = maj_dict['genotype']
        self.experiment_parameters.atr = maj_dict['atr']
        self.experiment_parameters.choice2rgb = maj_dict['choice2rgb']

    def set_param(self, key, value):
        if hasattr(self, key):
            p = getattr(self, key)
            p.set_params(value)
        else:
            valid_keys,duplicates = self.param_list()
            if key in valid_keys:
                [p.set_param(key, value) for p in vars(self).values()]
            if key in duplicates:
                warnings.warn(f"Duplicate key {key} in parameter list -- can't set by name, use dict instead")

    def set_params(self, param_dict):
        for key, value in param_dict.items():
            self.set_param(key, value)
