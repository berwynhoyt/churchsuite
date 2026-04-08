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

def get_secret(secret_id, version_id="latest"):
    """ Access Google Secret Manager for the given secret_id; version_id can be "latest" or a specific number.
        If environment variable GOOGLE_CLOUD_PROJECT is not defined, instead look up the secret_id in secret_app.py (for local testing).
    """
    if not os.getenv('GAE_ENV') and request.host.startswith('localhost'):
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

@app.route("/version")
def version():
    return __version__

@app.route("/")
def home():
    """ Display home page """
    today = date.today()
    future = f"{request.url_root}docxplans?fontsize={serviceplan.args.fontsize}&starts_after={today}"
    past = f"{request.url_root}docxplans?fontsize={serviceplan.args.fontsize}&starts_after={today-timedelta(days=31)}&starts_before={today}"
    output = f"""
        <h1>Docx Service Plan Export Tool v{__version__} for ChurchSuite</h1>
        <p>Download service plans for <a href="{future}">the future</a> or <a href="{past}">the past month</a> plans.
    """
    return output

@app.route("/docxplans")
def docxplans():
    if 'token' not in session:
        # Store any query parameters into session, and remember query path
        session['query_params'] = dict(request.args)
        session['query_endpoint'] = request.path
        return redirect(url_for('login'))
    args = serviceplan.args
    for k, v in serviceplan.args.__dict__.items():
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
    oauth = OAuth2Session(get_secret('client_id'), redirect_uri=callback_url, scope=[cs.Churchsuite.scope])
    authorization_url, state = oauth.authorization_url(cs.Churchsuite.auth_url)
    session['oauth_state'] = state  # store for checking by the request_uri when redirected back there
    return redirect(authorization_url)

@app.route("/callback")
def callback():
    """ OAuth callback containing authorization token """
    # Fetch original query parameters into serviceplan.args
    if request.args.get('state') != session.pop('oauth_state'):
        return "Invalid state parameter", 400

    callback_url = request.url_root + 'callback'
    oauth = OAuth2Session(get_secret('client_id'), redirect_uri=callback_url, scope=[cs.Churchsuite.scope])
    json = oauth.fetch_token(cs.Churchsuite.token_url, authorization_response=request.url, client_secret=get_secret('client_secret'))
    session['token'] = json.get('access_token')

    endpoint = session.get('query_endpoint', '/')
    query_params = session.get('query_params', {})
    return redirect(url_for(endpoint.lstrip('/'), **query_params))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='count', default=0, help="Increase verbosity level (e.g., -vv).")
    parser.add_argument('--version', action='store_true', help="Print version number of this script and exit.")

    logging.basicConfig(level=logging.INFO, format=f'%(levelname)s: %(message)s')
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=True, host="0.0.0.0", port=port)
