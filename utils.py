import os
import sys
from pathlib import Path

import yaml


def read_yaml(file):
    with open(file, "r") as stream:
        try:
            return yaml.load(stream, Loader=yaml.CLoader)
        except yaml.YAMLError as e:
            raise e


def read_configs(config_files):
    def nested_update(old_dict, new_dict):
        for key, value in new_dict.items():
            if isinstance(value, dict):
                old_dict[key] = nested_update(old_dict.get(key, {}), value)
            else:
                old_dict[key] = value
        return old_dict

    config = {}
    for file in config_files:
        config = nested_update(config, read_yaml(file))
    return config


class Logger:
    """Prints the stdout simultaneously to the terminal and a file."""
    def __init__(self, log_file: Path | str):
        log_file = Path(log_file)
        self.stdout = sys.stdout
        os.makedirs(log_file.parent, exist_ok=True)
        self.file_name = f'{log_file}.ansi'
        self.file = open(self.file_name, "w")

    def write(self, message):
        self.stdout.write(message)
        self.file.write(message)

    def flush(self):
        self.stdout.flush()
        self.file.flush()
