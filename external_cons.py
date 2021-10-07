from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from typing import Any

async def the_drive() -> Any:
    """ Gets the GoogleDrive connection. """

    gauth = GoogleAuth()
    # gauth.LocalWebserverAuth()
    gauth.LoadCredentialsFile("mycreds.txt")
    if gauth.credentials is None:
        # This is what solved the issues:
        gauth.GetFlow()
        gauth.flow.params.update({'access_type': 'offline'})
        gauth.flow.params.update({'approval_prompt': 'force'})

        # Authenticate if they're not there
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:

        # Refresh them if expired
        gauth.Refresh()
    else:

        # Initialize the saved creds
        gauth.Authorize()

    # Save the current credentials to a file
    gauth.SaveCredentialsFile("mycreds.txt")

    drive = GoogleDrive(gauth)
    return drive