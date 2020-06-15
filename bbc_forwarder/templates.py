"""templates module
================

The templates module loads all templates in the 'templates' folder and stores
them as namedtuple in `templates`. Similarly the subject lines belonging to the
tempaltes are loaded from `CONFIG` (these are stored in 'config.json').
"""

from pathlib import Path
from string import Template

from bbc_forwarder.config import to_namedtuple, CONFIG


def read(path):
    return Path(path).read_text(encoding='utf8')


def name(path):
    return Path(path).suffixes[0].strip('.').strip('_')


glob = Path('templates').glob('*.html')
templates = to_namedtuple(
    {name(path):Template(read(path)) for path in glob},
    name='Templates',
)

subjects = to_namedtuple(
    {k:Template(v) for k,v in CONFIG.forwarder.subjects.items()},
    name='Subjects',
)
