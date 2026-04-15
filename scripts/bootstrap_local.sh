#!/usr/bin/env bash
set -e
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env || true
cd backend
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
