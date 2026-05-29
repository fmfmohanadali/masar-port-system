import os
import uuid
import logging

import qrcode
from io import BytesIO

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core import signing, validators
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserProfile(TimeStampedModel):
    ROLE_CHOICES = [
        ('broker', 'مخلص جمركي'),
        ('carrier', 'شركة نقل'),
        ('gate_guard', 'حارس بوابة'),
        ('port_admin', 'إدارة الميناء'),
        ('ops', 'عمليات'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='broker', db_index=True)
    phone = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        verbose_name = "ملف المستخدم"
        verbose_name_plural = "ملفات المستخدمين"

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_admin_or_ops(self):
        return self.role in ('port_admin', 'ops')


class Company(TimeStampedModel):
    COMPANY_TYPES = [
        ('broker', 'مخلص'),
        ('carrier', 'ناقل'),
        ('port', 'ميناء'),
        ('customs', 'جمارك'),
        ('other', 'أخرى'),
    ]

    name = models.CharField(max_length=255, unique=True)
    company_type = models.CharField(max_length=20, choices=COMPANY_TYPES, default='other', db_index=True)
    contact_name = models.CharField(max_length=255, blank=True, null=True)
    contact_phone = models.CharField(max_length=30, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('name',)
        verbose_name = "شركة"
        verbose_name_plural = "الشركات"

    def __str__(self):
        return self.name


class Driver(TimeStampedModel):
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=30)
    national_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('full_name', 'phone')
        ordering = ('full_name',)
        verbose_name = "سائق"
        verbose_name_plural = "السائقين"

    def __str__(self):
        return self.full_name


class Truck(TimeStampedModel):
    plate_number = models.CharField(max_length=50, unique=True)
    owner_company = models.ForeignKey(
        Company, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='trucks'
    )
    truck_type = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('plate_number',)
        verbose_name = "شاحنة"
        verbose_name_plural = "الشاحنات"

    def __str__(self):
        return self.plate_number


class Container(TimeStampedModel):
    container_no = models.CharField(max_length=30, unique=True)
    weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    destination = models.CharField(max_length=255, db_index=True)
    customs_status = models.CharField(max_length=50, default='released', db_index=True)

    class Meta:
        ordering = ('container_no',)
        verbose_name = "حاوية"
        verbose_name_plural = "الحاويات"

    def __str__(self):
        return self.container_no


class BookingSlot(TimeStampedModel):
    date = models.DateField(db_index=True)
    hour = models.PositiveIntegerField(
        help_text='0-23',
        validators=[validators.MaxValueValidator(23)]
    )
    capacity = models.PositiveIntegerField(default=0)
    booked_count = models.PositiveIntegerField(default=0)
    is_closed = models.BooleanField(default=False, db_index=True)
    active_cranes = models.PositiveIntegerField(default=1)
    avg_load_minutes = models.PositiveIntegerField(default=30)
    active_gate_lanes = models.PositiveIntegerField(default=1)
    lane_rate_per_hour = models.PositiveIntegerField(default=10)
    yard_slots = models.PositiveIntegerField(default=20)

    class Meta:
        unique_together = ('date', 'hour')
        ordering = ('date', 'hour')
        verbose_name = "نافذة حجز"
        verbose_name_plural = "نوافذ الحجز"
        indexes = [
            models.Index(fields=['date', 'hour'], name='idx_slot_date_hour'),
            models.Index(fields=['date', 'is_closed'], name='idx_slot_date_closed'),
        ]

    def __str__(self):
        return f"{self.date} {self.hour:02d}:00"

    @property
    def available(self):
        return max(self.capacity - self.booked_count, 0)

    def recalculate_capacity(self):
        crane_capacity = (
            int((60 / self.avg_load_minutes) * self.active_cranes)
            if self.avg_load_minutes else 0
        )
        gate_capacity = self.lane_rate_per_hour * self.active_gate_lanes
        yard_capacity = self.yard_slots
        self.capacity = max(min(crane_capacity, gate_capacity, yard_capacity), 1)
        self.is_closed = self.booked_count >= self.capacity
        return self.capacity


class Trip(TimeStampedModel):
    STATUS_CHOICES = [
        ('CREATED', 'تم الإنشاء'),
        ('BOOKED', 'محجوزة'),
        ('APPROVED', 'معتمدة'),
        ('ARRIVED_GATE', 'وصلت البوابة'),
        ('ENTERED_PORT', 'داخل الميناء'),
        ('AT_BERTH', 'في الرصيف'),
        ('LOADING_COMPLETE', 'اكتمل التحميل'),
        ('PASSED_CUSTOMS', 'اجتازت الجمارك'),
        ('EXITED_PORT', 'خرجت من الميناء'),
        ('IN_TRANSIT', 'في الطريق'),
        ('DELIVERED', 'تم التسليم'),
        ('CANCELLED', 'ملغاة'),
    ]

    trip_code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    broker = models.ForeignKey(User, on_delete=models.PROTECT, related_name='broker_trips')
    carrier_company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='carrier_trips')
    truck = models.ForeignKey(Truck, on_delete=models.PROTECT)
    driver = models.ForeignKey(Driver, on_delete=models.PROTECT)
    container = models.ForeignKey(Container, on_delete=models.PROTECT)
    slot = models.ForeignKey(BookingSlot, on_delete=models.PROTECT, related_name='trips')
    destination = models.CharField(max_length=255)
    qr_token = models.TextField(blank=True, null=True)
    qr_image = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='CREATED', db_index=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = "رحلة"
        verbose_name_plural = "الرحلات"
        indexes = [
            models.Index(fields=['status', 'created_at'], name='idx_trip_status_created'),
            models.Index(fields=['broker', 'status'], name='idx_trip_broker_status'),
        ]

    def __str__(self):
        return f"{self.trip_code} - {self.container.container_no}"

    def generate_qr_token(self):
        payload = {
            'trip_id': str(self.trip_code),
            'truck_plate': self.truck.plate_number,
            'slot_date': str(self.slot.date),
            'slot_hour': self.slot.hour,
            'container_no': self.container.container_no,
        }
        salt = getattr(settings, 'QR_SIGNING_SALT', 'masar-trip')
        return signing.dumps(payload, salt=salt)

    def generate_qr_image(self):
        if not self.qr_token:
            self.qr_token = self.generate_qr_token()
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2
        )
        qr.add_data(self.qr_token)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        filename = f"trip_{self.trip_code}.png"
        self.qr_image.save(filename, ContentFile(buffer.getvalue()), save=False)
        super().save(update_fields=['qr_image'])
        logger.info(f"QR image generated for trip {self.trip_code}")
        return self.qr_image.url if self.qr_image else ''


