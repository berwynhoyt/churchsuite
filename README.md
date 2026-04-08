# Docx Export for ChurchSuite and Python Scripting for API v2

This repository contains three things:

1. [Docx Export Web App](https://serviceplans.ts.r.appspot.com/) that exports that exports the coming week's service plans as MS Word `docx` files.
2. [Docx Export](#docx-export-of-service-plans), a command-line Python script `serviceplan.py` that exports the coming week's service plans as MS Word `docx` files.
3. A Python library `churchsuite.py` to conveniently access to the ChurchSuite API v2. (This library is used by Docx Export.)

## Quickstart

### Docx Export Web App

To export your church service plans as Docx files, browse to this [live site](https://serviceplans.ts.r.appspot.com/). I'm afraid it won't work for you at this point because you don't have your client_id and client_secret in a Google Secrets database. I'm still working out the best way to do this for guest users without having to store all your ChurchSuite app secrets in my database, which seems dodgy.

But if I can get around that, then all you have to do is setting up an app in ChurchSuite at `ProfileIcon -> Settings -> OAuth Apps`, and  set its "Redirect URI" to `https://serviceplans.ts.r.appspot.com/callback`.

### Python library CLI script

Install python >= 3.12 and set up a venv. Google for instructions.

Clone this repository and download Python prerequisites as follows:

```bash
git clone https://github.com/berwynhoyt/churchsuite.git
cd churchsuite
pip install -r requirements-base.txt
```

Second, [get your ChurchSuite API keys](https://developer.churchsuite.com/auth) and use them to create a file called `secret.py` as follows:

```python
# Client secrets for Churchsuite authentication
CLIENT_ID = "your-client-id"
CLIENT_SECRET = "your-client-secret"
```

Now you are ready to run either the [Docx Export](#docx-export-of-service-plans) applet below or create your own ChurchSuite app in Python as follows.

### Create your own ChurchSuite Python app

Third, create a Python program like the following `contacts.py` which prints the names of the first 100 active contacts from your ChurchSuite database:

```python
#!/usr/bin/env python3

import churchsuite
import secret

db = churchsuite.Churchsuite(secret.CLIENT_ID, secret.CLIENT_SECRET)
people = db.get(churchsuite.URL.contacts, per_page=100, status='active')
for p in people:
	print(f"{p.first_name} {p.last_name}: {p.email}")
```

Then run `python contacts.py`.

### OAuth_app Authorization

If you supply a third `redirect_url` parameter when you call `churchsuite.Churchsuite(client_id, client_secret, redirect_url)`, it will automatically use `oauth_app` authorization instead of `api_enabled_user` authorization. This is used if you have designed a churchsuite app and deployed it on Google App Engine or a similar cloud platform. You can use `oauth_app` to give your web app users access to their Churchsuite data. To set this up:

1. Get your app client_id and client_secret by setting up an app in ChurchSuite: `ProfileIcon -> Settings -> OAuth Apps`.
2. Invoke `churchsuite.Churchsuite` giving it a `redirect_url` that points to your app's url that is ready to receive a ChurchSuite access token.

An example [cloud app setup](#cloud-app-setup) for Docx Export is given below.

## Docx Export of Service Plans

This exports the coming week's service plans to separate docx files. This allows service leaders to more easily highlight or add their own notes than they could with the pdf. It is also a much clearer format for service leaders to find their place on the page.

It works as follows:

- It automatically highlights in red any responsive text that comes after "all:", "everyone:", "together:", or "people:"
- It stops red text when it gets to a double-new-line or when it gets to a "Leader:" line.
- It emboldens "Leader:", "Minister, or "Reader:"
- "Song", "Hymn" and "Psalm" headings are displayed in green along with the song title.
- Level-2 section headings are omitted if they contain no text.

To use it as a command-line interface, do the setup as in the Quickstart above, then run `python serviceplan.py` and it will save one `docx` file for each service plan in the coming week.

If you don't like the command-line, to set up your own cloud app in Google App Engine as follows.

### Cloud app setup -- using Google App Engine (GAE)

This section explains creating your own web app for your ChurchSuite users. It uses the example of the Docx Export app which lets users download service plans simply by browsing to a bookmarked web page. Instead of the command-line version above, you will need to run `serviceplan_app.py` as a web app on Google App Engine as follows:

1. Follow instructions to [Create a Google Cloud project](https://docs.cloud.google.com/appengine/docs/standard/python3/building-app/creating-gcp-project). Call the project `<yourchurch>-serviceplans` (or something similar; called **[PROJECT_ID]** below). This is complicated, but hopefully you'll get there. I can't help you with it. It will make you create a Google billing account and will take your credit card but it won't actually bill you anything as typical usage of docx fits well within the free tier.
3. Note: you can test the app on your localhost by running `python serviceplan_app.py` and then browsing to `localhost:8080`.
4. Deploy the app to your Google Cloud project by browsing to [Google Cloud Shell](https://shell.cloud.google.com/) and then typing the following:

```sh
git clone https://github.com/berwynhoyt/churchsuite.git
cd churchsuite
gcloud config set project [PROJECT_ID]  # use the project name you selected in point 1 above
gcloud app deploy
```

Now the app will be running on the APP_URL that the command above supplies, typically: `https://[PROJECT_ID].ts.r.appspot.com/`

Finally, your app will not work until you store your app secrets in Google's Secret Manager:

1. Get your oauth_app `client_id` and `client_secret` by add your app to ChurchSuite: `ProfileIcon -> Settings -> OAuth Apps`. In the "Redirect URI" field, enter your APP_URL/token, e.g.: `https://[PROJECT_ID].ts.r.appspot.com/authorized`

2. Go to [Google Cloud Console](https://console.cloud.google.com/welcome?project=serviceplans-492207).

3. Make sure the name of your Google [PROJECT_ID] is selected in the top-left corner beside Google Cloud.

4. Type "Secret Manager" into the Google Cloud search bar and click it. Enable Secret Manager if necessary.

5. Click "+ Create Secret" for each of  `client_id` and `client_secret` that you got from ChurchSuite above. You only need to enter the name and value of each secret and leave the rest of the settings untouched. Click "Create secret" at the bottom.

6. Add permission for your Google Cloud project to access your secrets `client_id` and `client_secret` by typing the following into your Google Cloud Console:

   ```sh
   gcloud secrets add-iam-policy-binding client_id \
       --member="serviceAccount:[PROJECT_ID]@appspot.gserviceaccount.com" \
       --role="roles/secretmanager.secretAccessor"
   gcloud secrets add-iam-policy-binding client_secret \
       --member="serviceAccount:[PROJECT_ID]@appspot.gserviceaccount.com" \
       --role="roles/secretmanager.secretAccessor"
   ```

#### Testing the cloud app locally

If you want to test the cloud app locally, create a secret_app.py file containing `client_id` and `client_secret` from your app setup on ChurchSuite. Then run the server locally:

```sh
python serviceplan_app.py
```

You will have to set up a new app on ChurchSuite (see point 1 above), or edit your current app to point the "Redirect URI" to `localhost:8080`. Now you can browse to the app at `localhost:8080` to run the app.

Instead of using a local `secret_app.py`, if you want to test use of the Google Secrets Manager locally, you need to get a json key file:

1. Go to  [Google Cloud Console](https://console.cloud.google.com/welcome?project=serviceplans-492207), find `IAM & Admin > Service Accounts`

2. Select the service account for your [Project_ID], go to the **Keys** tab, and add a key of type `json` which will download a json file. Save the json file in a secure location on your computer.

3. Now create two environment variables and run the app locally:

   ```sh
   export GOOGLE_CLOUD_PROJECT=[PROJECT_ID]
   export GOOGLE_APPLICATION_CREDENTIALS=[path_to_your_json_file]
   python serviceplan_app.py`
   ```

