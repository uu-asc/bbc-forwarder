"""mailbox module
==============

The mailbox module creates the workspace for the bbc-forwarder. It contains
several objects for manipulating the microsoft office 365 mailbox.

`config.json` needs to be properly configured in order for the bbc-forwarder to
work. It should contain:

- the main resource (what mailbox to access)
- the authentication credentials
- the scopes
- the redirect uri
- the workspace location
- the names of the workspace folders

Make sure to register the app in Azure as well.
https://portal.azure.com/

More information
----------------
See the following links for more information on how authentication works:
- [Get access on behalf of a user - Microsoft Graph | Microsoft Docs](https://docs.microsoft.com/en-us/graph/auth-v2-user?context=graph%2Fapi%2F1.0&view=graph-rest-1.0)
- [O365 - Oauth Authentication](https://github.com/O365/python-o365#oauth-authentication)
"""

from pathlib import Path
from O365 import Account, FileSystemTokenBackend
from bbc_forwarder.config import CONFIG, to_namedtuple


token_path = Path(CONFIG['mailbox']['token_path']).expanduser().resolve()
token_filename = CONFIG['mailbox']['token_filename']
print(token_path / token_filename)

token_backend = FileSystemTokenBackend(
    token_path = token_path,
    token_filename = token_filename,
)
credentials = (CONFIG['mailbox']['app_client_id'], CONFIG['mailbox']['secret'])
scopes = CONFIG['mailbox']['scopes']
main_resource = CONFIG['mailbox']['main_resource']


account = Account(
    credentials,
    main_resource = CONFIG['mailbox']['main_resource'],
    token_backend = token_backend,
    # redirect_uri=CONFIG['mailbox']['redirect_uri'],
)

if not account.is_authenticated:
    if account.authenticate(scopes=CONFIG['mailbox']['scopes']):
       print('O365 Authenticated!')


MAILBOX = account.mailbox()

WORKSPACE = MAILBOX.inbox_folder()
if CONFIG['forwarder']['location'] is not None:
    destination = CONFIG['forwarder']['location'].split('/')
    for folder in destination:
        WORKSPACE = WORKSPACE.get_folder(folder_name=folder)

workspace_folders = WORKSPACE.get_folders()
found_folders = {folder.name:folder.folder_id for folder in workspace_folders}
expected_folders = CONFIG['forwarder']['folders'].values()
if not all(folder in found_folders for folder in expected_folders):
    raise EnvironmentError(
        "\nSANITY CHECK FAILED :\n"
        "One or more workspace folders were not in the expected location."
    )

FOLDER_IDS = {
    k:found_folders[v]
    for k,v in CONFIG['forwarder']['folders'].items()
}