class TransportRequest(TimeStampedModel):
    STATUS_CHOICES = [
        ('DRAFT', 'مسودة'),
        ('VERIFIED', 'تم التحقق'),
        ('OFFERS_SENT', 'تم إرسال العروض'),
        ('CARRIER_SELECTED', 'تم اختيار شركة النقل'),
        ('PAID', 'مدفوع'),
        ('DRIVER_ASSIGNED', 'تم تعيين السائق'),
        ('PORT_SLOT_BOOKED', 'تم حجز موعد الميناء'),
        ('QR_ISSUED', 'تم إصدار QR'),
        ('COMPLETED', 'مكتمل'),
        ('CANCELLED', 'ملغي'),
    ]

    VALID_TRANSITIONS = {
        'DRAFT': ['VERIFIED', 'CANCELLED'],
        'VERIFIED': ['OFFERS_SENT', 'CANCELLED'],
        'OFFERS_SENT': ['CARRIER_SELECTED', 'CANCELLED'],
        'CARRIER_SELECTED': ['PAID', 'CANCELLED'],
        'PAID': ['DRIVER_ASSIGNED', 'CANCELLED'],
        'DRIVER_ASSIGNED': ['PORT_SLOT_BOOKED', 'CANCELLED'],
        'PORT_SLOT_BOOKED': ['QR_ISSUED', 'CANCELLED'],
        'QR_ISSUED': ['COMPLETED', 'CANCELLED'],
        'COMPLETED': [],
        'CANCELLED': [],
    }

    requester = models.ForeignKey(User, on_delete=models.PROTECT, related_name='transport_requests')
    container_no = models.CharField(max_length=30, db_index=True)
    bl_no = models.CharField(max_length=80, blank=True, null=True)
    vessel_name = models.CharField(max_length=160, blank=True, null=True)
    release_date = models.DateField(blank=True, null=True)
    arrival_port = models.CharField(max_length=160, blank=True, null=True)
    destination = models.CharField(max_length=255)
    release_document = models.FileField(upload_to='release_documents/', blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='DRAFT', db_index=True)
    selected_carrier = models.ForeignKey(
        Company, on_delete=models.SET_NULL, blank=True, null=True,
        related_name='selected_transport_requests'
    )
    agreed_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    assigned_driver = models.ForeignKey(
        Driver, on_delete=models.SET_NULL, blank=True, null=True,
        related_name='transport_requests'
    )
    assigned_truck = models.ForeignKey(
        Truck, on_delete=models.SET_NULL, blank=True, null=True,
        related_name='transport_requests'
    )
    slot = models.ForeignKey(
        BookingSlot, on_delete=models.SET_NULL, blank=True, null=True,
        related_name='transport_requests'
    )
    linked_trip = models.OneToOneField(
        Trip, on_delete=models.SET_NULL, blank=True, null=True,
        related_name='transport_request'
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = "طلب نقل"
        verbose_name_plural = "طلبات النقل"

    def __str__(self):
        return f"{self.container_no} - {self.get_status_display()}"

    def can_transition_to(self, new_status):
        allowed = self.VALID_TRANSITIONS.get(self.status, [])
        return new_status in allowed


class TransportOffer(TimeStampedModel):
    STATUS_CHOICES = [
        ('PENDING', 'قيد الانتظار'),
        ('ACCEPTED', 'مقبول'),
        ('REJECTED', 'مرفوض'),
    ]

    request = models.ForeignKey(TransportRequest, on_delete=models.CASCADE, related_name='offers')
    carrier_company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='transport_offers')
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[validators.MinValueValidator(0)])
    estimated_pickup_at = models.DateTimeField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    class Meta:
        unique_together = ('request', 'carrier_company')
        ordering = ('price', 'created_at')
        verbose_name = "عرض نقل"
        verbose_name_plural = "عروض النقل"

    def __str__(self):
        return f"{self.request.container_no} - {self.carrier_company.name} - {self.price}"


