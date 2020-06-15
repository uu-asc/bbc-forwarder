"""script bbc_forwarder
====================

This script will run the complete bbc forwarding routine.
"""

import sys
sys.path.insert(0, '../osiris_query')
from datetime import date
from bbc_forwarder.parser import parser
from bbc_forwarder.mailbox import workspace, folder_ids
from bbc_forwarder.templates import templates, subjects
from bbc_forwarder.population import population
from bbc_forwarder.forwarder import create_report, process_attachment


# create logs
to_process = workspace.get_folder(folder_id=folder_ids.to_process)
parsed = parser(to_process, population, limit=None)


# send log report
today = str(date.today())
report = create_report(parsed.frame)

subject = subjects.logs.substitute(date=today, nrecords=len(parsed.frame))
content = templates.logs.substitute(date=today, report=report)
filename = f"logs/{today}.logs.bbc_forwarder.xlsx"
parsed.frame.to_excel(filename)

msg = workspace.get_folder(folder_id=folder_ids.logs).new_message()
msg.subject = subject
msg.body = templates.base.substitute(content=content)
msg.attachments.add(filename)
msg.to.add("csa.asc@uu.nl")
msg.send()


# process attachments
## exclude messages that have more than one pdf
## exclude attachment if no student was found

def check_n_pdf(df):
    "Return index containing object_id's with more than one pdf attached."
    messages_with_pdf = df.query('pdf==True').groupby('object_id')
    more_than_one_pdf = messages_with_pdf.attachment_id.nunique() > 1
    return more_than_one_pdf[more_than_one_pdf].index

too_many_pdf = check_n_pdf(parsed.frame)
query = "found_student == True and object_id not in @too_many_pdf"
df = parsed.frame.query(query)
df.amounts = df.amounts.apply(', '.join)
df.institutes = df.institutes.apply(', '.join)

for attachment_id in df.attachment_id.unique():
    process_attachment(attachment_id)


# move messages with more than one pdf to issues folder
df = parsed.frame.query("object_id in @too_many_pdf")
for object_id in df.object_id.unique():
    msg = mailbox.get_message(object_id=object_id)
    msg.mark_as_unread()
    msg.move(folder_id=folder_ids.issues)
