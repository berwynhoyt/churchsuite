#!/usr/bin/env python3
""" Library to access ChurchSuite data conveniently """

import json
import os.path
import logging
import pprint

from types import SimpleNamespace
from functools import wraps
from urllib.parse import urljoin

import requests
from flask import url_for, session, request, redirect
from requests_oauthlib import OAuth2Session

import config


__version__ = '1.0.0'

# List of URLs for ChurchSuite access
class URL:
    api = 'https://api.churchsuite.com/v2/'

    plans = api + 'planning/plans'
    plan_items = api + 'planning/plan_items'
    contacts = api + 'addressbook/contacts'

def dump_request(req):
    """ Debugging function to dump a PreparedRequest from request.Request().prepare() or response.request """
    output = f"{req.method} {req.path_url} HTTP/1.1\n"
    output += '\n'.join(f'{k}: {v}' for k, v in req.headers.items())
    output += "\n\n"
    if req.body is not None:
        # Decode body if it is in bytes, handling potential encoding issues
        output += req.body.decode('utf-8') if isinstance(req.body, bytes) else req.body
    return output

def joiner(*args):
    """ Join multiple args to the end of a url, separating them with '/' """
    return '/'.join(str(arg) for arg in args if arg is not None)

def trace_logging():
    """ Detect whether trace-level logging is enabled with a log_level even more verbose than DEBUG (-vvv) """
    return logging.getLogger(__name__).getEffectiveLevel() < logging.DEBUG

class Churchsuite:
    """ Class used to access ChurchSuite data """

    token_url = "https://login.churchsuite.com/oauth2/token"
    auth_url = "https://login.churchsuite.com/oauth2/authorize"
    scope = 'full_access'

    def __init__(self, access_token=None, auth=None, raw=None):
        """ Create ChurchSuite instance for access to ChurchSuite data.
            If access_token is not supplied, attempt to get one using user auth (client_id, client_secret).
            If filename raw is supplied, store all json text received from the server into that file.
        """
        self.access_token = access_token or self.authorize(*auth)
        self.raw = raw
        if raw is not None:
            # truncate file
            open(raw, 'w').close()

    def append_raw(self, text):
        if self.raw is not None:
            with open(self.raw, 'a') as f:
                f.write(text)

    def authorize(self, client_id, client_secret, scope=('full_access',)):
        """ Return access_token using api_enbaled_user authorization with the supplied authorization credentials.
            scope: is a sequence of scopes
        """
        auth = (client_id, client_secret)
        data = {'grant_type': 'client_credentials', 'scope': ','.join(scope)}
        r = requests.post(self.token_url, auth=auth, json=data, headers={'Content-Type': 'application/json'})
        r.raise_for_status()
        return r.json().get('access_token')

    def get(self, url, id=None, item=None, *, params=None, **kwargs):
        """ Return 'data' field from ChurchSuite GET response as a SimpleNamespace, or list of SimpleNamespaces if the request returns a list.
            If id or item are supplied, they are prefixed with '/' and appended as strings to the url.
            If params dict is supplied, it is updated with kwargs and then sent as json params to the url.
        """
        url = joiner(url, id, item)
        if params is None:
            params = {}
        params.update({k: str(v) for k, v in kwargs.items()})
        r = requests.get(url, headers={'Authorization': f'Bearer {self.access_token}'}, params=params)
        if trace_logging():
            logging.debug(f"request: {dump_request(r.request).replace('\n', '\n|  ')}")
        r.raise_for_status()
        self.append_raw(json.dumps(r.json(), indent=4) + '\n')
        # Convert json dict to SimpleNamespace (recursively for sub-objects)
        object = json.loads(r.text, object_hook=lambda d: SimpleNamespace(**d))
        formatted_response = f"GET {url} =>\n| {pprint.pformat(object).replace('\n', '\n| ')}"
        if trace_logging():
            logging.debug(formatted_response)
        if not hasattr(object, 'data'):
            raise Exception("No 'data' field found in response to {formatted_response}")
        return object.data


def test_manual_authorization(client_id, client_secret=None, redirect_url=None, state=None):
    """ Fetch access access_token using oauth_app authorization with the supplied authorization credentials.
        This is a test function to simulate what occurs with authorize_app_stage{1,2}()
    """
    from requests_oauthlib import OAuth2Session
    oauth = OAuth2Session(client_id, redirect_uri=redirect_url, scope=('full_access',), pkce='S256')
    authorization_url, state = oauth.authorization_url(Churchsuite.auth_url, state=state)
    code_verifier = oauth._code_verifier  # fetch from private field as requests-oauthlib does not yet support a public access method
    # In a web app, you would save state for later: session['oauth_state'] = state
    # Simulate callback into Python here by making the user paste in the URL that came back to the browser from to the redirect_url
    print(f"Please authorize at:")
    print(f"    {authorization_url}")
    print()
    print(f"Note: after login, the browser may say the site can't be reached (because you're not running a web server).")
    print(f"But the URL shown in the address bar will still be suitable for pasting here.")
    authorization_response_url = input('Enter the full callback URL (shown in the browser address bar): ')
    # Check that request.args.get('state') != session.pop('oauth_state'); otherwise bomb out with error 400
    # code_verifier = session.pop('code_verifier')
    oauth = OAuth2Session(client_id, redirect_uri=redirect_url)
    oauth._code_verifier = code_verifier  # store into a private field as requests-oauthlib does not yet support a public access method
    json = oauth.fetch_token(Churchsuite.token_url, authorization_response=authorization_response_url, code_verifier=code_verifier)
    return json.get('access_token')


