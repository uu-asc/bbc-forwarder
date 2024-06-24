"""templates module
================

The templates module loads a Jinja `Environment` in a global variable. Similarly the subject lines and filenames belonging to the templates are loaded in a global dictionary (`SUBJECTS` and `FILENAME`) from `CONFIG` (these are stored in 'config.json').
"""

from pathlib import Path
from string import Template

from jinja2 import Environment, FileSystemLoader

from bbc_forwarder.config import to_namedtuple, CONFIG, PATH


def read(path):
    return Path(path).read_text(encoding='utf8')


def name(path):
    return Path(path).suffixes[0].strip('.').strip('_')


ENV = Environment(
    loader = FileSystemLoader(searchpath = PATH / 'templates'),
    trim_blocks = True,
    lstrip_blocks = True
)

SUBJECTS = {k:Template(v) for k,v in CONFIG['forwarder']['subjects'].items()}

FILENAME = Template(CONFIG['forwarder']['filename'])
