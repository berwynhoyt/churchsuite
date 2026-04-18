#!/usr/bin/env python3
""" Run a web app on port $PORT (default 8080) to fetch the upcoming service plans from ChurchSuite and export into docx format """

import os
import sys
import io
import logging
import secrets
from datetime import date, timedelta
from zipfile import ZipFile

from requests_oauthlib import OAuth2Session
from flask import Flask, session, request, redirect, url_for, send_file
from google.cloud import secretmanager
import churchsuite as cs
import serviceplan

__version__ = serviceplan.__version__

# Pretty up the web page a bit
Header = """<!DOCTYPE html><html><head><style>
    html { font-family: "Trebuchet MS", sans-serif; }
    h1, h2, h3, h4, h5, h6 { color: #3c4791; margin-bottom: -10px; }
    a { color: #3c4791; }
</style></head><body>"""

def get_secret(secret_id, version_id="latest"):
    """ Access Google Secret Manager for the given secret_id; version_id can be "latest" or a specific number.
        If environment variable GOOGLE_CLOUD_PROJECT is not defined, instead look up the secret_id in secret_app.py (for local testing).
    """
    if request.host.startswith('localhost') and not os.getenv('GAE_ENV'):
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' # allow debug using insecure http://localhost
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    if not project_id:
        print(f"Importing secret {secret_id} from secret_app.py")
        import secret_app
        return getattr(secret_app, secret_id)
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config['SESSION_COOKIE_SECURE'] = True # make app send session data only over secure https (set to false for localhost debugging below

@app.route("/version")
def version():
    return __version__

@app.route("/")
def home():
    """ Display home page """
    today = date.today()
    future = f"{request.url_root}docxplans?fontsize={serviceplan.args.fontsize}&starts_after={today}"
    past = f"{request.url_root}docxplans?fontsize={serviceplan.args.fontsize}&starts_after={today-timedelta(days=31)}&starts_before={today}"
    output = f"""{Header}
        <h1>DocExport</h1>
        <p style="color: #3c4791;"><b>Church service plan beautifier for ChurchSuite that exports service plans as docx files.<br/>Version {__version__}.
            Source code and documentation <a href="https://github.com/berwynhoyt/churchsuite">here</a>.</b></p>
        <p>Download service plans for <a href="{future}">the future</a> or <a href="{past}">the past month</a>.
    """
    return output

@app.route("/docxplans")
def docxplans():
    if 'token' not in session:
        # Store any query parameters into session, and remember query path
        session['query_params'] = dict(request.args)
        session['query_endpoint'] = request.path
        return redirect(url_for('login'))
    # Fetch original query parameters into serviceplan.args
    args = serviceplan.args
    for k, v in args.__dict__.items():
        setattr(args, k, request.args.get(k, default=v, type=type(v)))
    db = cs.Churchsuite(token=session.get('token'))
    plans = serviceplan.get_serviceplans(db)
    if not plans:
        return f"There are no plans in ChurchSuite starting after ({args.starts_after if args.starts_after or args.starts_before else 'today'}) and before ({args.starts_before})"

    # Zip up the plans and send them to the user
    zipstream = io.BytesIO()
    with ZipFile(zipstream, 'w') as zf:
        for plan in plans:
            stream = io.BytesIO()
            filename = serviceplan.plan2docx(db, plan, stream=stream)
            zf.writestr(filename, stream.getvalue())
    zipstream.seek(0)
    return send_file(zipstream, as_attachment=True, download_name='serviceplans.zip')

@app.route("/login")
def login():
    """ Get ChurchSuite authorization token and store it in the session """
    callback_url = request.url_root + 'callback'
    client_id = get_secret('client_id')
    oauth = OAuth2Session(client_id, redirect_uri=callback_url, scope=[cs.Churchsuite.scope], pkce='S256')
    authorization_url, state = oauth.authorization_url(cs.Churchsuite.auth_url)
    # Store items for checking by the callback when redirected back there
    session['oauth_state'] = state
    session['code_verifier'] = oauth._code_verifier
    session['client_id'] = client_id
    return redirect(authorization_url)

@app.route("/callback")
def callback():
    """ OAuth callback containing authorization token """
    if request.args.get('state') != session.pop('oauth_state'):
        return "Invalid state parameter", 400

    callback_url = request.url_root + 'callback'
    oauth = OAuth2Session(session.pop('client_id'), redirect_uri=callback_url)
    json = oauth.fetch_token(cs.Churchsuite.token_url, authorization_response=request.url, code_verifier=session.pop('code_verifier'))
    session['token'] = json.get('access_token')

    endpoint = session.get('query_endpoint', '/')
    query_params = session.get('query_params', {})
    return redirect(url_for(endpoint.lstrip('/'), **query_params))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='count', default=0, help="Increase verbosity level (e.g., -vv).")
    parser.add_argument('--version', action='store_true', help="Print version number of this script and exit.")
    args = parser.parse_args()

    # Set increasing logging level based on -v flag
    log_level = logging.WARNING - 10*args.verbose
    logging.basicConfig(level=log_level, format=f'%(levelname)s: %(message)s')

    app.config['SESSION_COOKIE_SECURE'] = False # https not required for localhost debugging
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=True, host="0.0.0.0", port=port)
