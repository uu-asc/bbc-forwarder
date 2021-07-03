"""script bbc_forwarder
====================

This script will run the complete bbc forwarding routine:

1. Parse all emails in the 'to_process' folder
2. Create a report and send logs to 'logs' folder (if 'send_log_report' is set
to True in config)
3. Process all attachments that were successfully parsed:
    - Move email to 'issues' folder if no or more than one record is associated
    to the attachment.
    - Forward to faculty if record pertains to decentral enrolment application.
    - Send to csa mailbox if record pertains to central enrolment application.
4. Move any emails to 'issues' folder that contain no or more than one pdf
attachment.

If killswitch is set to True in config, the script will not run.
"""

import sys
sys.path.insert(0, '../osiris_query')
from datetime import date
from bbc_forwarder.config import CONFIG, PATH
from bbc_forwarder.parser import parser
from bbc_forwarder.mailbox import mailbox, workspace, folder_ids
from bbc_forwarder.templates import templates, subjects
from bbc_forwarder.population import population
from bbc_forwarder.forwarder import create_report, process_attachment


def find_too_many_pdf(df):
    "Return list containing object_id's with more than one pdf attached."
    messages_with_pdf = df.query('pdf==True').groupby('object_id')
    more_than_one_pdf = messages_with_pdf.attachment_id.nunique() > 1
    return more_than_one_pdf[more_than_one_pdf].index.to_list()


def find_no_pdf(df):
    "Return list containing object_id's with no pdf attached."
    no_pdf = df.groupby('object_id').pdf.sum() == 0
    return no_pdf[no_pdf].index.to_list()


def find_pdf_not_parsed(df):
    "Return list containing object_id's with no pdf attached."
    pdf_not_parse = ~df.groupby('object_id')['parsed?'].any()
    return pdf_not_parse[pdf_not_parse].index.to_list()

if __name__ == '__main__' and not CONFIG.forwarder.settings['killswitch']:
    # create logs
    to_process = workspace.get_folder(folder_id=folder_ids.to_process)
    parsed = parser(to_process, population, limit=None)


    # send log report
    today = str(date.today())
    report = create_report(parsed.frame)

    subject = subjects.logs.substitute(date=today, nrecords=len(parsed.frame))
    content = templates.logs.substitute(date=today, report=report)
    filename = f"logs/{today}.logs.bbc_forwarder.xlsx"
    parsed.frame.to_excel(PATH / filename)

    msg = workspace.get_folder(folder_id=folder_ids.logs).new_message()
    msg.subject = subject
    msg.body = templates.base.substitute(content=content)
    msg.attachments.add(filename)
    msg.to.add(CONFIG.forwarder.address['uu'])
    msg.send()


    # process attachments
    ### exclude messages that have no pdf
    ### exclude messages that have more than one pdf
    ### exclude attachment if no student was found

    if 'found_student' in parsed.frame.columns:
        no_pdf = find_no_pdf(parsed.frame)
        too_many_pdf = find_too_many_pdf(parsed.frame)
        pdf_not_parsed = find_pdf_not_parsed(parsed.frame)

        query = "found_student and object_id not in @too_many_pdf"
        df = parsed.frame.query(query)

        df.amounts = df.amounts.apply(', '.join)
        df.institutes = df.institutes.apply(', '.join)

        for attachment_id in df.attachment_id.unique():
            # this will move messages to issues
            # when no records or too many records were found
            process_attachment(attachment_id, df)


        # move messages with no or more than one pdf to issues folder
        other_issues = no_pdf + too_many_pdf + pdf_not_parsed
        df = parsed.frame.query("object_id in @other_issues")
        for object_id in df.object_id.unique():
            msg = mailbox.get_message(object_id=object_id)
            msg.mark_as_unread()
            msg.move(folder_ids.issues)
