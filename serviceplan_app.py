#!/usr/bin/env python3
""" Run a web app on port $PORT (default 8080) to fetch the upcoming service plans from ChurchSuite and export into docx format """

import os
import sys
import io
import secrets
from datetime import date, timedelta
from zipfile import ZipFile
from types import SimpleNamespace

import jinja2
import flask
from flask import Flask, session, request, redirect, render_template_string
from requests_oauthlib import OAuth2Session

from churchsuite import Churchsuite, ChurchsuiteApp
import serviceplan
import config

__version__ = serviceplan.__version__

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config['SESSION_COOKIE_SECURE'] = True  # send session data only over secure https (set to false below for localhost debugging)

cs = ChurchsuiteApp(app, config.OAuth.CLIENT_ID)

# If there is more than one app run by this server, override this in the parent app that imports this module """
@app.errorhandler(404)
def notfound(e):
    if request.path == '/':
        return redirect('/docx')
    return "<h1>Not found</h1>The requested URL was not found on this server.", 404

@app.route('/docx')
def home():
    """ Display home page """
    return render_template_string(templates.home, __version__=__version__)

@app.route('/docx/version')
def version():
    return __version__

@app.route('/docx/plans')
@cs.login_required
def plans():
    today = date.today()
    future = f"{request.url_root}docx/download?fontsize={serviceplan.args.fontsize}&starts_after={today}"
    past = f"{request.url_root}docx/download?fontsize={serviceplan.args.fontsize}&starts_after={today-timedelta(days=31)}&starts_before={today}"
    return render_template_string(templates.plans, future=future, past=past)

@app.route('/docx/download')
@cs.login_required
def download():
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


# HTML pages

templates = SimpleNamespace(
    header = """<!DOCTYPE html><html> <head><style> {% include 'css' %} </style><link rel="icon" href="data:,"></head> <body>""",
    footer = """</body></html>""",

    css = """
        body { margin: 0 30px; }
        html { font-family: "Trebuchet MS", sans-serif; }
        h1, h2, h3, h4, h5, h6 { color: #3c4791; margin-bottom: -10px; }
        a { color: #3c4791; }
        input { color: #3c4791; accent-color: #3c4791; font-family: "Trebuchet MS", sans-serif; }
        input[type="submit"] { font-weight: bold; cursor: pointer; }
        .note-box {
            border: 2px solid #333; /* Thick solid border */
            background-color: #f9f9f9; /* Light grey background */
            padding: 0px 15px; /* top and  bottom inside box */
            border-radius: 5px;
        }
    """,

    home = """
        {% include 'header' %}
        <h1>DocExport</h1>
        <p style="color: #3c4791;"><b>Church service plan beautifier for ChurchSuite that exports service plans as docx files.<br/>Version {{ __version__ }}.
            Source code and documentation <a href="https://github.com/berwynhoyt/churchsuite">here</a>.</b></p>

        <form action="/docx/plans" >
            <label for="future">Select service plans:</label><br>
                <input type="radio" id="future" name="timeperiod" value="future" checked>
                    <label for="future">Future</label><br>
                <input type="radio" id="past" name="timeperiod" value="past">
                    <label for="past">Past</label><br><br>
            <div id="id_section" hidden>
                <label for="client_id">Client Identifier<sup>(<b>Note 1</b>)</sup>:</label>
                    <input type="text" id="client_id" name="client_id" value="">
                    <div id="linksection" style="visibility:hidden; margin-left: 20px;">(direct link: <a id="autolink" href="{{ request.base_url }}?client_id=">link</a>)</div><br><br>
            </div>
          <input type="submit" value="Get service plans">
        </form>

        <div id="note1" hidden>
            <br><br>
            <p><b>Note 1</b>: To use this app you need a Client Identifier from ChurchSuite. Your browser will remember the number you enter here. Obtain this by setting up this app in ChurchSuite at:
              <pre>    User Menu -> Settings -> OAuth Apps -> Add OAuth App</pre>
            When adding an app, select "Public" for Application Type, and enter the following into the "Redirect URI" field:
              <pre>    {{ request.url_root }}login/callback</pre>
            ChurchSuite will then display your "Client Identifier" in your newly created app.</p>
        </div>

        <script>
            const params = new URLSearchParams(window.location.search)
            const form = document.querySelector('form');
            const autolink = document.querySelector('#autolink')
            function getCookie(name) {
                let value = `; ${document.cookie}`;
                let parts = value.split(`; ${name}=`);
                if (parts.length === 2) return parts.pop().split(';').shift();
            }

            // Store client_id back into cookie on submit
            form.onsubmit = function(form) {
                const date = new Date();
                date.setTime(date.getTime() + ( 400 * 24 * 60 * 60 * 1000)); // 400 days is max that browsers allow
                document.cookie = "churchsuite_client_id=" + encodeURIComponent(form.client_id.value) + ";expires=" + date.toUTCString() + ";path=/";
                return true; // true allows form submission
            }

            // Ask for client_id only if it wasn't supplied in the url
            document.querySelector('#id_section').hidden = params.get('client_id')? true: false;
            document.querySelector('#note1').hidden = params.get('client_id')? true: false;

            // Auto-fill client_id from query parameter or cookie on load
            form.client_id.value = params.get('client_id') ?? getCookie('churchsuite_client_id') ?? '';

            // Update automatic client_id link as user types
            const input = document.querySelector('#client_id')
            input.onchange = input.onkeyup = function(input) {
                autolink.search = '?client_id=' + encodeURIComponent(form.client_id.value);
                autolink.textContent = autolink.href
                document.querySelector('#linksection').style.visibility = form.client_id.value? 'visible': 'hidden';
            };
            input.onchange()
        </script>
        {% include 'footer' %}
    """,

    plans = """
        {% include 'header' %}
        <p>Download service plans for <a href="{{ future }}">the future</a> or <a href="{{ past }}">the past month</a>.
        {% include 'footer' %}
    """,
)

# Allow jinja to load the string templates defined above
string_loader = jinja2.DictLoader(vars(templates))
app.jinja_env.loader = jinja2.ChoiceLoader([string_loader, app.jinja_env.loader])


if __name__ == "__main__":
    app.config['SESSION_COOKIE_SECURE'] = False # https not required for localhost debugging
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' # allow debug using insecure http://localhost
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=True, host="0.0.0.0", port=port)
