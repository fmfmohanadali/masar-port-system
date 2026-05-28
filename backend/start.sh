#!/usr/bin/env bash

cd backend

# انتظار أولي 3 دقائق — قاعدة البيانات Free Tier تحتاج وقت
echo "⏳ Waiting 3 minutes for Free Tier database to wake up..."
sleep 180

for i in {1..30}; do
    echo "⏳ Attempt $i/30: checking database..."
    if python manage.py showmigrations >/dev/null 2>&1; then
        echo "✅ Database is ready!"
        sleep 15
        break
    fi
    echo "   Database not ready, waiting 10s..."
    sleep 10
done

echo "🔄 Running migrations..."
python manage.py migrate --noinput

echo "🚀 Starting server..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
