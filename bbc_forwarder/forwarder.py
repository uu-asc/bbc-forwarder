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


def create_report(df):
    "Create a html-table containing a log report."
    s = pd.Series(dtype=int)
    s.loc['aantal_mails']       = df.object_id.nunique()
    s.loc['unieke_attachments'] = df.attachment_id.nunique()

    attachments = df.groupby("attachment_id")
    s.loc['attachment_is_pdf'] = attachments.pdf.any().sum()
    s.loc['parser_succesvol']  = attachments['parsed?'].any().sum()
    s.loc['student_gevonden']  = attachments.found_student.any().sum()

    central = df.query("soort_inschrijving == 'S'").groupby("attachment_id")
    decentral = df.query("soort_inschrijving != 'S'").groupby("attachment_id")
    s.loc['vti_centraal']   = central.studentnummer.any().sum()
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
            fields = fields.values()
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
    records = logs.loc[select_attachment & not_cancelled]
    first_record = records.iloc[0]
    object_id = first_record.loc['object_id']
    msg = mailbox.get_message(object_id=object_id)

    if len(records) != 1:
        msg.move(folder_ids.issues)
    else:
        studentnummer      = first_record.loc['studentnummer']
        faculteit          = first_record.loc['faculteit']
        soort_inschrijving = first_record.loc['soort_inschrijving']

        substitutions = annotate(records)
        if soort_inschrijving == 'S':
            to = CONFIG.address['uu']
            subject = subjects.annotated.substitute(substitutions)
            content = templates.annotated.substitute(substitutions)
            body = templates.base(content=content)
            fwd = create_forward(msg, to, subject, body)
            fwd.move(folder_ids.annotated)
        else:
            to = CONFIG.address.get(faculteit)
            subject = subjects.forward.substitute(substitutions)
            content = templates.forward.substitute(substitutions)
            body = templates.base(content=content)
            fwd = create_forward(msg, to, subject, body)
            fwd.move(folder_ids.forward)
        msg.move(folder_ids.archived)
