# Python Scripting for ChurchSuite API v2

This repository contains a Python library `churchsuite.py` to conveniently access to the ChurchSuite API v2. It also contains a Python script `plan.py` that uses the library to fetch the coming week's service plans and exports them to MS Word `docx` documents.

## Quickstart

First clone this repository and download python prerequisites:

```bash
git clone https://github.com/berwynhoyt/churchsuite.git
cd churchsuite
pip install -r requirements.txt
```

Second, [get your ChurchSuite API keys](https://developer.churchsuite.com/auth) and use them to create a file called `secrets.py` as follows:

```python
# Client secrets for Churchsuite authentication
CLIENT_ID = "your-client-id"
CLIENT_SECRET = "your-client-secret"
```

Third, create a Python program like the following `contacts.py` which prints the names of the first 100 active contacts from your ChurchSuite database:

```python
#!/usr/bin/env python3

import churchsuite
import secrets

db = churchsuite.Churchsuite(auth=(secrets.CLIENT_ID, secrets.CLIENT_SECRET))
people = db.get(churchsuite.URL.contacts, per_page=100, status='active')
for p in people:
	print(f"{p.first_name} {p.last_name}: {p.email}")
```

Then run `python contacts.py`.

## Export service plans to docx

Setup as in the Quickstart above, then run `python plan.py` and it will save one `docx` file for each service plan.
