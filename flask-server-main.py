import os

import flask
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

app = flask.Flask(__name__)
app.secret_key = 'mot2passe'

CLIENT_SECRETS_FILE = "../web_client_secret.json"
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


@app.route('/')
def index():
    return '<a href="/emails_live">Récupérer ses emails</a>'


@app.route('/authorize')
def authorize():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=flask.url_for('oauth2callback', _external=True, _scheme='http'))

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    flask.session['state'] = state
    return flask.redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
    state = flask.session['state']
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=flask.url_for('oauth2callback', _external=True, _scheme='http')
    )

    flow.fetch_token(authorization_response=flask.request.url)
    credentials = flow.credentials
    with open('../web_client_token.json', 'w') as token:
        token.write(credentials.to_json())
    return flask.redirect('/emails_live')


@app.route('/emails')
def emails():
    creds = Credentials.from_authorized_user_file('../web_client_token.json', SCOPES)
    service = build('gmail', 'v1', credentials=creds)

    results = service.users().messages().list(userId='me', maxResults=5).execute()
    messages = results.get('messages', [])

    email_list = []
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
        headers = msg_data['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        email_list.append(f"<p><strong>{subject}</strong> - {sender}</p>")

    return '<h1>Derniers emails</h1>' + ''.join(email_list)


@app.route('/emails_live')
def emails_live():
    creds = None
    if os.path.exists('../web_client_token.json'):
        creds = Credentials.from_authorized_user_file('../web_client_token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            return flask.redirect('/authorize')
    return '''
    <html>
      <head>
        <meta charset="utf-8">
        <title>Emails en temps réel</title>
      </head>
      <body>
        <h1>Derniers emails</h1>
        <p>Prochaine mise à jour dans <span id="countdown">5</span> secondes</p>
        <div id="emails"></div>

        <script>
          let countdown = 5;

          function updateCountdown() {
            document.getElementById('countdown').innerText = countdown;
            countdown--;
            if (countdown < 0) {
              fetchEmails();
              countdown = 5;
            }
          }

          async function fetchEmails() {
            const res = await fetch('/emails');
            const data = await res.text();
            document.getElementById('emails').innerHTML = data;
          }

          // Premier chargement
          fetchEmails();
          setInterval(updateCountdown, 1000); // mise à jour chaque seconde
        </script>
      </body>
    </html>
    '''



if __name__ == '__main__':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run('localhost', 9090, debug=True)
