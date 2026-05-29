#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
cd backend
python manage.py collectstatic --noinput
# NOTE: migrate runs in start.sh, NOT here
# because Render DB may not be available during build
