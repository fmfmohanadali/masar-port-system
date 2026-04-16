from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.authtoken.models import Token
from core.models import UserProfile, Company, Driver, Truck, Container, BookingSlot, Trip, ScanPoint


class Command(BaseCommand):
    help = 'Creates demo users, scan points, slots and sample trips'

    def handle(self, *args, **options):
        default_password = 'Admin@12345'

        users = [
            ('admin', 'ops', True),
            ('broker1', 'broker', False),
            ('guard1', 'gate_guard', False),
            ('portadmin1', 'port_admin', False),
        ]

        created_users = []
        for username, role, is_staff in users:
            user, created = User.objects.get_or_create(username=username, defaults={
                'is_staff': is_staff,
                'is_superuser': is_staff,
                'email': f'{username}@masar.local',
                'first_name': username,
            })
            if created:
                user.set_password(default_password)
                user.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.save()
            Token.objects.get_or_create(user=user)
            created_users.append(user)

        carrier, _ = Company.objects.get_or_create(name='شركة الأمان للنقل', defaults={'company_type': 'carrier'})

        points = [
            ('بوابة الدخول', 'ENTRY_GATE'),
            ('الرصيف', 'BERTH'),
            ('منطقة الجمارك', 'CUSTOMS_ZONE'),
            ('بوابة الخروج', 'EXIT_GATE'),
            ('التسليم', 'DELIVERY'),
        ]
        for name, point_type in points:
            ScanPoint.objects.get_or_create(point_type=point_type, defaults={'name': name, 'is_active': True})

        today = timezone.localdate()
        current_hour = timezone.localtime().hour
        for h in range(current_hour, min(current_hour + 8, 24)):
            slot, _ = BookingSlot.objects.get_or_create(date=today, hour=h)
            slot.recalculate_capacity()
            slot.save()

        broker = User.objects.get(username='broker1')
        driver, _ = Driver.objects.get_or_create(full_name='أحمد علي', phone='777000111')
        truck, _ = Truck.objects.get_or_create(plate_number='ADN-1001', defaults={'owner_company': carrier})
        container, _ = Container.objects.get_or_create(container_no='MSKU1234567', defaults={'destination': 'صنعاء'})
        slot = BookingSlot.objects.filter(date=today).order_by('hour').first()
        if slot and not Trip.objects.filter(container=container).exists():
            Trip.objects.create(
                broker=broker,
                carrier_company=carrier,
                truck=truck,
                driver=driver,
                container=container,
                slot=slot,
                destination='صنعاء',
                status='BOOKED',
                notes='رحلة تجريبية 1'
            )

        driver2, _ = Driver.objects.get_or_create(full_name='خالد سعيد', phone='777222333')
        truck2, _ = Truck.objects.get_or_create(plate_number='ADN-1002', defaults={'owner_company': carrier})
        container2, _ = Container.objects.get_or_create(container_no='TGHU8899001', defaults={'destination': 'تعز'})
        slot2 = BookingSlot.objects.filter(date=today).order_by('hour')[1:2].first() or slot
        if slot2 and not Trip.objects.filter(container=container2).exists():
            Trip.objects.create(
                broker=broker,
                carrier_company=carrier,
                truck=truck2,
                driver=driver2,
                container=container2,
                slot=slot2,
                destination='تعز',
                status='APPROVED',
                notes='رحلة تجريبية 2'
            )

        self.stdout.write(self.style.SUCCESS('Demo data seeded successfully.'))
        self.stdout.write(self.style.WARNING(f'admin / {default_password}'))
        self.stdout.write(self.style.WARNING(f'broker1 / {default_password}'))
