import os.path
import base64
from email import message_from_bytes
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def authenticate_gmail():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds


def list_messages(service, user_id='me'):
    results = service.users().messages().list(userId=user_id, maxResults=10).execute()
    messages = results.get('messages', [])
    return messages


def get_message(service, msg_id, user_id='me'):
    message = service.users().messages().get(userId=user_id, id=msg_id, format='raw').execute()
    msg_raw = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))
    mime_msg = message_from_bytes(msg_raw)
    return mime_msg


def main():
    creds = authenticate_gmail()
    service = build('gmail', 'v1', credentials=creds)

    print("Fetching messages...")
    for i in range(101):
        messages = list_messages(service)
    messages = list_messages(service)
    for msg in messages:
        mime_msg = get_message(service, msg['id'])
        print("Subject:", mime_msg['Subject'])
        print("From:", mime_msg['From'])
        print("-" * 40)


if __name__ == '__main__':
    main()
