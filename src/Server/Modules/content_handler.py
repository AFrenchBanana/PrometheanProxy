"""
content handler for loading different types of files into
"""
from tomlkit import parse, dumps
import json


class TomlFiles:
    """Loads a TOML file and provides methods for updating and saving."""

    def __init__(self, filename: str) -> None:
        self.filename = filename
        with open(filename, "rt", encoding="utf-8") as f:
            self.data = parse(f.read())

    def __enter__(self) -> dict:
        return self.data

    def __exit__(self, tipe, value, traceback):
        pass  # No need to close the file in this approach

    def update_config(
            self,
            key: str,
            subkey: str,
            new_value: str | bool | int) -> None:
        """Updates the value at the specified key and subkey."""
        self.data[key][subkey] = new_value
        self.save()

    def save(self) -> None:
        """Saves the updated data to the TOML file."""
        with open(self.filename, 'wt', encoding='utf-8') as f:
            f.write(dumps(self.data))

class JsonFiles:
    """Loads a JSON file and provides methods for updating and saving."""

    def __init__(self, filename: str) -> None:
        self.filename = filename
        with open(filename, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def __enter__(self) -> dict:
        return self.data

    def __exit__(self, tipe, value, traceback):
        pass 

    def update_config(self, key: str, new_value: str | bool | int) -> None:
        """Updates the value at the specified key."""
        self.data[key] = new_value
        self.save()

    def save(self) -> None:
        """Saves the updated data to the JSON file."""
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4)
