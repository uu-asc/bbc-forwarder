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

The module further contains several helper functions which the `parser` utilizes during parsing:

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

from query import osiris as osi
from bbc_forwarder.config import CONFIG


SQL = """
select
    studentnummer,
    stud.voorletters,
    stud.voorvoegsels,
    stud.achternaam,
    stud.geboortedatum,
    sinh.sinh_id,
    sinh.soort_inschrijving_fac soort_inschrijving,
    sinh.croho,
    opleiding,
    case ropl.faculteit
        when 'IVLOS' then 'GST'
        when 'RA' then 'UCR'
        when 'UC' then 'UCU'
        else ropl.faculteit
    end faculteit,
    ropl.aggregaat_1,
    ropl.aggregaat_2,
    sinh.actiefcode_opleiding_csa actiefcode,
    sinh.mutatiedatum_actiefcode datum_actiefcode,
    sinh.inschrijvingstatus,
    sinh.datum_verzoek_inschr datum_verzoek,
    sinh.intrekking_vooraanmelding datum_intrekking,
    sinh.ingangsdatum,
    sinh.afloopdatum,
    sinh.examentype_csa examentype
from
    osiris.ost_student_inschrijfhist sinh
    join osiris.ost_student stud using (studentnummer)
    left join osiris.ost_opleiding ropl using (opleiding)
where
    sinh.collegejaar = {{ collegejaar }}
    and stud.geboortedatum = date '{{ geboortedatum }}'
"""


def is_pdf(attachment) -> bool:
    "Return if attachment has extension '.pdf' as boolean."
    return Path(attachment.name).suffix.lower() == '.pdf'


def parse_pdf(attachment):
    """Try to read pdf and return contents as string.
    Return False if extraction fails.
    """
    try:
        doc = base64.b64decode(attachment.content)
        text = extract_text(io.BytesIO(doc))
        # return False if parsed text is (mostly) empty
        if len(text) < 24:
            return False
        return text
    except:
        return False


def remove_whitespace(text) -> str:
    "Remove any redundant whitespace (but not newlines)."
    regex = r"[^\S\n\r]{2,}"
    return re.sub(regex, ' ', text)


def find_amounts(text) -> list[str]:
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


def find_institute(text) -> list:
    """Search text after removing newlines and redundant whitespace and return
    any matched institutes (list of institutes is stored in 'config.json'."""
    found_institutes = []
    text = text.replace('\n', ' ')
    text = remove_whitespace(text)
    for institute in CONFIG['parser']['institutes']:
        if re.search(institute, text):
            found_institutes.append(institute)
    return found_institutes


def replace_months(text) -> str:
    "Replace month names with month number in string."
    replacements = {
        '(?<=[\b-\\\\])(januari|jan)':     '01',
        '(?<=[\b-\\\\])(februari|feb)':    '02',
        '(?<=[\b-\\\\])(maart|mrt|mar)':   '03',
        '(?<=[\b-\\\\])(april|apr)':       '04',
        '(?<=[\b-\\\\])(mei|may)':         '05',
        '(?<=[\b-\\\\])(juni|jun)':        '06',
        '(?<=[\b-\\\\])(juli|jul)':        '07',
        '(?<=[\b-\\\\])(augustus|aug)':    '08',
        '(?<=[\b-\\\\])(september|sep)':   '09',
        '(?<=[\b-\\\\])(oktober|okt|oct)': '10',
        '(?<=[\b-\\\\])(november|nov)':    '11',
        '(?<=[\b-\\\\])(december|dec)':    '12',
    }
    for pat, repl in replacements.items():
        text = re.sub(pat, repl, text, count=0, flags=re.I)
    return text


def find_datestrings(text) -> list[str]:
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


def get_earliest(datestrings) -> pd.Timestamp:
    "Convert datestrings into timestamps and return earliest date."
    def to_timestamp(datestring) -> pd.Timestamp | None:
        regex = r'(?:[-/\.]|[^\S\n\r])'
        order = ['day', 'month', 'year']
        zipped = zip(order, re.split(regex, datestring))
        dateparts = {unit:int(part) for unit, part in zipped}
        try:
            return pd.Timestamp(**dateparts)
        except ValueError:
            return None
    timestamps = [to_timestamp(i) for i in datestrings]
    return min([i for i in timestamps if i is not None])


def search_name(name: str, text: str, population: pd.DataFrame) -> pd.DataFrame:
    """
    Search text for name. If match is found, return all records from
    population database as DataFrame. Return empty DataFrame if no match.
    """
    regex = re.compile(rf"\b{name}\b")
    match = regex.findall(text)
    if match:
        query = "achternaam == @name"
        return population.query(query)
    else:
        return pd.DataFrame()


def get_kandidaten(geboortedatum: pd.Timestamp) -> pd.DataFrame:
    result = osi.execute_query(
        SQL,
        collegejaar = CONFIG['parser']['collegejaar'],
        geboortedatum = f"{geboortedatum:%Y-%m-%d}"
    )
    return result


def parse_attachment(attachment) -> dict:
    records = []
    record = {}
    record['attachment_id'] = attachment.attachment_id
    record['attachment_name'] = attachment.name
    record['is_pdf'] = is_pdf(attachment)
    if not is_pdf(attachment):
        records.append(record)
        return records
    text = parse_pdf(attachment)
    record['is_parsed'] = bool(text)
    if not bool(text):
        records.append(record)
        return records

    text = remove_whitespace(text)

    record['instelling'] = frozenset(find_institute(text))
    record['bedrag'] = frozenset(find_amounts(text))

    text = replace_months(text)
    dates = find_datestrings(text)
    record['n_dates_found'] = len(dates)
    if not dates:
        records.append(record)
        return records

    date = get_earliest(dates)
    record['search_date'] = date

    candidates = get_kandidaten(record['search_date'])
    record['has_candidates'] = not candidates.empty
    if candidates.empty:
        records.append(record)
        return records

    record['found_student'] = False
    for name in candidates.achternaam.unique():
        student_data = search_name(name, text, candidates)
        if not student_data.empty:
            record['found_student'] = True
            record['n_sinh'] = len(student_data)
            for _, row in student_data.iterrows():
                new_record = record | row.to_dict()
                records.append(new_record)
    if not record['found_student']:
        records.append(record)
    return records


def parse_message(message) -> list:
    records = list()
    record = dict(
        datum_ontvangst = message.received.strftime("%Y-%m-%d %Hh%Mm%Ss"),
        object_id       = message.object_id,
        folder_id       = message.folder_id,
        zender          = str(message.sender),
        flag            = message.flag,
        is_read         = message.is_read,
        onderwerp       = message.subject,
        has_attachments = message.has_attachments,
    )
    if not message.has_attachments:
        records.append(record)
        return records

    message.attachments.download_attachments()
    for attachment in message.attachments:
        parsed_attachment_data = parse_attachment(attachment)
        for parsed_attachment in parsed_attachment_data:
            new_record = record | parsed_attachment
            records.append(new_record)
    return records


def parse_all_messages(messages) -> pd.DataFrame:
    results = []
    for message in messages:
        result = parse_message(message)
        results.extend(result)
    df = pd.DataFrame(results)
    return df
