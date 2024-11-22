import os
import sys
from pathlib import Path
import re

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
                if isinstance(key, str) and key[-7:] == ".append":
                    if key[:-7] in old_dict:
                        old_dict[key[:-7]] = old_dict[key[:-7]] + value
                elif isinstance(key, str) and key[-8:] == ".prepend":
                    if key[:-8] in old_dict:
                        old_dict[key[:-8]] = value + old_dict[key[:-8]]
                else:
                    old_dict[key] = value
        return old_dict

    config = {}
    for file in config_files:
        config = nested_update(config, read_yaml(file))
    return config


def print_config(config: dict):
    print("Config:\n")
    yaml.dump(config, sys.stdout, sort_keys=False)
    print("\n")


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


def case_insensitive_partition(string: str, separator: str):
    # Escape special characters in the separator
    escaped_separator = re.escape(separator)

    # Search for the separator in a case-insensitive manner
    match = re.search(escaped_separator, string, re.IGNORECASE)

    if match:
        # If found, partition the string
        start = match.start()
        end = match.end()

        # Return the three parts: before, separator, and after
        return string[:start], string[start:end], string[end:]
    else:
        # If not found, return the entire string and two empty strings
        return string, '', ''
