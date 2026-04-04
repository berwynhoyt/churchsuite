#!/usr/bin/env python3
""" Run a web app on port $PORT (default 8080) to fetch the upcoming service plans from ChurchSuite and export into docx format """

import os
import sys
import logging

from flask import Flask
from google.cloud import secretmanager
import serviceplan

def get_secret(project_id, secret_id, version_id="latest"):
    """ Access the payload for the given secret_id; version_id can be "latest" or a specific number """
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

app = Flask(__name__)

@app.route("/")
def hello_world():
    """ Example Hello World route. """
    name = os.environ.get("NAME", "World")
    return f"Hello {name}! PROJECT_ID={os.environ.get('GOOGLE_CLOUD_PROJECT')}"

@app.route("/secret")
def secret():
    """ Return secret """
    return get_secret(os.environ.get('GOOGLE_CLOUD_PROJECT'), 'secret_id')

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=f'%(levelname)s: %(message)s')

    if os.getenv('GAE_ENV'):
        # For google app engine, get secrets from Google Secret Manager
        pass
    else:
        import secret
        client_id, client_secret = secret.CLIENT_ID_app, secret.CLIENT_SECRET_app

    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
