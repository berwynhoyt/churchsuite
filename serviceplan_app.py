#!/usr/bin/env python3
""" Run a web app on port $PORT (default 8080) to fetch the upcoming service plans from ChurchSuite and export into docx format """

import os
import sys
import io
import logging
import secrets
from datetime import date, timedelta
from zipfile import ZipFile

import flask
from flask import Flask, session, request
from requests_oauthlib import OAuth2Session

from churchsuite import Churchsuite, ChurchsuiteApp
import serviceplan
import config

__version__ = serviceplan.__version__

# Pretty up the web page a bit
Header = """<!DOCTYPE html><html><head><style>
    html { font-family: "Trebuchet MS", sans-serif; }
    h1, h2, h3, h4, h5, h6 { color: #3c4791; margin-bottom: -10px; }
    a { color: #3c4791; }
</style></head><body>"""

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config['SESSION_COOKIE_SECURE'] = True  # send session data only over secure https (set to false below for localhost debugging)

cs = ChurchsuiteApp(app, config.OAuth.CLIENT_ID)

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
@cs.login_required
def docxplans():
    # Fetch original query parameters into serviceplan.args
    args = serviceplan.args
    for k, v in args.__dict__.items():
        setattr(args, k, request.args.get(k, default=v, type=type(v)))
    plans = serviceplan.get_serviceplans(cs)
    if not plans:
        return f"There are no plans in ChurchSuite starting after ({args.starts_after if args.starts_after or args.starts_before else 'today'}) and before ({args.starts_before})"

    # Zip up the plans and send them to the user
    zipstream = io.BytesIO()
    with ZipFile(zipstream, 'w') as zf:
        for plan in plans:
            stream = io.BytesIO()
            filename = serviceplan.plan2docx(cs, plan, stream=stream)
            zf.writestr(filename, stream.getvalue())
    zipstream.seek(0)
    return flask.send_file(zipstream, as_attachment=True, download_name='serviceplans.zip')


if __name__ == "__main__":
    app.config['SESSION_COOKIE_SECURE'] = False # https not required for localhost debugging
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' # allow debug using insecure http://localhost
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=True, host="0.0.0.0", port=port)
