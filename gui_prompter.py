import json
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime

from livetracker import LiveTracker
from ymazeparameters import LiveTrackerParameters
# EXPERIMENTS_DIR = Path.home() / "drosophila_experiments_gui_data"
#
PROMPTS = [
    "experimenter",
    "genotype",
    "num_larva",
    "maze_description",
    "experiment_type",
    "notes",
]


class ExperimentGUI:
    def __init__(self, root, default_dict, name = "Metadata Form"):
        self.root = root
        self.root.title(name)
        self.root.geometry("620x430")

        self.entries = {}
        self.current_file = None
        self.extra_metadata = {}

       # EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)

        title = tk.Label(
            root,
            text=name,
            font=("Arial", 16)
        )
        title.pack(pady=10)

        form_frame = tk.Frame(root)
        form_frame.pack(fill="both", expand=True, padx=20, pady=5)

        for row_number, prompt in enumerate(PROMPTS):
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

        tk.Button(button_frame, text="New Form", width=12,
                  command=self.clear_form).grid(row=0, column=0, padx=5)
        tk.Button(button_frame, text="Load JSON", width=12,
                  command=self.load_json).grid(row=0, column=1, padx=5)
        tk.Button(button_frame, text="Save", width=12,
                  command=self.save_json).grid(row=0, column=2, padx=5)
        tk.Button(button_frame, text="Save As", width=12,
                  command=self.save_json_as).grid(row=0, column=3, padx=5)

        self.status_label = tk.Label(
            root,
            text=f"Save folder: TODO",
            anchor="w",
        )
        self.status_label.pack(fill="x", padx=20, pady=(0, 12))

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

        metadata["last_modified"] = datetime.now().isoformat()

        return metadata

    def put_metadata_in_form(self, metadata):
        """Place dictionary values into the GUI fields."""
        for prompt, entry in self.entries.items():
            entry.delete(0, tk.END)

            value = metadata.get(prompt, "")
            entry.insert(0, str(value))

    def clear_form(self):
        """Clear every box and start a new metadata file."""
        for entry in self.entries.values():
            entry.delete(0, tk.END)

        self.current_file = None
        self.status_label.config(text="New form")

    def load_json(self):
        """Choose an existing JSON file and load it into the GUI."""
        filepath = filedialog.askopenfilename(
            title="Select an experiment JSON file",
            initialdir=str(EXPERIMENTS_DIR),
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )

        if not filepath:
            return

        try:
            with open(filepath, "r", encoding="utf-8") as file:
                metadata = json.load(file)

            if not isinstance(metadata, dict):
                messagebox.showerror(
                    "Wrong JSON format",
                    "Choose an individual experiment JSON file. "
                    "The selected file contains a list.",
                )
                return

            self.put_metadata_in_form(metadata)
            self.current_file = Path(filepath)
            self.status_label.config(text=f"Loaded: {self.current_file}")

        except json.JSONDecodeError as error:
            messagebox.showerror("Invalid JSON", f"Invalid JSON:\n{error}")
        except OSError as error:
            messagebox.showerror("File error", f"Could not open file:\n{error}")

    def save_json(self):
        """
        Save over the currently loaded file.
        If no file is loaded, create a new file.
        """
        if self.current_file is None:
            self.save_json_as()
            return

        try:
            with open(self.current_file, "w", encoding="utf-8") as file:
                json.dump(self.get_metadata(), file, indent=4)

            self.status_label.config(text=f"Saved: {self.current_file}")
            messagebox.showinfo("Saved", f"Saved to:\n{self.current_file}")

        except OSError as error:
            messagebox.showerror("Save error", f"Could not save file:\n{error}")

    def save_json_as(self):
        """Save the form as a new JSON file."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        filepath = filedialog.asksaveasfilename(
            title="Save experiment metadata",
            initialdir=str(EXPERIMENTS_DIR),
            initialfile=f"{timestamp}_metadata.json",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )

        if not filepath:
            return

        self.current_file = Path(filepath)
        self.save_json()


def main():
    print("Starting Drosophila metadata GUI...")
    #print(f"Default save folder: {EXPERIMENTS_DIR}")

    ltp = LiveTrackerParameters()
    root = tk.Tk()
    app = ExperimentGUI(root, ltp.camera_parameters.to_dict(), "camera parameters")


    root.after(100, root.lift)
    root.after(150, lambda: root.attributes("-topmost", True))
    root.after(400, lambda: root.attributes("-topmost", False))

    root.mainloop()


if __name__ == "__main__":
    main()
