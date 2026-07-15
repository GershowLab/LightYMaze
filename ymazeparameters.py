import warnings
from dataclasses import dataclass, asdict, field
import numpy as np
import tkinter as tk
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

    def get_param(self, key):
        return getattr(self, key, None)

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
        self.major_parameters = [
            ['experiment_parameters', 'genotype'],
            ['experiment_parameters', 'atr'],
            ['led_choice_parameters', 'choice2rgb']
        ]

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

    def get_param(self, key, paramset = None):
        if paramset is not None:
            p = getattr(self, paramset)
            return p.get_param(key)
        else:
            for p in vars(self).values():
                if p.get_param(key) is not None:
                    return p.get_param(key)
            return None

    def get_major_params(self):
        d = {}
        for p in self.major_parameters:
            if isinstance(p,str):
                d[p] = self.get_param(p)
            else:
                d[p[1]] = self.get_param(p[1],p[0])
        return d


    def set_major_params(self, maj_dict):
        for p in self.major_parameters:
            if isinstance(p,str):
                if maj_dict.get(p) is not None:
                    self.set_param(p,maj_dict[p])
            else:
                if maj_dict.get(p[1]) is not None:
                    a = getattr(self, p[0])
                    a.set_param(p[1],maj_dict[p[1]])

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
        if param_dict is None:
            return

        if isinstance(param_dict,LiveTrackerParameters) or isinstance(param_dict,BaseParameterClass):
            param_dict = param_dict.to_dict()

        if not isinstance(param_dict,dict):
            try:
                param_dict = vars(param_dict)
            except:
                warnings.warn("Could not convert argument to dictionary")
                return

        for key, value in param_dict.items():
            self.set_param(key, value)

#TODO: when the main panel text boxes are edited, the corresponding values in the
#parameter fields should update

#TODO: when the panels are updated, the main textboxes should also change

class MainGUI:
    def __init__(self, root, ltp):
        self.root = root
        self.root.title("Parameters")
        self.root.geometry("620x430")
        self.entries = {}
        self.current_file = None

        title = tk.Label(
            root,
            text="Parameters",
            font=("Arial", 16)
        )
        title.pack(pady=10)

        form_frame = tk.Frame(root)
        form_frame.pack(fill="both", expand=True, padx=20, pady=5)

        mp = []
        for p in ltp.major_parameters:
            if isinstance(p,str):
                mp.append(p)
            else:
                mp.append(p[1])

        for row_number, prompt in enumerate(mp):
            tk.Label(
                form_frame,
                text=prompt.replace("_", " ").title() + ":",
                anchor="w",
                width=18,
            ).grid(row=row_number, column=0, sticky="nw", padx=5, pady=6)

            entry = tk.Entry(form_frame, width=47)
            entry.grid(row=row_number, column=1, sticky="ew", padx=5, pady=6)
            self.entries[prompt] = entry

        form_frame.columnconfigure(1, weight=1)

        button_frame = tk.Frame(root)
        button_frame.pack(pady=12)

        c = 0
        for key, value in vars(ltp).items():
            if isinstance(value,BaseParameterClass):
                bname = key.replace("_parameters", "").replace("_"," ")
                tk.Button(button_frame, text=bname, width=12,
                          command=lambda arg1=value,arg2=bname: self.popup_panel(arg1, arg2)).grid(row=0, column=c, padx=5)
                c = c+1

        self.status_label = tk.Label(
            root,
            text=f"Save folder: TODO",
            anchor="w",
        )
        self.status_label.pack(fill="x", padx=20, pady=(0, 12))
        self.put_metadata_in_form(ltp.get_major_params())

    def popup_panel(self, params, win_name):
        print(type(params))
        print(params)
        ParameterGUI(self.root, params, win_name)

    def read_widget(self, prompt):
        widget = self.entries[prompt]
        if isinstance(widget, tk.Text):
            return widget.get("1.0", tk.END).strip()
        return widget.get().strip()

    def write_widget(self, prompt, value):
        widget = self.entries[prompt]
        if isinstance(widget, tk.Text):
            widget.delete("1.0", tk.END)
            widget.insert("1.0", str(value))
        else:
            widget.delete(0, tk.END)
            widget.insert(0, str(value))

    def get_metadata(self):
        """Collect all GUI values into one dictionary."""
        metadata = {}

        for prompt, entry in self.entries.items():
            metadata[prompt] = entry.get().strip()

        return metadata

    def put_metadata_in_form(self, metadata):
        """Place dictionary values into the GUI fields."""
        for prompt, entry in self.entries.items():
            entry.delete(0, tk.END)

            value = metadata.get(prompt, "")
            entry.insert(0, str(value))




