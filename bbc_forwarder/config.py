"""config module
=============

The config module creates the `CONFIG` object from 'config.json':
a nested namedtuple containing the project settings.
"""

import json
from collections import namedtuple
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent

def to_namedtuple(dct, name):
    "Return dictionary as namedtuple."
    NamedTuple = namedtuple(name.capitalize(), [key.lower() for key in dct])
    return NamedTuple(**dct)


def config_from_json(path):
    "Read json from path and convert to config object (nested namedtuples)."
    with open(path, 'r') as f:
        data = json.load(f)
    return to_namedtuple(
        {k:to_namedtuple(v, k) for k,v in data.items()},
        name='Config',
    )


CONFIG = config_from_json(PATH / "config.json")
