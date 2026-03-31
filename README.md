# Docx Export for ChurchSuite and Python Scripting for API v2

This repository contains two things:

1. A Python library `churchsuite.py` to conveniently access to the ChurchSuite API v2.
2. A Python script `plan.py` that uses the library to export the coming week's service plans as MS Word `docx` files.

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

## Docx Export

This exports the coming week's service plans to separate docx files. This allows service leaders to more easily highlight or add their own notes than they could with the pdf. It is also a much clearer format for service leaders to find their place on the page.

It works as follows:

- It automatically highlights in red any responsive text that comes after "all:", "everyone:", "together:", or "people:"
- It stops red text when it gets to a double-new-line or when it gets to a "Leader:" line.
- It emboldens "Leader:", "Minister, or "Reader:"

To use it, do the setup as in the Quickstart above, then run `python plan.py` and it will save one `docx` file for each service plan.
