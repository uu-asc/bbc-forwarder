"""parser module
=============

The parser module contains the `parser` function which does the following:

1. Loop through all messages in a folder;
2. Loop trhough all attachments in a message;
3. If an attachment is a pdf:
    a. Attempt to read its contents.
    b. Store contents if successful.
    c. Extract dates from the contents.
    d. Use earliest extracted date as birth date.
    e. Search for names in population datebase by this birth date.
    f. Try to match any of the retrieved names to the contents of the pdf.
    g. If a name is match, store the population record.
4. Logs this process.

The module further contains several helper functions and a `ParseLogger` class
which the `parser` utilizes during parsing:

- ParseLogger :
- is_pdf :
- parse_pdf :
- remove_whitespace :
- find_institute :
- find_amount :
- replace_months :
- find_dates :
- get_earliest :
- search_name :

More information
----------------
Searching the contents is done using regular expressions:
- [Regular expression operations](https://docs.python.org/3/library/re.html)
- [regex101](https://regex101.com/)
"""

import base64
import io
import re
from pathlib import Path

import pandas as pd
from pdfminer.high_level import extract_text

from bbc_forwarder.config import CONFIG


class ParseLogger(object):
    """ParseLogger
    ===========

    Class for logging and storing parser results.

    ### Metadata
    Set `metadata` to the meta data you wish to store with the logs/results.

    ### Storing results
    Store results through simple subscription:
        `logger[id] = value`

    ### Logging results
    `__call__` instance to create a log at timestamp.now(). The current meta
    data plus any kwargs provided to the call will be added to the log.

    Attributes
    ==========
    metadata : dict
        Dictionary for storing meta data of the current parsed/logged item.
    logs : list
        List for storing all logged messages.
    results : dict
        Dictionary for storing all parsed results, keys should be ids.
    frame : pd.DataFrame
        Df containing all logged results.

    Methods
    =======
    __call__ : log metadata and **kwargs
    __setitem__ : store parsed result at `key`.
    __getitem__ : retrieve parsed result at `key`.
    """

    def __init__(self):
        self.metadata = {}
        self.results = {}
        self.logs = []

    def __call__(self, **kwargs):
        log = dict(timestamp=pd.Timestamp.now(), **self.metadata, **kwargs)
        self.logs.append(log)

    def __setitem__(self, key, value):
        self.results[key] = value

    def __getitem__(self, key):
        return self.results[key]

    @property
    def frame(self):
        return pd.DataFrame(self.logs)

    @property
    def fields(self):
        return self.logs.columns


def is_pdf(attachment):
    "Return if attachment has extension '.pdf' as boolean."
    return Path(attachment.name).suffix.lower() == '.pdf'


def parse_pdf(attachment):
    """Try to read pdf and return contents as string.
    Return False if extraction fails.
    """
    try:
        doc = base64.b64decode(attachment.content)
        return extract_text(io.BytesIO(doc))
    except:
        return False


def remove_whitespace(text):
    "Remove any redundant whitespace (but not newlines)."
    regex = r"[^\S\n\r]{2,}"
    return re.sub(regex, ' ', text)


def find_amounts(text):
    "Search text and return any strings matching amount format: € #,####.##"
    regex = re.compile(
        r"""
        €           # euro-teken
        [^\S\n\r]*  # optionele whitespace, geen newline
        \d          # cijfer
        (?:         # non-capturing groep
        [.,]?       # optionele punt of komma
        |           # of
        [^\S\n\r]   # whitespace, geen newline
        )           #
        \d+         # ten minste één cijfer
        [.,]?       # optionele punt of komma
        \d*         # overige cijfers indien aanwezig
        """, re.X)
    return re.findall(regex, text)


def find_institute(text):
    """Search text after removing newlines and redundant whitespace and return
    any matched institutes (list of institutes is stored in 'config.json'."""
    found_institutes = []
    text = text.replace('\n', ' ')
    text = remove_whitespace(text)
    for institute in CONFIG.parser.institutes:
        if re.search(institute, text):
            found_institutes.append(institute)
    return found_institutes


