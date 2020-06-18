"""forwarder module
================

The forwarder module contains several functions for annotating and forwarding
messages. The main function is `process attachment` which contains the logic for
deciding what to do with a message based on its attachment:

1. If no or more than one record was associated with the attachment, then move
it to the 'issues' folder.
2. If the record refers to a central enrolment application, then create a
message from the 'annotated' template and forward it to the csa.
3. If the record refers to a decentral enrolment application, then create a
message from the 'forward' template and forward it to the relevant faculty.

The module further contains the following helper functions:

create_report : create table with report for logs mail
annotate : create tables with logging information
create_forward : create forward from email
"""

from string import Template
import pandas as pd

from bbc_forwarder.config import CONFIG
from bbc_forwarder.templates import templates, subjects
from bbc_forwarder.mailbox import mailbox, folder_ids


def create_report(df):
    "Create a html-table containing a log report."
    s = pd.Series(dtype=int)
    if df.empty:
        return 'Geen enkele e-mail verwerkt.'
    s.loc['aantal_mails'] = df.object_id.nunique()

    if 'attachment_id' in df.columns:
        s.loc['unieke_attachments'] = df.attachment_id.nunique()
        attachments = df.groupby("attachment_id")
        s.loc['attachment_is_pdf'] = attachments.pdf.any().sum()
        s.loc['parser_succesvol'] = attachments['parsed?'].any().sum()

        if 'found_student' in df.columns and df.found_student.any():
            s.loc['student_gevonden'] = attachments.found_student.any().sum()
            query = "soort_inschrijving == 'S'"
            central = df.query(query).groupby("attachment_id")
            s.loc['vti_centraal'] = central.studentnummer.any().sum()
            decentral = df.query(f"not {query}").groupby("attachment_id")
            s.loc['vti_decentraal'] = decentral.studentnummer.any().sum()
    return s.to_frame().to_html(header=None)


def annotate(records):
    "Create a dictionary of html-tables containing annotation data."
    fields = dict(
        bbc = {
            'received':   'datum_ontvangst',
            'sender':     'zender',
            'subject':    'onderwerp',
            'institutes': 'instelling',
            'amounts':    'bedrag',
        },
        student = [
            'studentnummer',
            'voorletters',
            'voorvoegsels',
            'achternaam',
            'geboortedatum',
        ],
        vti = [
            'soort_inschrijving',
            'opleiding',
            'faculteit',
            'inschrijvingstatus',
            'datum_vti',
            'ingangsdatum',
            'afloopdatum',
            'examentype',
        ],
    )
    substitutions = {}
    for key, values in fields.items():
        if isinstance(values, dict):
            records = records.rename(values, axis=1)
            values = values.values()
        substitutions[key] = records[values].astype(str).T.to_html(header=False)
    return substitutions


def create_forward(msg, recipient, subject, body):
    "Create a forward from `msg` with `subject`, `body` and `recipient`."
    fwd = msg.forward()
    fwd.body = body
    fwd.subject = subject
    fwd.to.add(recipient)
    fwd.save_draft()
    return fwd


def get_address(keys):
    """Loop through `keys` and return the first address where the key matches a
    key in `CONFIG.forwarder.address`. Return None if no match was found."""
    address = CONFIG.forwarder.address
    items = (item.lower() for item in keys)
    generator = (item for item in items if item in address)
    key = next(generator, None)
    return address.get(key)


def process_attachment(attachment_id, logs):
    """Process `attachment_id` from `logs` with the following steps:

    1. selecting records from `logs` pertaining to `attachment_id`.
    2. removing cancelled enrolments from those records.
    3. checking how many records are left.
    4. if the number of records is not 1, move it to issues.
    5. else: annotate the record
    6. forward it to faculty or send it to own mailbox.
    7. archive message.
    """
    select_attachment = logs.attachment_id == attachment_id
    not_cancelled = logs.inschrijvingstatus != 'G'
    records = logs.loc[select_attachment & not_cancelled].copy()
    first_record = records.iloc[0]
    object_id = first_record.loc['object_id']
    msg = mailbox.get_message(object_id=object_id)

    if len(records) != 1:
        msg.move(folder_ids.issues)
    else:
        studentnummer      = first_record.loc['studentnummer']
        soort_inschrijving = first_record.loc['soort_inschrijving']

        keys = dict(
            opleiding   = first_record.loc['opleiding'],
            aggregaat_2 = first_record.loc['aggregaat_2'],
            aggregaat_1 = first_record.loc['aggregaat_1'],
            faculteit   = first_record.loc['faculteit'],
        )

        substitutions = annotate(records)
        if soort_inschrijving == 'S':
            to = CONFIG.forwarder.address['uu']
            subject = subjects.annotated.substitute(studentnummer=studentnummer)
            content = templates.annotated.substitute(substitutions)
            body = templates.base.substitute(content=content)
            fwd = create_forward(msg, to, subject, body)
            draft = CONFIG.forwarder.settings['draft_annotated']
            if draft:
                fwd.move(folder_ids.annotated)
            else:
                fwd.send()
        else:
            to = get_address(keys.values())
            subject = subjects.forward.substitute(studentnummer=studentnummer)
            content = templates.forward.substitute(substitutions)
            body = templates.base.substitute(content=content)
            fwd = create_forward(msg, to, subject, body)
            draft = CONFIG.forwarder.settings['draft_forward']
            if draft or to is None:
                fwd.move(folder_ids.forward)
            else:
                fwd.send()
        msg.move(folder_ids.archived)
