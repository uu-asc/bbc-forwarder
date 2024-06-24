"""config module
=============

The config module creates the `CONFIG` object from 'config.json':
a dictionary containing the project settings.
"""

import json
from collections import namedtuple
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent


def to_namedtuple(dct, name) -> namedtuple:
    "Return dictionary as namedtuple."
    NamedTuple = namedtuple(name.capitalize(), [key.lower() for key in dct])
    return NamedTuple(**dct)


def read_json_from_path(path) -> dict:
    "Read json from path."
    with open(path, 'r') as f:
        data = json.load(f)
    return data


CONFIG = read_json_from_path(PATH / "config.json")
