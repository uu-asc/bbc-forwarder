"""mailbox module
==============

The mailbox module contains the mailbox object which provides an api for
accessing the microsoft office 365 mailbox. Use `config.json` to provide the
necessary credentials. Make sure to register the app in Azure as well.

More information
----------------
See the following links for more information on how authentication works:
- [Get access on behalf of a user - Microsoft Graph | Microsoft Docs](https://docs.microsoft.com/en-us/graph/auth-v2-user?context=graph%2Fapi%2F1.0&view=graph-rest-1.0)
- [O365 - Oauth Authentication](https://github.com/O365/python-o365#oauth-authentication)
"""


from O365 import Account
from bbc_forwarder.config import CONFIG


credentials = (CONFIG.mailbox.app_client_id, CONFIG.mailbox.secret)
scopes = CONFIG.mailbox.scopes
main_resource = CONFIG.mailbox.main_resource


account = Account(
    credentials,
    main_resource=CONFIG.mailbox.main_resource,
    redirect_uri=CONFIG.mailbox.redirect_uri,
    )

if not account.is_authenticated:
    if account.authenticate(scopes=CONFIG.mailbox.scopes):
       print('Authenticated!')


mailbox = account.mailbox()
