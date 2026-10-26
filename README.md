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

## Quizzes

Past quizzes are listed at `/quizzes/`, where anyone can play them on their own.

To run a live quiz at a meetup:

**(1)** Add a quiz in the admin, at `/organizers-admin/djangolondon/quiz/`, with
its multiple choice questions. Leave it unpublished, so nobody can see the
answers early.

**(2)** Put `/quizzes/<slug>/screen/` up on the projector.
It shows a QR code for the play page and the players who have joined.

**(3)** Attendees scan the QR code, enter their name, and wait.

**(4)** Press the big button to step through the quiz:

* Each question, which players answer on their phones. They can change their
  minds until you move on. The screen shows who is in the lead and who is
  behind, on the questions so far.
* Each answer, highlighted, with how many people chose each option.
* The results: the names of everyone with a perfect score, then the next score
  down, and so on, until you stop.

Use the back button if you press on too soon, and “Start over” to clear out
the players and run the quiz again.

**(5)** Afterwards, publish the quiz to list it at `/quizzes/`.

Past quizzes are imported from `data/quizzes/`, one TOML file each, and are
refreshed from those files on every deploy, so edit them there rather than in
the admin.
