# [djangolondon.com](https://djangolondon.com)

The website for Django London, the monthly meetup for Django enthusiasts in London, established 2012.

## Development setup

**(1)** Install [uv](https://docs.astral.sh/uv/)

**(2)** Run migrations:

```bash
DEBUG=1 manage.py migrate
```

**(3)** Start the server:

```bash
DEBUG=1 manage.py runserver
```

Visit `/organizers-admin/` to log in.
In debug mode, the migration process automatically creates a superuser with these credentials:

```
username: admin
password: thames
```

## Prize draws

To run a prize draw at a meetup:

**(1)** Add a prize draw in the admin, at `/organizers-admin/djangolondon/prizedraw/`.
Add one row per prize, in the order you want to give them away, attaching each
prize’s voucher PDF.

**(2)** Put `/prize-draws/<slug>/screen/` up on the projector.
It shows a QR code for the entry page and a live entry count.

**(3)** Attendees scan the QR code, enter their name, and wait.

**(4)** Press the big draw button, once per prize.
Each press picks a random entrant who has not already won, announces them on
the screen, and records the win in the database.
Entries close on the first press.

**(5)** Winners see their win on their own phone, and can download their
voucher PDF there and then.

Uploaded vouchers are stored in the database, so they need no disk of their own
and are covered by the same backups. They are only downloadable by the winner.