def replace_months(text):
    "Replace month names with month number in string."
    replacements = {
        '(januari|jan)':   '01',
        '(februari|feb)':  '02',
        '(maart|mrt)':     '03',
        '(april|apr)':     '04',
        '(mei)':           '05',
        '(juni|jun)':      '06',
        '(juli|jul)':      '07',
        '(augustus|aug)':  '08',
        '(september|sep)': '09',
        '(oktober|okt)':   '10',
        '(november|nov)':  '11',
        '(december|dec)':  '12',
    }
    for pat, repl in replacements.items():
        text = re.sub(pat, repl, text, count=0, flags=0)
    return text


def find_datestrings(text):
    "Search text and return any strings matching date format: dd-mm-yyyy."
    regex = re.compile(
        r"""
        \d{1,2}     # minimaal 1, maximaal 2 cijfers
        (?:         # non-capturing groep
        [-/\.]      # streep, backslash, punt
        |           # of
        [^\S\n\r]   # whitespace, geen newline
        )           #
        \d{1,2}     # minimaal 1, maximaal 2 cijfers
        (?:         # non-capturing groep
        [-/\.]      # streep, backslash, punt
        |           # of
        [^\S\n\r]   # whitespace, geen newline
        )           #
        \d{4}       # 4 cijfers
        \b          # einde reeks
        """, re.X)
    return re.findall(regex, text)


def get_earliest(datestrings):
    "Convert datestrings into timestamps and return earliest date."
    def to_timestamp(datestring):
        regex = r'(?:[-/\.]|[^\S\n\r])'
        order = ['day', 'month', 'year']
        zipped = zip(order, re.split(regex, datestring))
        dateparts = {unit:int(part) for unit, part in zipped}
        return pd.Timestamp(**dateparts)
    return min([to_timestamp(datestring) for datestring in datestrings])


def search_name(name, date, text, population):
    """Search text for name. If match is found, return all records from
    population database as DatFrame. Return empty DataFrame if no match.
    """
    match = re.findall(name, text)
    if match:
        query = "achternaam == @name and geboortedatum == @date"
        return population.query(query)
    else:
        return pd.DataFrame()


def parser(folder, population, limit=None):
    "Parse mailbox folder and return results as ParseLogger object."
    logger = ParseLogger()
    for message in folder.get_messages(limit=limit):
        logger.metadata = dict(
            received    = message.received.strftime("%Y-%m-%d %Hh%Mm%Ss"),
            object_id   = message.object_id,
            folder_id   = message.folder_id,
            folder_name = folder.name,
            sender      = str(message.sender),
            flag        = message.flag,
            is_read     = message.is_read,
            subject     = message.subject,
            attachments = message.has_attachments,
        )

        if not message.has_attachments:
            logger()
            continue

        message.attachments.download_attachments()
        for attachment in message.attachments:
            log = dict()
            log['attachment_id'] = attachment.attachment_id
            log['attachment_name'] = attachment.name
            log['pdf'] = is_pdf(attachment)
            if not is_pdf(attachment):
                logger(**log)
                continue

            text = parse_pdf(attachment)
            log['parsed?'] = bool(text)
            if not bool(text):
                logger(**log)
                continue
            text = remove_whitespace(text)
            logger[attachment.attachment_id] = text

            log['institutes'] = find_institute(text)
            log['amounts'] = find_amounts(text)

            text = replace_months(text)
            dates = find_datestrings(text)
            log['n_dates_found'] = len(dates)
            if not dates:
                logger(**log)
                continue

            date = get_earliest(dates)
            log['search_date'] = date

            candidates = population.query("geboortedatum == @date")
            log['candidates'] = ~candidates.empty
            if candidates.empty:
                logger(**log)
                continue

            log['found_student'] = False
            for name in candidates.achternaam.unique():
                match = search_name(name, date, text, population)
                if not match.empty:
                    log['found_student'] = True
                    for record in match.iterrows():
                        log.update(record[1].to_dict())
                        logger(**log)
            if not log['found_student']:
                logger(**log)
    return logger