class ChurchsuiteApp(Churchsuite):
    def __init__(self, app, client_id=None, client_secret=None, use_pkce=True, login_url='/login', redirect_url='/login/callback', scope=('full_access',)):
        """ ChurchSuite subclass that sets up web server route functions to make the user log in.
            app: the flask app being authorized
            client_id: defaults to flask config.py variable OAuth.CLIENT_ID
            client_secret: defaults to flask config.py variable OAuth.CLIENT_SECRET
            use_pkce: if True, no client_secret is required (better): select 'public' app on ChurchSuite to use this.
            login_url: path of url that any route will redirect to for login (any route decorated with @login_required)
            redirect_url: path of url that ChurchSuite will call back after login (must match the redirect_url set in ChurchSuite app config)
            scope: is a sequence of scopes
        """
        self.app = app
        self.raw = None  # it's unlikely the web server wants to retain all the json data
        self.client_id = client_id or config.OAuth.CLIENT_ID
        self.client_secret = client_secret or getattr(config.OAuth, 'CLIENT_SECRET', None)
        self.use_pkce = use_pkce
        self.login_url = login_url
        self.redirect_url = redirect_url
        self.login_urls = (login_url, redirect_url)
        self.scope = scope

        app.before_request(self._log_request)
        app.after_request(self._log_response)

        app.add_url_rule(login_url, view_func=self._login)
        app.add_url_rule(redirect_url, view_func=self._callback)

    @property
    def access_token(self):
        return session['access_token']

    # Debugging logging of full incoming requests during login
    def _log_request(self):
        if request.path in self.login_urls:
            self.app.logger.debug(f"Auth Req {request.url}:\n|  " + (str(request.headers)+request.get_data(as_text=True)).replace('\n', '\n|  '))
    def _log_response(self, response):
        if request.path in self.login_urls:
            self.app.logger.debug(f"Response status [{response.status} by URL {request.url}:\n|  " + response.get_data(as_text=True).replace('\n', '\n|  '))
        return response

    def _login(self):
        """ Get ChurchSuite authorization access_token and store it in the flask session """
        callback_url = urljoin(request.url_root, self.redirect_url)
        pkce = 'S256' if self.use_pkce else None
        oauth = OAuth2Session(self.client_id, redirect_uri=callback_url, scope=self.scope, pkce=pkce)
        authorization_url, state = oauth.authorization_url(Churchsuite.auth_url)
        # Store items for the callback when redirected back there
        session['oauth_state'] = state
        session['code_verifier'] = oauth._code_verifier
        return redirect(authorization_url)

    def _callback(self):
        """ OAuth callback route that receives the authorization access_token from ChurchSuite """
        if request.args.get('state') != session.pop('oauth_state'):
            return "Invalid state parameter", 400

        callback_url = urljoin(request.url_root, self.redirect_url)
        oauth = OAuth2Session(self.client_id, redirect_uri=callback_url)
        json = oauth.fetch_token(Churchsuite.token_url, authorization_response=request.url, code_verifier=session.pop('code_verifier'))
        session['access_token'] = json.get('access_token')

        return redirect(session.get('next_url', '/'))

    # Define a decorator that requires login for a route and brings them back to the same place.
    # Saves 'next_page' so that it automatically comes back to the page that triggered the login.
    @property
    def login_required(self):
        """ This is a decorator for a view function (route). If the user is not logged in when this route is called,
            save the current page url, redirect the user to login, and bring them back to the same url after login.
        """
        def wrapper(func):
            @wraps(func)
            def check_authorization(*args, **kwargs):
                if 'access_token' not in session:
                    session['next_url'] = request.url
                    return redirect(self.login_url)
                return func(*args, **kwargs)
            return check_authorization
        return wrapper


if __name__ == "__main__":
    client_id = client_id or config.OAuth.CLIENT_ID
    client_secret = client_secret or config.OAuth.CLIENT_SECRET
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' # allow debug using insecure http://localhost
    access_token = test_manual_authorization(client_id, client_secret, redirect_uri='http://localhost:8080/login/callback')
    print(f"\nSuccessful authorization! Token={access_token}")