class ParameterGUI:
    def __init__(self, root, params, name = None, modal = False):
        self.root = root
        self.win = tk.Toplevel(root)
        if name is None:
            name = type(params).__name__
        self.win.title(name)

        #google ai to make modal
        # # 2. Force focus and freeze the parent window
        if modal:
            self.win.focus_set()         # Moves keyboard focus to the new window
            self.win.grab_set()          # Redirects all user events (clicks/keys) to this window


        self.win.geometry("620x430")

        self.entries = {}
        self.current_file = None
        self.extra_metadata = {}

        self.params = params
        self.original_settings = params.to_dict()

        title = tk.Label(
            self.win,
            text=name,
            font=("Arial", 16)
        )
        title.pack(pady=10)

        form_frame = tk.Frame(self.win)
        form_frame.pack(fill="both", expand=True, padx=20, pady=5)

        for row_number, prompt in enumerate(self.original_settings.keys()):
            tk.Label(
                form_frame,
                text=prompt.replace("_", " ").title() + ":",
                anchor="w",
                width=18,
            ).grid(row=row_number, column=0, sticky="nw", padx=5, pady=6)

            entry = tk.Entry(form_frame, width=47)
            entry.grid(row=row_number, column=1, sticky="ew", padx=5, pady=6)
            self.entries[prompt] = entry

        form_frame.columnconfigure(1, weight=1)

        button_frame = tk.Frame(self.win)
        button_frame.pack(pady=12)
        tk.Button(button_frame, text="Reset", width=12,
                  command=self.clear_form).grid(row=0, column=0, padx=5)
        tk.Button(button_frame, text="Done", width=12,
                  command=self.close).grid(row=0, column=1, padx=5)
        # tk.Button(button_frame, text="Save", width=12,
        #           command=self.save_json).grid(row=0, column=2, padx=5)
        # # tk.Button(button_frame, text="Save As", width=12,
        #           command=self.save_json_as).grid(row=0, column=3, padx=5)

        self.status_label = tk.Label(
            self.win,
            text=f"Save folder: TODO",
            anchor="w",
        )
        self.status_label.pack(fill="x", padx=20, pady=(0, 12))
        self.put_metadata_in_form(self.original_settings)

    def read_widget(self, prompt):
        widget = self.entries[prompt]
        if isinstance(widget, tk.Text):
            return widget.get("1.0", tk.END).strip()
        return widget.get().strip()

    def write_widget(self, prompt, value):
        widget = self.entries[prompt]
        if isinstance(widget, tk.Text):
            widget.delete("1.0", tk.END)
            widget.insert("1.0", str(value))
        else:
            widget.delete(0, tk.END)
            widget.insert(0, str(value))

    def get_metadata(self):
        """Collect all GUI values into one dictionary."""
        metadata = {}

        for prompt, entry in self.entries.items():
            metadata[prompt] = entry.get().strip()

        # metadata["last_modified"] = datetime.now().isoformat()

        return metadata

    def put_metadata_in_form(self, metadata):
        """Place dictionary values into the GUI fields."""
        for prompt, entry in self.entries.items():
            entry.delete(0, tk.END)

            value = metadata.get(prompt, "")
            entry.insert(0, str(value))

    def clear_form(self):
        """Clear every box and start a new metadata file."""
        self.put_metadata_in_form(self.original_settings)

    def update_params(self):
        self.params.set_params(self.get_metadata())

    def close(self):
        self.update_params()
        self.win.destroy()



def main():
    print("Test GUI panels...")

    ltp = LiveTrackerParameters()
    root = tk.Tk()
    app = MainGUI(root, ltp)
    # panel1 = ParameterGUI(root, ltp.camera_parameters, "camera parameters")
    # panel2 = ParameterGUI(root, ltp.led_choice_parameters, "led parameters")


    root.after(100, root.lift)
    root.after(150, lambda: root.attributes("-topmost", True))

    root.mainloop()

    print(ltp.camera_parameters.to_dict())

if __name__ == "__main__":
    main()
