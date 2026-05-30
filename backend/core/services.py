import logging
from django.conf import settings
from django.contrib.auth.models import User
from django.core import signing
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from .models import (
    UserProfile, Company, Driver, Truck, Container, BookingSlot,
    Trip, ScanPoint, ScanEvent, Notification, AuditLog, TransportRequest
)

logger = logging.getLogger(__name__)

STATUS_MAP = {
    'ENTRY_GATE': 'ENTERED_PORT',
    'BERTH': 'AT_BERTH',
    'CUSTOMS_ZONE': 'PASSED_CUSTOMS',
    'EXIT_GATE': 'EXITED_PORT',
    'DELIVERY': 'DELIVERED',
}

STATUS_ORDER = [
    'CREATED', 'BOOKED', 'APPROVED', 'ARRIVED_GATE',
    'ENTERED_PORT', 'AT_BERTH', 'LOADING_COMPLETE',
    'PASSED_CUSTOMS', 'EXITED_PORT', 'IN_TRANSIT', 'DELIVERED',
]


def audit(user, action, model_name, object_id=None, details='', ip_address=None):
    try:
        AuditLog.objects.create(
            user=user, action=action, model_name=model_name,
            object_id=str(object_id or ''), details=details,
            ip_address=ip_address,
        )
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")


def create_notification(user, title, message):
    try:
        return Notification.objects.create(user=user, title=title, message=message)
    except Exception as e:
        logger.error(f"Failed to create notification: {e}")
        return None


def get_or_create_slot(slot_dt):
    slot_date = slot_dt.date()
    slot_hour = slot_dt.hour
    slot, created = BookingSlot.objects.get_or_create(date=slot_date, hour=slot_hour)
    slot.recalculate_capacity()
    slot.save(update_fields=['capacity', 'is_closed', 'updated_at'])
    if created:
        logger.info(f"Created new booking slot: {slot_date} {slot_hour:02d}:00")
    return slot


@transaction.atomic
def quick_create_trip(*, broker_user, data):
    required_fields = ['carrier_company_name', 'driver_name', 'driver_phone',
                       'truck_plate', 'container_no', 'destination', 'slot_datetime']
    for field in required_fields:
        if not data.get(field):
            raise ValueError(f"الحقل {field} مطلوب")

    carrier, _ = Company.objects.get_or_create(
        name=data['carrier_company_name'], defaults={'company_type': 'carrier'}
    )
    driver, _ = Driver.objects.get_or_create(
        full_name=data['driver_name'], phone=data['driver_phone']
    )
    truck, _ = Truck.objects.get_or_create(
        plate_number=data['truck_plate'], defaults={'owner_company': carrier}
    )
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

    slot = BookingSlot.objects.get(pk=slot.pk)

    trip = Trip.objects.create(
        broker=broker_user, carrier_company=carrier, truck=truck,
        driver=driver, container=container, slot=slot,
        destination=data['destination'], status='BOOKED',
        notes=data.get('notes', ''),
    )

    slot.booked_count = Trip.objects.filter(slot=slot).exclude(status='CANCELLED').count()
    slot.recalculate_capacity()
    slot.save(update_fields=['booked_count', 'capacity', 'is_closed', 'updated_at'])

    trip.qr_token = trip.generate_qr_token()
    trip.save(update_fields=['qr_token'])
    try:
        trip.generate_qr_image()
    except Exception:
        pass

    create_notification(broker_user, 'تم إنشاء الرحلة',
                        f'تم إنشاء الرحلة {trip.trip_code} للحاوية {container.container_no}')
    audit(broker_user, 'CREATE', 'Trip', trip.trip_code,
          f'Quick create for container {container.container_no}')
    logger.info(f"Trip {trip.trip_code} created by {broker_user.username}")
    return trip


def verify_trip_token(token):
    salt = getattr(settings, 'QR_SIGNING_SALT', 'masar-trip')
    max_age = getattr(settings, 'QR_TOKEN_MAX_AGE', 60 * 60 * 72)
    try:
        return signing.loads(token, salt=salt, max_age=max_age)
    except signing.BadSignature:
        raise ValueError("توقيع QR غير صالح أو منتهي الصلاحية")


