"""forwarder module
================

The forwarder module contains several functions for annotating and forwarding
messages. The main function is `process_message` which contains the logic for
deciding what to do with a message based on the associated logging data.

The module further contains the following helper functions:

get_stats : create table with report for logs mail
get_message_data : create tables with logging information
create_forward : create forward from email
"""

import base64
import io

import pandas as pd
from O365.message import Message

from bbc_forwarder.config import CONFIG
from bbc_forwarder.templates import ENV, SUBJECTS, FILENAME
from bbc_forwarder.mailbox import MAILBOX, FOLDER_IDS


def get_message_data(df: pd.DataFrame) -> dict[str, pd.DataFrame|str]:
    record = df.iloc[0]
    mail = [
        'datum_ontvangst',
        'zender',
        'onderwerp',
    ]
    bbc = [
        'instelling',
        'bedrag',
    ]
    student = [
        'studentnummer',
        'voorletters',
        'voorvoegsels',
        'achternaam',
        'geboortedatum',
    ]
    inschrijfregel = [
        'soort_inschrijving',
        'opleiding',
        'faculteit',
        'inschrijvingstatus',
        'datum_verzoek',
        'datum_intrekking',
        'ingangsdatum',
        'afloopdatum',
        'examentype',
    ]
    return {
        # strings
        'msg_id':              record['object_id'],
        'status':              record['status'],
        'soort':               record['soort'],
        'onderwerp':           record['onderwerp'],
        'ontvanger':           record['ontvanger'],
        'opleiding':           record['opleiding'],
        'studentnummer':       ';'.join(df.studentnummer.dropna().unique()),

        # tables
        'mail_data':           df[mail].drop_duplicates().T,
        'bbc_data':            df[bbc].drop_duplicates().T,
        'student_data':        df[student].drop_duplicates().T,
        'inschrijfregel_data': df[inschrijfregel].T,
    }


def get_stats(results, field) -> pd.Series:
    stats = (
        results
        .groupby('object_id')[field]
        .agg(lambda grp: grp.iloc[0])
        .value_counts()
        .rename('aantal')
    )
    stats['Totaal'] = stats.sum()
    return stats


def create_forward(msg, recipient, subject, body) -> Message:
    "Create a forward from `msg` with `subject`, `body` and `recipient`."
    fwd = msg.forward()
    fwd.body = body
    fwd.subject = subject
    fwd.to.add(recipient)
    fwd.save_draft()
    return fwd


def process_message(
    message_id: str,
    template_path: str,
    results: pd.DataFrame,
    test_run: bool = False,
) -> None:
    message = MAILBOX.get_message(object_id=message_id)

    query = f"object_id == '{message_id}'"
    logs = results.query(query)
    data = get_message_data(logs)

    soort         = data['soort']
    status        = data['status']
    studentnummer = data['studentnummer']
    opleiding     = data['opleiding']
    onderwerp     = data['onderwerp']
    ontvanger     = data['ontvanger']

    template = ENV.get_template(template_path)
    body = template.render(**data)

    subject = SUBJECTS[soort].substitute(
        status        = status,
        onderwerp     = onderwerp,
        studentnummer = studentnummer,
        opleiding     = opleiding,
    )

    if test_run:
        ontvanger = ontvanger if ontvanger else 'geen_ontvanger'
        print(f"{soort:.<12}{ontvanger:.<20}{subject}")
        return None

    forward = create_forward(
        message,
        recipient = ontvanger,
        subject = subject,
        body = body,
    )

    if soort in ['csa', 'faculteit']:
        # rename pdf attachment and reattach it
        # remove all other attachments
        forward.attachments.download_attachments()
        for attachment in forward.attachments:
            if attachment.name.lower().endswith('.pdf'):
                content = base64.b64decode(attachment.content)
                new_attachment = io.BytesIO(content)
            forward.attachments.remove(attachment)
        new_name = FILENAME.substitute(studentnummer=studentnummer)
        forward.attachments.add([(new_attachment, new_name)])
        forward.save_draft()

    save_as_draft = CONFIG['forwarder']['settings']['save_as_draft'][soort]
    if save_as_draft or not ontvanger:
        forward.move(FOLDER_IDS[soort])
    else:
        forward.send()
    message.move(FOLDER_IDS['archived'])
    return None
