#!/bin/sh
# Runs before every container start (docs/DEPLOYMENT.md Decision 10), so the
# manual deploy runbook stays a single command — migrations and static files
# are never a separate step to remember.
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
