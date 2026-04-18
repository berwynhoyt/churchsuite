#!/usr/bin/env python3
""" Library to access ChurchSuite data conveniently """

import requests
import json
import os.path
import logging
import pprint

from types import SimpleNamespace

from requests_oauthlib import OAuth2Session

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

    def __init__(self, token=None, auth=None, raw=None):
        """ Create ChurchSuite instance for access to ChurchSuite data.
            If token is not supplied, attempt to get one using user auth (client_id, client_secret).
            If filename raw is supplied, store all json text received from the server into that file.
        """
        if not token:
            token = self.authorize(*auth)
        self.token = token
        self.raw = raw
        if raw is not None:
            # truncate file
            open(raw, 'w').close()

    def append_raw(self, text):
        if self.raw is not None:
            with open(self.raw, 'a') as f:
                f.write(text)

    def authorize(self, client_id, client_secret):
        """ Return access token using api_enbaled_user authorization with the supplied authorization credentials. """
        auth = (client_id, client_secret)
        r = requests.post(self.token_url, auth=auth, json={'grant_type': 'client_credentials', 'scope': self.scope}, headers={'Content-Type': 'application/json'})
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
        r = requests.get(url, headers={'Authorization': f'Bearer {self.token}'}, params=params)
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

class ChurchsuiteApp(Churchsuite):
    def __init__(self):
        """ Create ChurchSuite instance that will hold an access token once authorized. """
        self.raw = None
        # Import this here to prevent Flask needing to be installed if only using standard Churchsuite() not ChurchsuiteApp()
        import flask
        self.flask = flask

    def test_manual_authorization(self, client_id, client_secret=None, redirect_uri=None, state=None):
        """ Fetch access token using oauth_app authorization with the supplied authorization credentials.
            This is a test function to simulate what occurs with authorize_app_stage{1,2}()
        """
        oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=[self.scope], pkce='S256')
        authorization_url, state = oauth.authorization_url(self.auth_url, state=state)
        code_verifier = oauth._code_verifier  # fetch from private field as requests-oauthlib does not yet support a public access method
        # In a web app, you would save state for later: session['oauth_state'] = state
        # Simulate callback into Python here by making the user paste in the URL that came back to the browser from to the redirect_url
        print(f"Please go to {authorization_url} and authorize access.")
        authorization_response_url = input('Enter the full callback URL: ')
        # Check that request.args.get('state') != session.pop('oauth_state'); otherwise bomb out with error 400
        # code_verifier = session.pop('code_verifier')
        oauth = OAuth2Session(client_id, redirect_uri=redirect_uri)
        oauth._code_verifier = code_verifier  # store into a private field as requests-oauthlib does not yet support a public access method
        json = oauth.fetch_token(self.token_url, authorization_response=authorization_response_url, code_verifier=code_verifier)
        self.token = json.get('access_token')

if __name__ == "__main__":
    import secret_app
    cs = ChurchsuiteApp()
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' # allow debug using insecure http://localhost
    cs.test_manual_authorization(secret_app.client_id, secret_app.client_secret, redirect_uri='http://localhost:8080/callback')
    print(f"\nSuccessful authorization! Token={cs.token}")
