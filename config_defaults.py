# Python config file for a ChurchSuite Flask app
# You can override these in config.py (not version-controlled).

# This can be left empty if you wish to create an app for the public. Then the app will automatically ask the user for their church's
# Client Identifier and when they enter it, will give them a URL to bookmark that already incorporates their church's identifier.
# They can then share this bookmark with all their ChurchSuite users without them having to enter client_id each time.
# If you don't like this functionality, simply supply a valid OAUTH_CLIENT_ID here or to ChurchSuiteApp().
# You get your client_id from ChurchSuite. Configure a public 'app in': ChurchSuite -> User Menu -> Settings -> OAuth Apps
# No need to supply a CLIENT_SECRET as well as CLIENT_ID if you set the app as public in ChurchSuite (preferred)
# (don't worry, this does not make your ChurchSuite login details 'public' -- all public apps are still protected by a user login).
OAUTH_CLIENT_ID = ''  # Leave empty ('') to use the 'client_id' field given in the URL parameters of the query that required login

# Client secrets if you use specific user authentication as a particular API_enabled user (for Churchsuite class rather than ChurchsuiteApp).
# Especially useful if you are running python churchsuite script on your local computer rather than as a web app.
# These should probably not be stored on a public server like GAE. If you need to supply user credentials, put them in Google Secret Manager.
USER_CLIENT_ID = None
USER_CLIENT_SECRET = None

# This makes Flask sign cookies to ensure no middle-man hack has altered our cookies.
# To make your server preserve the session between restarts, set this to a constant, different for each server.
# But if your server is using the default RAM storage session (not a database), this may not help much.
import secrets
SECRET_KEY = secrets.token_hex()

# send session data only over secure https (set to false for localhost debugging only)
SESSION_COOKIE_SECURE = True
