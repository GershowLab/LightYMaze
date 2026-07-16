#TODO: JSON data dump
#(probably also load from file)
#dimensions
#weird panel popover issues

import warnings
from dataclasses import dataclass, asdict, field
import numpy as np
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
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
            if isinstance(getattr(obj, param), np.ndarray):
                setattr(obj, param, np.array(getattr(self, param)))
            else:
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
            ['led_choice_parameters', 'choice2rgb'],
            ['experiment_parameters', 'experimenter_name'],
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
         return {key: asdict(value) for key, value in self.__dict__.items() if value is dict}

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
        self.ltp = ltp

        self.root.title("Parameters")
        self.root.geometry("700x520")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.entries = {}
        self.boolean_vars = {}
        self.field_types = {}
        self.current_file = None

        title = tk.Label(
            root,
            text="Parameters",
            font=("Arial", 16)
        )
        title.pack(pady=10)

        form_frame = tk.Frame(root)
        form_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=5
        )

        # Build the main form directly from the current parameter values.
        major_parameters = self.ltp.get_major_params()

        for row_number, (prompt, value) in enumerate(
            major_parameters.items()
        ):
            tk.Label(
                form_frame,
                text=prompt.replace("_", " ").title() + ":",
                anchor="w",
                width=22,
            ).grid(
                row=row_number,
                column=0,
                sticky="nw",
                padx=5,
                pady=6
            )

            # Real Boolean values become checkboxes.
            if isinstance(value, bool):
                variable = tk.BooleanVar(value=value)

                widget = tk.Checkbutton(
                    form_frame,
                    text="Yes",
                    variable=variable,
                    onvalue=True,
                    offvalue=False,
                )

                widget.grid(
                    row=row_number,
                    column=1,
                    sticky="w",
                    padx=5,
                    pady=6
                )

                self.boolean_vars[prompt] = variable
                self.field_types[prompt] = bool

            else:
                widget = tk.Entry(
                    form_frame,
                    width=47
                )

                widget.grid(
                    row=row_number,
                    column=1,
                    sticky="ew",
                    padx=5,
                    pady=6
                )

                self.field_types[prompt] = type(value)

            self.entries[prompt] = widget

        form_frame.columnconfigure(1, weight=1)

        # Buttons that open nested parameter panels.
        panel_button_frame = tk.LabelFrame(
            root,
            text="Additional Parameter Panels",
            padx=10,
            pady=10
        )
        panel_button_frame.pack(
            fill="x",
            padx=20,
            pady=8
        )

        column = 0

        for key, value in vars(self.ltp).items():
            if isinstance(value, BaseParameterClass):
                button_name = (
                    key.replace("_parameters", "")
                    .replace("_", " ")
                    .title()
                )

                tk.Button(
                    panel_button_frame,
                    text=button_name,
                    width=16,
                    command=lambda params=value, name=button_name:
                        self.popup_panel(params, name)
                ).grid(
                    row=0,
                    column=column,
                    padx=5,
                    pady=5
                )

                column += 1

        action_button_frame = tk.Frame(root)
        action_button_frame.pack(pady=10)

        tk.Button(
            action_button_frame,
            text="Save",
            width=12,
            command=self.save_json
        ).grid(row=0, column=0, padx=5)

        tk.Button(
            action_button_frame,
            text="Save As",
            width=12,
            command=self.save_json_as
        ).grid(row=0, column=1, padx=5)

        tk.Button(
            action_button_frame,
            text="Refresh",
            width=12,
            command=self.refresh_from_ltp
        ).grid(row=0, column=2, padx=5)

        tk.Button(
            action_button_frame,
            text="Close",
            width=12,
            command=self.close
        ).grid(row=0, column=3, padx=5)

        self.status_label = tk.Label(
            root,
            text="No file saved yet",
            anchor="w",
        )
        self.status_label.pack(
            fill="x",
            padx=20,
            pady=(0, 12)
        )

        self.put_metadata_in_form(
            self.ltp.get_major_params()
        )

    def popup_panel(self, params, win_name):
        """
        Open a popup using the real nested parameter object.

        Because the exact object is passed into ParameterGUI, changes made
        in the popup update the same object stored inside self.ltp.
        """
        self.apply_major_params()

        panel = ParameterGUI(
            self.root,
            params,
            win_name,
            modal=True
        )

        # Wait until the popup closes, then refresh the main form.
        self.root.wait_window(panel.win)
        self.refresh_from_ltp()

    def read_widget(self, prompt):
        """
        Read a value from the correct widget type.

        Boolean checkboxes return real True/False values.
        """
        if self.field_types[prompt] is bool:
            return bool(
                self.boolean_vars[prompt].get()
            )

        return self.entries[prompt].get().strip()

    def write_widget(self, prompt, value):
        """Write a value into either a checkbox or an Entry."""
        if self.field_types[prompt] is bool:
            self.boolean_vars[prompt].set(
                bool(value)
            )
            return

        widget = self.entries[prompt]
        widget.delete(0, tk.END)
        widget.insert(0, str(value))

    def get_metadata(self):
        """Collect all major GUI values."""
        return {
            prompt: self.read_widget(prompt)
            for prompt in self.entries
        }

    def put_metadata_in_form(self, metadata):
        """Place major parameter values into the main GUI."""
        for prompt in self.entries:
            value = metadata.get(prompt, "")
            self.write_widget(prompt, value)

    def refresh_from_ltp(self):
        """
        Reload the main form from the shared LiveTrackerParameters object.
        """
        self.put_metadata_in_form(
            self.ltp.get_major_params()
        )

        self.status_label.config(
            text="Refreshed from shared parameters"
        )

    def apply_major_params(self):
        """
        Write the main form values back into LiveTrackerParameters.
        """
        metadata = self.get_metadata()

        if hasattr(self.ltp, "set_major_params"):
            self.ltp.set_major_params(metadata)

        elif hasattr(self.ltp, "set_params"):
            self.ltp.set_params(metadata)

        else:
            # Fallback if no setter function exists.
            for key, value in metadata.items():
                if hasattr(self.ltp, key):
                    setattr(self.ltp, key, value)

    def collect_all_metadata(self):
        """
        Collect the main parameters and all popup-panel parameters.

        This includes camera parameters, LED parameters, and every other
        BaseParameterClass stored inside LiveTrackerParameters.
        """
        self.apply_major_params()

        metadata = dict(
            self.ltp.get_major_params()
        )

        for key, value in vars(self.ltp).items():
            if isinstance(value, BaseParameterClass):
                metadata[key] = value.to_dict()

        metadata["last_modified"] = (
            datetime.now().isoformat(
                timespec="seconds"
            )
        )

        return metadata

    def save_json(self):
        """Save all major and nested parameter data."""
        if self.current_file is None:
            self.save_json_as()
            return

        try:
            metadata = self.collect_all_metadata()

            with open(
                self.current_file,
                "w",
                encoding="utf-8"
            ) as file:
                json.dump(
                    metadata,
                    file,
                    indent=4
                )

            self.status_label.config(
                text=f"Saved: {self.current_file}"
            )

            messagebox.showinfo(
                "Saved",
                f"Parameters saved to:\n"
                f"{self.current_file}",
                parent=self.root
            )

        except (OSError, TypeError) as error:
            messagebox.showerror(
                "Save Error",
                f"Could not save parameters:\n{error}",
                parent=self.root
            )

    def save_json_as(self):
        """Choose a new JSON filename and save all parameters."""
        save_directory = (
            Path.home()
            / "drosophila_experiments_gui_data"
        )

        save_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        timestamp = datetime.now().strftime(
            "%Y-%m-%d_%H-%M-%S"
        )

        filepath = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save experiment parameters",
            initialdir=str(save_directory),
            initialfile=(
                f"{timestamp}_parameters.json"
            ),
            defaultextension=".json",
            filetypes=[
                ("JSON files", "*.json")
            ]
        )

        if not filepath:
            return

        self.current_file = Path(filepath)
        self.save_json()

    def close(self):
        """
        Apply the main-window values before closing.

        Popup values have already been written directly into their shared
        parameter objects when their Done buttons were clicked.
        """
        self.apply_major_params()
        self.root.destroy()

