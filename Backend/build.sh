#!/usr/bin/env bash
# Runs on Render every time the backend is deployed.
set -o errexit  # stop at the first error

pip install -r requirements-prod.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Creates your admin login the first time. Skipped when the variables are not set,
# and harmless on later deploys (the account already exists).
if [[ -n "${DJANGO_SUPERUSER_USERNAME:-}" && -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]]; then
  python manage.py createsuperuser --no-input || true
fi