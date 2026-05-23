#!/bin/bash

uv run manage.py migrate
exec uv run gunicorn --bind :8000 --workers 2 djangolondon.wsgi
