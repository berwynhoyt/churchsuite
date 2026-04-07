#!/usr/bin/env python3
""" Run a web app on port $PORT (default 8080) to fetch the upcoming service plans from ChurchSuite and export into docx format """

import os
import sys
import logging
import secrets
from datetime import date

from requests_oauthlib import OAuth2Session
from flask import Flask, session, request, redirect, url_for
from google.cloud import secretmanager
import churchsuite as cs
import serviceplan

__version__ = serviceplan.__version__

def get_secret(secret_id, version_id="latest"):
    """ Access Google Secret Manager for the given secret_id; version_id can be "latest" or a specific number.
        If environment variable GOOGLE_CLOUD_PROJECT is not defined, instead look up the secret_id in secret_app.py (for local testing).
    """
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    if not project_id:
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
    start_date = date.today()
    url = f"{request.url_root}docxplan?fontsize={serviceplan.args.fontsize}&date={start_date.isoformat()}"
    output = [f"<h1>Docx Service Plan Export Tool v{__version__}</h1>"]
    output += [f"""<p>Click <a href="{url}">{url}</a> to fetch the coming week's service plans.</p>"""]
    project = os.environ.get('GOOGLE_CLOUD_PROJECT')
    if project:
        output += [f"<p>Running on Google App Engine with PROJECT_ID={os.environ.get('GOOGLE_CLOUD_PROJECT')}</p>"]
    return '\n'.join(output)

@app.route("/docxplan")
def docxplan():
    if 'token' not in session:
        # Store any query parameters into session, and remember query path
        session['query_params'] = dict(request.args)
        session['query_endpoint'] = request.path
        return redirect(url_for('login'))
    for k, v in serviceplan.args.__dict__.items():
        serviceplan.args[k] = request.args.get(k, default=v, type=type(v))
    cs = serviceplan.Churchsuite(token=session.get('token'))
    plans = cs.upcoming_services(db)
    stream = io.BytesIO()
    filename = cs.plan2docx(plan[0], stream=stream)
    return send_file(stream, as_attachment=True, download_name=filename)

@app.route("/login")
def login():
    """ Get ChurchSuite authorization token and store it in the session """
    oauth = OAuth2Session(get_secret('client_id'), redirect_uri=url_for('callback'), scope=[cs.Churchsuite.scope])
    authorization_url, state = oauth.authorization_url(cs.Churchsuite.auth_url)
    session['oauth_state'] = state  # store for checking by the request_uri when redirected back there
    return redirect(authorization_url)

@app.route("/callback")
def callback():
    """ OAuth callback containing authorization token """
    # Fetch original query parameters into serviceplan.args
    if request.args.get('state') != session.pop('oauth_state'):
        return "Invalid state parameter", 400

    oauth = OAuth2Session(get_secret('client_id'), redirect_uri=url_for('callback'), scope=[cs.Churchsuite.scope])
    json = oauth.fetch_token(cs.Churchsuite.token_url, authorization_response=request.url, client_secret=get_secret('client_secret'))
    session['token'] = json.get('access_token')

    endpoint = session.get('query_endpoint', '/')
    query_params = session.get('query_params', {})
    return redirect(url_for(endpoint, **query_params))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='count', default=0, help="Increase verbosity level (e.g., -vv).")
    parser.add_argument('--version', action='store_true', help="Print version number of this script and exit.")

    logging.basicConfig(level=logging.INFO, format=f'%(levelname)s: %(message)s')
    port = int(os.environ.get("PORT", 8080))
    if not os.getenv('GAE_ENV'):
        print(f"Running as local server on localhost:{port}")
    app.run(debug=True, host="0.0.0.0", port=port)
