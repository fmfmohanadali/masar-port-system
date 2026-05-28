#!/usr/bin/env bash

cd backend

for i in {1..30}; do
    echo "⏳ Attempt $i/30: checking database..."
    if python manage.py showmigrations >/dev/null 2>&1; then
        echo "✅ Database is ready!"
        break
    fi
    echo "   Database not ready, waiting 5s..."
    sleep 5
done

echo "🔄 Running migrations..."
python manage.py migrate --noinput

echo "🚀 Starting server..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
