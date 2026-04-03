# Docx Export for ChurchSuite and Python Scripting for API v2

This repository contains two things:

1. A Python library `churchsuite.py` to conveniently access to the ChurchSuite API v2.
2. [Docx Export](#docx-export-of-service-plans), a Python script `serviceplan.py` that uses the library to export the coming week's service plans as MS Word `docx` files.

## Quickstart

Install python >= 3.12 and set up a venv. Google for instructions.

Clone this repository and download Python prerequisites as follows:

```bash
git clone https://github.com/berwynhoyt/churchsuite.git
cd churchsuite
pip install -r requirements.txt
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

If you supply a third parameter when you call `churchsuite.Churchsuite(client_id, client_secret, request_url)`, it will automatically use `oauth_app` authorization instead of `api_enabled_user` authorization. You can use this to give for web app users access to their Churchsuite data. (First you need to set up an app in ChurchSuite: `ProfileIcon -> Settings -> OAuth Apps`.)

## Docx Export of Service Plans

This exports the coming week's service plans to separate docx files. This allows service leaders to more easily highlight or add their own notes than they could with the pdf. It is also a much clearer format for service leaders to find their place on the page.

It works as follows:

- It automatically highlights in red any responsive text that comes after "all:", "everyone:", "together:", or "people:"
- It stops red text when it gets to a double-new-line or when it gets to a "Leader:" line.
- It emboldens "Leader:", "Minister, or "Reader:"
- "Song", "Hymn" and "Psalm" headings are displayed in green along with the song title.
- Level-2 section headings are omitted if they contain no text.

To use it, do the setup as in the Quickstart above, then run `python serviceplan.py` and it will save one `docx` file for each service plan in the  coming week.

### Cloud app version

Instead of the command-line version above, if you wish to run `serviceplan.py` as a web app on Google App Engine, follow these instructions:

1. Create a project using the [Google Cloud console](https://console.cloud.google.com/). It requires a project. Call it `<yourchurch>-serviceplans` (or similar).
2. Follow instructions to [Create a Google Cloud project](https://docs.cloud.google.com/appengine/docs/standard/python3/building-app/creating-gcp-project). This is complicated, but hopefully you'll get there. I can't help you with it. It will make you create a Google billing account and will take your credit card but it won't actually bill you anything as typical usage of docx fits well within the free tier.
3. Note: you can test the app on your localhost by running `python serviceplan.py --app` and then browsing to `localhost:8080`.
4. Deploy the app to your Google Cloud project by browsing to [Google Cloud Shell](https://shell.cloud.google.com/) and then typing the following:

```sh
git clone https://github.com/berwynhoyt/churchsuite.git
cd churchsuite
gcloud config set project <yourchurch>-serviceplans  # use the project name you selected in point 1 above
gcloud deploy app
```

Now the app will be on the URL the command above supplies; typically https://<your-church>-serviceplans.ts.r.appspot.com/, depending on what you called your project.
