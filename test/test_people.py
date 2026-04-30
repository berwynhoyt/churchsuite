import churchsuite
import config

cs = churchsuite.Churchsuite(auth=[config.USER_CLIENT_ID, config.USER_CLIENT_SECRET])
people = cs.get(f'{churchsuite.api}/addressbook/contacts', per_page=100, status='active')
for p in people:
	print(f"{p.first_name} {p.last_name}: {p.email}")
