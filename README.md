# [djangolondon.com](https://djangolondon.com)

Setup:

**(1)** Install [uv](https://docs.astral.sh/uv/)

**(2)** Run migrations:

```bash
DEBUG=1 uv run manage.py migrate
```

**(3)** Start the server:

```bash
DEBUG=1 uv run manage.py runserver
```

Visit `/organizers/` to log in.
In debug mode, the migration process automatically creates a superuser with these credentials:

```
username: admin
password: thames
```