class TransportPayment(TimeStampedModel):
    STATUS_CHOICES = [
        ('PENDING', 'قيد الانتظار'),
        ('PAID', 'مدفوع'),
        ('FAILED', 'فشل'),
        ('REFUNDED', 'مسترد'),
    ]

    request = models.OneToOneField(TransportRequest, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[validators.MinValueValidator(0)])
    method = models.CharField(max_length=60, default='manual')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    transaction_ref = models.CharField(max_length=160, blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "دفعة نقل"
        verbose_name_plural = "دفعات النقل"

    def __str__(self):
        return f"{self.request.container_no} - {self.get_status_display()}"


class ScanPoint(TimeStampedModel):
    POINT_CHOICES = [
        ('ENTRY_GATE', 'بوابة الدخول'),
        ('BERTH', 'الرصيف'),
        ('CUSTOMS_ZONE', 'منطقة الجمارك'),
        ('EXIT_GATE', 'بوابة الخروج'),
        ('DELIVERY', 'التسليم'),
    ]

    name = models.CharField(max_length=120)
    point_type = models.CharField(max_length=30, choices=POINT_CHOICES, unique=True)
    location_description = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('name',)
        verbose_name = "نقطة مسح"
        verbose_name_plural = "نقاط المسح"

    def __str__(self):
        return self.name


class ScanEvent(TimeStampedModel):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='scan_events')
    scan_point = models.ForeignKey(ScanPoint, on_delete=models.PROTECT)
    scanned_by = models.ForeignKey(User, on_delete=models.PROTECT)
    scanned_at = models.DateTimeField(default=timezone.now)
    note = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ('-scanned_at',)
        verbose_name = "حدث مسح"
        verbose_name_plural = "أحداث المسح"
        indexes = [
            models.Index(fields=['trip', 'scan_point'], name='idx_scan_trip_point'),
        ]

    def __str__(self):
        return f"{self.trip.trip_code} @ {self.scan_point.point_type}"


class Notification(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = "إشعار"
        verbose_name_plural = "الإشعارات"

    def __str__(self):
        return self.title


class AuditLog(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=120, db_index=True)
    model_name = models.CharField(max_length=120, db_index=True)
    object_id = models.CharField(max_length=120, blank=True, null=True)
    details = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = "سجل مراجعة"
        verbose_name_plural = "سجلات المراجعة"

    def __str__(self):
        return f"{self.action} - {self.model_name}"
