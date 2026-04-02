#!/usr/bin/env python3
""" Library to access ChurchSuite data conveniently """

import requests
import json
import os.path
import logging
import pprint

from types import SimpleNamespace

from requests_oauthlib import OAuth2Session

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

class Churchsuite:
    def __init__(self, client_id, client_secret, *, redirect_url=None, raw=None):
        """ Create ChurchSuite database 'connection' instance and get access token using the supplied authorisation details.
            If redirect_url is supplied, it will use oauth_app authorization; otherwise it will use api_enabled_user authorization.
            If filename raw is supplied, store all json text received from the server into that file.
        """
        self.token = self.authorize(client_id, client_secret, redirect_url)
        self.raw = raw
        if raw is not None:
            # truncate file
            open(raw, 'w').close()

    def append_raw(self, text):
        if self.raw is not None:
            with open(self.raw, 'a') as f:
                f.write(text)

    @staticmethod
    def authorize(client_id, client_secret, redirect_url=None):
        """ Return access token using the supplied authorisation details.
            If redirect_url is supplied, it will use oauth_app authorization; otherwise it will use api_enabled_user authorization.
        """
        token_url = "https://login.churchsuite.com/oauth2/token"
        auth_url = "https://login.churchsuite.com/oauth2/authorize"
        scope = ['full_access']

        # If using api_enabled_user authorization
        if redirect_url is None:
            auth = (client_id, client_secret)
            r = requests.post(token_url, auth=auth, json={'grant_type': 'client_credentials', 'scope': scope[0]}, headers={'Content-Type': 'application/json'})
            r.raise_for_status()
            return r.json().get('access_token')

        # Otherwise try oauth_app authorization
        oauth = OAuth2Session(client_id, redirect_uri=redirect_url, scope=scope)
        authorization_url, state = oauth.authorization_url(auth_url)
        print(f"Please go to {authorization_url} and authorize access.")
        authorization_response = input('Enter the full callback URL: ')
        json = oauth.fetch_token(token_url, authorization_response=authorization_response, client_secret=client_secret)
        return json.get('access_token')

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
        logging.debug(f"request: {dump_request(r.request).replace('\n', '\n|  ')}")
        r.raise_for_status()
        self.append_raw(json.dumps(r.json(), indent=4) + '\n')
        # Convert json dict to SimpleNamespace (recursively for sub-objects)
        object = json.loads(r.text, object_hook=lambda d: SimpleNamespace(**d))
        formatted_response = f"GET {url} =>\n| {pprint.pformat(object).replace('\n', '\n| ')}"
        logging.info(formatted_response)
        if not hasattr(object, 'data'):
            raise Exception("No 'data' field found in response to {formatted_response}")
        return object.data
