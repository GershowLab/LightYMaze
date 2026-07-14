import json
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime


EXPERIMENTS_DIR = Path.home() / "drosophila_experiments_gui_data"

PROMPTS = [
    "experimenter",
    "genotype",
    "num_larva",
    "maze_description",
    "experiment_type",
    "notes"
]


class ExperimentGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Drosophila Experiment Metadata")

        self.entries = {}
        self.current_file = None

        EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)

        title = tk.Label(
            root,
            text="Drosophila Experiment Metadata",
            font=("Arial", 16)
        )
        title.pack(pady=10)

        form_frame = tk.Frame(root)
        form_frame.pack(padx=20, pady=10)

        for row_number, prompt in enumerate(PROMPTS):
            label = tk.Label(
                form_frame,
                text=prompt.replace("_", " ").title()
            )
            label.grid(
                row=row_number,
                column=0,
                sticky="w",
                padx=5,
                pady=5
            )

            entry = tk.Entry(form_frame, width=45)
            entry.grid(
                row=row_number,
                column=1,
                padx=5,
                pady=5
            )

            self.entries[prompt] = entry

        button_frame = tk.Frame(root)
        button_frame.pack(pady=15)

        new_button = tk.Button(
            button_frame,
            text="New Form",
            command=self.clear_form
        )
        new_button.grid(row=0, column=0, padx=5)

        load_button = tk.Button(
            button_frame,
            text="Load JSON",
            command=self.load_json
        )
        load_button.grid(row=0, column=1, padx=5)

        save_button = tk.Button(
            button_frame,
            text="Save",
            command=self.save_json
        )
        save_button.grid(row=0, column=2, padx=5)

        save_as_button = tk.Button(
            button_frame,
            text="Save As",
            command=self.save_json_as
        )
        save_as_button.grid(row=0, column=3, padx=5)

        self.status_label = tk.Label(
            root,
            text="No file loaded"
        )
        self.status_label.pack(pady=5)

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
            title="Select experiment JSON file",
            initialdir=EXPERIMENTS_DIR,
            filetypes=[("JSON files", "*.json")]
        )

        if not filepath:
            return

        try:
            with open(filepath, "r") as file:
                metadata = json.load(file)

            if not isinstance(metadata, dict):
                messagebox.showerror(
                    "Invalid File",
                    "This JSON file contains a list, not one experiment dictionary."
                )
                return

            self.put_metadata_in_form(metadata)

            self.current_file = Path(filepath)
            self.status_label.config(
                text=f"Loaded: {self.current_file.name}"
            )

        except json.JSONDecodeError:
            messagebox.showerror(
                "Invalid JSON",
                "The selected file is not valid JSON."
            )

        except OSError as error:
            messagebox.showerror(
                "File Error",
                f"Could not open the file:\n{error}"
            )

    def save_json(self):
        """
        Save over the currently loaded file.
        If no file is loaded, create a new file.
        """
        if self.current_file is None:
            self.save_json_as()
            return

        metadata = self.get_metadata()

        try:
            with open(self.current_file, "w") as file:
                json.dump(metadata, file, indent=4)

            self.status_label.config(
                text=f"Saved: {self.current_file.name}"
            )

            messagebox.showinfo(
                "Saved",
                f"Changes saved to:\n{self.current_file}"
            )

        except OSError as error:
            messagebox.showerror(
                "Save Error",
                f"Could not save the file:\n{error}"
            )

    def save_json_as(self):
        """Save the form as a new JSON file."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        filepath = filedialog.asksaveasfilename(
            title="Save experiment metadata",
            initialdir=EXPERIMENTS_DIR,
            initialfile=f"{timestamp}_metadata.json",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )

        if not filepath:
            return

        self.current_file = Path(filepath)
        self.save_json()


def main():
    root = tk.Tk()
    ExperimentGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