@transaction.atomic
def scan_trip(*, token, point_type, user, note=''):
    payload = verify_trip_token(token)
    trip = Trip.objects.get(trip_code=payload['trip_id'])

    if trip.status == 'CANCELLED':
        raise ValueError("لا يمكن مسح رحلة ملغاة")

    if ScanEvent.objects.filter(trip=trip, scan_point__point_type=point_type).exists():
        raise ValueError(f"تم مسح هذه الرحلة مسبقاً عند {point_type}")

    point = ScanPoint.objects.get(point_type=point_type, is_active=True)
    new_status = STATUS_MAP.get(point_type)

    if new_status:
        current_idx = STATUS_ORDER.index(trip.status) if trip.status in STATUS_ORDER else -1
        new_idx = STATUS_ORDER.index(new_status) if new_status in STATUS_ORDER else -1
        if new_idx <= current_idx:
            raise ValueError(f"لا يمكن تحويل الحالة من {trip.status} إلى {new_status}")

    event = ScanEvent.objects.create(trip=trip, scan_point=point, scanned_by=user, note=note)

    if new_status:
        trip.status = new_status
        trip.save(update_fields=['status', 'updated_at'])
        create_notification(trip.broker, 'تحديث رحلة',
                            f'الرحلة {trip.trip_code} أصبحت: {trip.get_status_display()}')

    audit(user, 'SCAN', 'Trip', trip.trip_code, f'{point_type} - {note}')
    logger.info(f"Trip {trip.trip_code} scanned at {point_type} by {user.username}")

    if trip.status == 'DELIVERED':
        try:
            tr = TransportRequest.objects.filter(linked_trip=trip).exclude(status__in=['COMPLETED','CANCELLED']).first()
            if tr:
                tr.status = 'COMPLETED'
                tr.save(update_fields=['status','updated_at'])
                create_notification(tr.requester, 'طلب نقل مكتمل', f'تم إكمال طلب النقل للحاوية {tr.container_no}')
                audit(user, 'AUTO_COMPLETE', 'TransportRequest', tr.id, 'Auto-completed')
        except Exception as e:
            logger.error(f'auto-complete failed: {e}')

    return trip, event


def dashboard_summary_for(user):
    role = getattr(getattr(user, 'profile', None), 'role', 'broker')
    qs = Trip.objects.all()
    if role == 'broker':
        qs = qs.filter(broker=user)
    return {
        'total_trips': qs.count(),
        'waiting_trips': qs.filter(status__in=['CREATED', 'BOOKED', 'APPROVED']).count(),
        'inside_port': qs.filter(status__in=['ENTERED_PORT', 'AT_BERTH', 'PASSED_CUSTOMS', 'IN_TRANSIT']).count(),
        'delivered': qs.filter(status='DELIVERED').count(),
        'cancelled': qs.filter(status='CANCELLED').count(),
        'recent_trips': qs.select_related(
            'container', 'truck', 'driver', 'slot', 'carrier_company', 'broker'
        )[:10],
    }


def turnaround_report_for(user):
    role = getattr(getattr(user, 'profile', None), 'role', 'broker')
    qs = Trip.objects.all()
    if role == 'broker':
        qs = qs.filter(broker=user)

    trips = qs.select_related('container', 'truck', 'driver').prefetch_related(
        Prefetch('scan_events', queryset=ScanEvent.objects.select_related('scan_point'))
    )
    report = []
    for trip in trips:
        events = {e.scan_point.point_type: e.scanned_at for e in trip.scan_events.all()}
        minutes = None
        if 'ENTRY_GATE' in events and 'EXIT_GATE' in events:
            delta = events['EXIT_GATE'] - events['ENTRY_GATE']
            minutes = int(delta.total_seconds() // 60)
        report.append({
            'trip_code': str(trip.trip_code),
            'container_no': trip.container.container_no,
            'truck_plate': trip.truck.plate_number,
            'status': trip.status,
            'status_display': trip.get_status_display(),
            'turnaround_minutes': minutes,
        })
    return report
