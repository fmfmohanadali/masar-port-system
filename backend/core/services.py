from django.contrib.auth.models import User
from django.core import signing
from django.db.models import Avg, F, ExpressionWrapper, DurationField
from django.utils import timezone
from datetime import datetime
from .models import (
    UserProfile, Company, Driver, Truck, Container, BookingSlot,
    Trip, ScanPoint, ScanEvent, Notification, AuditLog
)

STATUS_MAP = {
    'ENTRY_GATE': 'ENTERED_PORT',
    'BERTH': 'AT_BERTH',
    'CUSTOMS_ZONE': 'PASSED_CUSTOMS',
    'EXIT_GATE': 'EXITED_PORT',
    'DELIVERY': 'DELIVERED',
}


def audit(user, action, model_name, object_id=None, details=''):
    AuditLog.objects.create(user=user, action=action, model_name=model_name, object_id=str(object_id or ''), details=details)


def create_notification(user, title, message):
    return Notification.objects.create(user=user, title=title, message=message)


def get_or_create_slot(slot_dt):
    slot_date = slot_dt.date()
    slot_hour = slot_dt.hour
    slot, _ = BookingSlot.objects.get_or_create(date=slot_date, hour=slot_hour)
    slot.recalculate_capacity()
    slot.save()
    return slot


def quick_create_trip(*, broker_user, data):
    carrier, _ = Company.objects.get_or_create(name=data['carrier_company_name'], defaults={'company_type': 'carrier'})
    driver, _ = Driver.objects.get_or_create(full_name=data['driver_name'], phone=data['driver_phone'])
    truck, _ = Truck.objects.get_or_create(plate_number=data['truck_plate'], defaults={'owner_company': carrier})
    container, _ = Container.objects.get_or_create(
        container_no=data['container_no'],
        defaults={'destination': data['destination'], 'customs_status': 'released'}
    )
    if container.destination != data['destination']:
        container.destination = data['destination']
        container.save(update_fields=['destination', 'updated_at'])
    slot = get_or_create_slot(data['slot_datetime'])
    if slot.is_closed:
        raise ValueError('الفترة الزمنية مغلقة وممتلئة حالياً')

    trip = Trip.objects.create(
        broker=broker_user,
        carrier_company=carrier,
        truck=truck,
        driver=driver,
        container=container,
        slot=slot,
        destination=data['destination'],
        status='BOOKED',
        notes=data.get('notes', ''),
    )
    create_notification(broker_user, 'تم إنشاء الرحلة', f'تم إنشاء الرحلة {trip.trip_code}')
    audit(broker_user, 'CREATE', 'Trip', trip.trip_code, f'Quick create for container {container.container_no}')
    return trip


def verify_trip_token(token):
    return signing.loads(token, salt='masar-trip', max_age=60 * 60 * 24 * 30)


def scan_trip(*, token, point_type, user, note=''):
    payload = verify_trip_token(token)
    trip = Trip.objects.get(trip_code=payload['trip_id'])
    point = ScanPoint.objects.get(point_type=point_type)
    event = ScanEvent.objects.create(trip=trip, scan_point=point, scanned_by=user, note=note)
    new_status = STATUS_MAP.get(point_type)
    if new_status:
        trip.status = new_status
        trip.save(update_fields=['status', 'updated_at'])
    create_notification(trip.broker, 'تحديث رحلة', f'الرحلة {trip.trip_code} أصبحت {trip.status}')
    audit(user, 'SCAN', 'Trip', trip.trip_code, f'{point_type} - {note}')
    return trip, event


def dashboard_summary_for(user):
    role = getattr(getattr(user, 'profile', None), 'role', 'broker')
    qs = Trip.objects.all()
    if role == 'broker':
        qs = qs.filter(broker=user)
    data = {
        'total_trips': qs.count(),
        'waiting_trips': qs.filter(status__in=['CREATED', 'BOOKED', 'APPROVED']).count(),
        'inside_port': qs.filter(status__in=['ENTERED_PORT', 'AT_BERTH', 'PASSED_CUSTOMS', 'IN_TRANSIT']).count(),
        'delivered': qs.filter(status='DELIVERED').count(),
        'recent_trips': qs.select_related('container', 'truck', 'driver', 'slot', 'carrier_company', 'broker')[:10],
    }
    return data


def turnaround_report_for(user):
    role = getattr(getattr(user, 'profile', None), 'role', 'broker')
    qs = Trip.objects.all()
    if role == 'broker':
        qs = qs.filter(broker=user)

    report = []
    for trip in qs.select_related('container', 'truck', 'driver'):
        events = {e.scan_point.point_type: e.scanned_at for e in trip.scan_events.select_related('scan_point').all()}
        if 'ENTRY_GATE' in events and 'EXIT_GATE' in events:
            delta = events['EXIT_GATE'] - events['ENTRY_GATE']
            minutes = int(delta.total_seconds() // 60)
        else:
            minutes = None
        report.append({
            'trip_code': str(trip.trip_code),
            'container_no': trip.container.container_no,
            'truck_plate': trip.truck.plate_number,
            'status': trip.status,
            'turnaround_minutes': minutes,
        })
    return report
