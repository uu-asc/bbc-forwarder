import json
from collections import namedtuple


with open("config.json", 'r') as fh:
    data = json.load(fh)


def dict_to_namedtuple(dct, name):
    NamedTuple = namedtuple(name.capitalize(), [key for key in dct])
    return NamedTuple(**dct)


def create_config(data):
    return dict_to_namedtuple(
        {k:dict_to_namedtuple(v, k) for k,v in data.items()},
        'Config',
    )


CONFIG = create_config(data)
