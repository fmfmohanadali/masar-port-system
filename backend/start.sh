#!/usr/bin/env bash

cd backend

echo "🔄 Running migrations..."
python manage.py migrate --noinput

echo "📦 Seeding data (if needed)..."
python manage.py shell -c "
from datetime import date, timedelta
from django.contrib.auth.models import User
from core.models import UserProfile, BookingSlot, ScanPoint

# Users
admin, _ = User.objects.get_or_create(username='admin1', defaults={'email': 'admin@example.com'})
admin.is_staff = True
admin.is_superuser = True
admin.set_password('Admin@12345')
admin.save()
admin_profile, _ = UserProfile.objects.get_or_create(user=admin)
admin_profile.role = 'admin'
admin_profile.save()

ops, _ = User.objects.get_or_create(username='ops1', defaults={'email': 'ops@example.com'})
ops.is_staff = True
ops.is_superuser = False
ops.set_password('Ops@12345')
ops.save()
ops_profile, _ = UserProfile.objects.get_or_create(user=ops)
ops_profile.role = 'ops'
ops_profile.save()

# Scan Points
points = [
    ('بوابة الدخول', 'ENTRY'),
    ('رصيف التحميل 1', 'BERTH_1'),
    ('رصيف التحميل 2', 'BERTH_2'),
    ('الجمارك', 'CUSTOMS'),
    ('بوابة الخروج', 'EXIT'),
]
for name, pt in points:
    ScanPoint.objects.get_or_create(name=name, point_type=pt, defaults={'is_active': True})

# Booking Slots — فقط إذا لم تكن موجودة!
if not BookingSlot.objects.filter(date__gte=date.today()).exists():
    WEEKDAY_RULES = {
        0: {'hours': [8,9,10,11,12,13,14,15], 'capacity': 30},
        1: {'hours': [8,9,10,11,12,13,14,15], 'capacity': 30},
        2: {'hours': [8,9,10,11,12,13,14,15], 'capacity': 30},
        3: {'hours': [8,9,10,11,12], 'capacity': 20},
        4: {'hours': [], 'capacity': 0},
        5: {'hours': [9,10,11,12,13], 'capacity': 15},
        6: {'hours': [8,9,10,11,12,13,14], 'capacity': 25},
    }
    today = date.today()
    fields = {f.name for f in BookingSlot._meta.fields}
    for d in range(30):
        cur = today + timedelta(days=d)
        rule = WEEKDAY_RULES.get(cur.weekday(), {'hours': [], 'capacity': 0})
        for h in rule['hours']:
            cap = rule['capacity']
            defaults = {}
            if 'capacity' in fields: defaults['capacity'] = cap
            if 'max_capacity' in fields: defaults['max_capacity'] = cap
            if 'limit' in fields: defaults['limit'] = cap
            if 'is_closed' in fields: defaults['is_closed'] = False
            if 'is_active' in fields: defaults['is_active'] = True
            BookingSlot.objects.get_or_create(date=cur, hour=h, defaults=defaults)
    print('Booking slots created')
else:
    print('Booking slots already exist, skipping')
"

echo "🚀 Starting server..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
