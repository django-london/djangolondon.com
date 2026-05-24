#!/bin/bash

uv run manage.py migrate

GUNICORN="uv run gunicorn --bind :8000 --workers 2 djangolondon.wsgi"

if [ -n "$BUCKET_NAME" ]; then
  exec litestream replicate -config /etc/litestream.yml -exec "$GUNICORN"
else
  exec $GUNICORN
fi