import weakref


class ParameterGUI:
    """
    Generic popup for editing a parameter object.

    Requirements for params:
        params.to_dict() -> dictionary
        params.set_params(dictionary) -> updates the parameter object

    If multiple ParameterGUI windows receive the same params object, clicking
    Done in one window updates the shared object and refreshes the other windows.
    Boolean values are displayed and returned as real Boolean checkboxes.
    """

    _open_panels = {}

    def __init__(self, root, params, name=None, modal=False):
        self.root = root
        self.params = params
        self.modal = modal

        self.win = tk.Toplevel(root)

        if name is None:
            name = type(params).__name__

        self.name = name
        self.win.title(name)
        self.win.geometry("620x430")
        self.win.protocol("WM_DELETE_WINDOW", self.close)

        if modal:
            self.win.transient(root)
            self.win.focus_set()
            self.win.grab_set()

        self.original_settings = params.to_dict().copy()

        self.entries = {}
        self.boolean_vars = {}
        self.field_types = {}

        self._register_panel()

        title = tk.Label(
            self.win,
            text=name,
            font=("Arial", 16)
        )
        title.pack(pady=10)

        form_frame = tk.Frame(self.win)
        form_frame.pack(fill="both", expand=True, padx=20, pady=5)

        for row_number, (prompt, value) in enumerate(
            self.original_settings.items()
        ):
            tk.Label(
                form_frame,
                text=prompt.replace("_", " ").title() + ":",
                anchor="w",
                width=18,
            ).grid(
                row=row_number,
                column=0,
                sticky="nw",
                padx=5,
                pady=6
            )

            if isinstance(value, bool):
                variable = tk.BooleanVar(value=value)

                widget = tk.Checkbutton(
                    form_frame,
                    text="Yes",
                    variable=variable,
                    onvalue=True,
                    offvalue=False,
                )
                widget.grid(
                    row=row_number,
                    column=1,
                    sticky="w",
                    padx=5,
                    pady=6
                )

                self.boolean_vars[prompt] = variable
                self.field_types[prompt] = bool

            else:
                widget = tk.Entry(form_frame, width=47)
                widget.grid(
                    row=row_number,
                    column=1,
                    sticky="ew",
                    padx=5,
                    pady=6
                )

                self.field_types[prompt] = type(value)

            self.entries[prompt] = widget

        form_frame.columnconfigure(1, weight=1)

        button_frame = tk.Frame(self.win)
        button_frame.pack(pady=12)

        tk.Button(
            button_frame,
            text="Reset",
            width=12,
            command=self.clear_form
        ).grid(row=0, column=0, padx=5)

        tk.Button(
            button_frame,
            text="Done",
            width=12,
            command=self.close
        ).grid(row=0, column=1, padx=5)

        self.status_label = tk.Label(
            self.win,
            text="Click Done to apply changes to every open panel.",
            anchor="w",
        )
        self.status_label.pack(fill="x", padx=20, pady=(0, 12))

        self.refresh_from_params()

    def _panel_key(self):
        return id(self.params)

    def _register_panel(self):
        key = self._panel_key()

        if key not in self._open_panels:
            self._open_panels[key] = weakref.WeakSet()

        self._open_panels[key].add(self)

    def _unregister_panel(self):
        key = self._panel_key()
        panels = self._open_panels.get(key)

        if panels is None:
            return

        panels.discard(self)

        if not panels:
            self._open_panels.pop(key, None)

    def _refresh_other_panels(self):
        panels = self._open_panels.get(self._panel_key(), weakref.WeakSet())

        for panel in list(panels):
            if panel is not self and panel.win.winfo_exists():
                panel.refresh_from_params()

    def read_widget(self, prompt):
        if self.field_types[prompt] is bool:
            return bool(self.boolean_vars[prompt].get())

        return self.entries[prompt].get().strip()

    def write_widget(self, prompt, value):
        if self.field_types[prompt] is bool:
            self.boolean_vars[prompt].set(bool(value))
            return

        widget = self.entries[prompt]
        widget.delete(0, tk.END)
        widget.insert(0, str(value))

    def get_metadata(self):
        return {
            prompt: self.read_widget(prompt)
            for prompt in self.entries
        }

    def put_metadata_in_form(self, metadata):
        for prompt in self.entries:
            value = metadata.get(prompt, "")
            self.write_widget(prompt, value)

    def refresh_from_params(self):
        latest_settings = self.params.to_dict()
        self.put_metadata_in_form(latest_settings)
        self.status_label.config(
            text="Showing the latest shared parameter values."
        )

    def clear_form(self):
        self.put_metadata_in_form(self.original_settings)
        self.status_label.config(
            text="Reset locally. Click Done to apply the reset."
        )

    def update_params(self):
        self.params.set_params(self.get_metadata())

    def close(self):
        self.update_params()
        self._refresh_other_panels()
        self._unregister_panel()

        if self.modal and self.win.grab_current() == self.win:
            self.win.grab_release()

        self.win.destroy()


def main():
    print("Test GUI panels...")

    ltp = LiveTrackerParameters()

    root = tk.Tk()
    app = MainGUI(root, ltp)

    root.after(100, root.lift)
    root.after(150, lambda: root.attributes("-topmost", True))

    root.mainloop()

    print(ltp.camera_parameters.to_dict())


if __name__ == "__main__":
    main()
