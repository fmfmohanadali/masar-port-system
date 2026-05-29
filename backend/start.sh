#!/usr/bin/env bash
set -o errexit
cd backend

echo "🔄 Running migrations..."
python manage.py migrate --noinput

echo "📦 Seeding data..."
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
admin_profile.role = 'port_admin'
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
    ('بوابة الدخول', 'ENTRY_GATE'),
    ('الرصيف', 'BERTH'),
    ('منطقة الجمارك', 'CUSTOMS_ZONE'),
    ('بوابة الخروج', 'EXIT_GATE'),
    ('التسليم', 'DELIVERY'),
]
for name, pt in points:
    ScanPoint.objects.get_or_create(name=name, point_type=pt, defaults={'is_active': True})

# Booking Slots
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
    for d in range(30):
        cur = today + timedelta(days=d)
        rule = WEEKDAY_RULES.get(cur.weekday(), {'hours': [], 'capacity': 0})
        for h in rule['hours']:
            BookingSlot.objects.get_or_create(
                date=cur, hour=h,
                defaults={'capacity': rule['capacity'], 'is_closed': False}
            )
    print('Booking slots created')
else:
    print('Booking slots already exist, skipping')
"

echo "🚀 Starting server..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
