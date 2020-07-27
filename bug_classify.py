from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import re
import bugzilla
import sys
from urllib.parse import urlparse
import argparse

URL = "https://bugzilla.redhat.com/xmlrpc.cgi"

# If modifying these scopes, delete the file token.pickle.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# The ID and range of a sample spreadsheet.
SPREADSHEET_ID = "1RIysPmBkQK1Mog1DfTf17FtkjKDDQRXAYhVHdyhvV_s"
SPREADSHEET_RANGE = "In Progress!A2:G8"


def main():
    api_key = get_bugzilla_api_key()
    values = get_list_from_sheets()
    urls = get_urls_from_rows(values)
    bug_ids = get_bug_ids_from_urls(urls)
    bzapi = authenticate_to_bugzilla(api_key)
    update_bugs(bug_ids, bzapi)

    return


def get_bugzilla_api_key():
    f = open("rhbz_api_key", "r")
    lines = f.readlines()
    api_key = ""
    for line in lines:
        api_key += line.replace("\n", "")

    f.close()

    return api_key


def get_bug_ids_from_urls(urls):
    bug_ids = []
    for url in urls:
        o = urlparse(url)
        if not o.query.split:
            continue
        bug_dict = dict(x.split("=") for x in o.query.split("&"))
        bug_id = bug_dict.get("id")

        if bug_id:
            bug_ids.append(bug_id)

    return bug_ids


def authenticate_to_bugzilla(api_key):
    bzapi = bugzilla.Bugzilla(URL, api_key=api_key)
    assert bzapi.logged_in

    return bzapi


def update_bugs(bug_ids, bzapi):
    for bug_id in bug_ids:
        try:
            bug = bzapi.getbug(bug_id)
            if not bug.internal_whiteboard:
                update = bzapi.build_update(internal_whiteboard="Telco:RHCOS Squad:Networking")
            if bug.internal_whiteboard:
                update = bzapi.build_update(internal_whiteboard="%s Telco:RHCOS Squad:Networking" % bug.internal_whiteboard)
            bzapi.update_bugs([bug_id], update)
        except:
            print("Error updating bug: %s You may not have permission to view" % bug_id)


def get_list_from_sheets():
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    service = build("sheets", "v4", credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = (
        sheet.values()
        .get(spreadsheetId=SPREADSHEET_ID, range=SPREADSHEET_RANGE)
        .execute()
    )
    values = result.get("values", [])
    return values


def get_urls_from_rows(values):
    if not values:
        return []
    else:
        urls = []
        for row in values:
            url_a = get_url(row[0])
            url_g = get_url_from_g(row)
            if url_a:
                urls.append(url_a)
            if url_g:
                urls.append(url_g)
        return urls


def get_url_from_g(row):
    if len(row) < 7:
        return None
    else:
        return get_url(row[6])


def get_url(row_string):
    matches = re.findall(r"(https?://bugzilla.redhat.com\S+)", row_string)
    if matches:
        return matches[0]
    else:
        return None


if __name__ == "__main__":
    main()
