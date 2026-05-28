#!/usr/bin/env bash
set -o errexit

cd backend

echo "⏳ Waiting for database..."
for i in {1..20}; do
    if python manage.py showmigrations >/dev/null 2>&1; then
        echo "✅ Database ready!"
        break
    fi
    echo "   Attempt $i/20 failed, retrying in 3s..."
    sleep 3
done

echo "🔄 Running migrations..."
python manage.py migrate --noinput

echo "🚀 Starting server..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
