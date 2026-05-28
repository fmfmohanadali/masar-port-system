#!/usr/bin/env bash

cd backend

for i in {1..40}; do
    echo "⏳ Attempt $i/40: checking database..."
    if python manage.py showmigrations >/dev/null 2>&1; then
        echo "✅ Database is ready!"
        echo "⏱️ Waiting 10s for connection to stabilize..."
        sleep 10
        break
    fi
    echo "   Database not ready, waiting 5s..."
    sleep 5
done

echo "🔄 Running migrations..."
python manage.py migrate --noinput || echo "⚠️ Migrate failed, continuing anyway..."

echo "🚀 Starting server..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
