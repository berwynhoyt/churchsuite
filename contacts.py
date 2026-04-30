#!/usr/bin/env python3

import churchsuite
import secrets

cs = churchsuite.Churchsuite(auth=(secrets.CLIENT_ID, secrets.CLIENT_SECRET))
people = cs.get(churchsuite.URL.contacts, per_page=100, status='active')
for p in people:
	print(f"{p.first_name} {p.last_name}: {p.email}")
