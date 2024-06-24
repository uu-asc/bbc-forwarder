"""script bbc_forwarder
====================

This script will run the complete bbc forwarding routine:

1. Parse all emails in the 'to_process' folder
2. Create a report and send logs to 'logs' folder (if 'send_log_report' is set
to True in config)
3. Process all messages:
    - Forward to faculty if record pertains to decentral enrolment application.
    - Send to csa mailbox if record pertains to central enrolment application.
    - Send to csa mailbox if record contains an issue.

If killswitch is set to True in config, the script will not run.
"""

from datetime import date

import pandas as pd

from bbc_forwarder.config import CONFIG, PATH
from bbc_forwarder.mailbox import WORKSPACE, FOLDER_IDS
from bbc_forwarder.templates import ENV, SUBJECTS
from bbc_forwarder import parser, dataset, forwarder


def process_messages(
    template: str,
    logs: pd.DataFrame,
    test_run: bool=False,
) -> None:
    for message_id in logs.object_id.unique():
        forwarder.process_message(message_id, template, logs, test_run=test_run)
    return None


def send_log_report(logs) -> None:
    # get data
    today = str(date.today())
    n_records = logs.object_id.nunique()
    per_soort = logs.pipe(forwarder.get_stats, 'soort')
    issues = logs.query("soort == 'issue'").pipe(forwarder.get_stats, 'status')

    # store logs and keep filename
    filename = PATH / f"logs/{today}.logs.bbc_forwarder.xlsx"
    logs.to_excel(filename)

    # create subject and body from templates
    subject = SUBJECTS['logs'].substitute(date=today, nrecords=n_records)
    template = ENV.get_template('template.logs.jinja.html')
    body = template.render(
        n_records = n_records,
        per_soort = per_soort,
        issues = issues,
        today = today,
    )

    # create and send message
    msg = WORKSPACE.get_folder(folder_id=FOLDER_IDS['logs']).new_message()
    msg.subject = subject
    msg.body = body
    msg.attachments.add(filename)
    msg.to.add(CONFIG['forwarder']['address']['csa'])
    msg.send()
    return None


if __name__ == '__main__' and not CONFIG['forwarder']['settings']['killswitch']:
    # create and send logs
    folder = WORKSPACE.get_folder(folder_id=FOLDER_IDS['to_process'])
    messages = folder.get_messages(limit=None)
    parsed_messages = parser.parse_all_messages(messages)
    logs = dataset.create_dataset(parsed_messages)
    if CONFIG['forwarder']['settings']['send_log_report']:
        send_log_report(logs)

    # process messages
    test_run = CONFIG['forwarder']['settings']['test_run']
    tasks = CONFIG['forwarder']['tasks']
    for template, queries in tasks.items():
        for query in queries:
            df = logs.query(query)
            process_messages(template, df, test_run=test_run)