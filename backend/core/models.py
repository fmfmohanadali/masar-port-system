import os
import uuid
import qrcode
from io import BytesIO
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core import signing
from django.db import models
from django.utils import timezone


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
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='broker')
    phone = models.CharField(max_length=30, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class Company(TimeStampedModel):
    COMPANY_TYPES = [
        ('broker', 'مخلص'),
        ('carrier', 'ناقل'),
        ('port', 'ميناء'),
        ('customs', 'جمارك'),
        ('other', 'أخرى'),
    ]
    name = models.CharField(max_length=255, unique=True)
    company_type = models.CharField(max_length=20, choices=COMPANY_TYPES, default='other')
    contact_name = models.CharField(max_length=255, blank=True, null=True)
    contact_phone = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class Driver(TimeStampedModel):
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=30)
    national_id = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        unique_together = ('full_name', 'phone')
        ordering = ('full_name',)

    def __str__(self):
        return self.full_name


class Truck(TimeStampedModel):
    plate_number = models.CharField(max_length=50, unique=True)
    owner_company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='trucks')
    truck_type = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('plate_number',)

    def __str__(self):
        return self.plate_number


class Container(TimeStampedModel):
    container_no = models.CharField(max_length=30, unique=True)
    weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    destination = models.CharField(max_length=255)
    customs_status = models.CharField(max_length=50, default='released')

    class Meta:
        ordering = ('container_no',)

    def __str__(self):
        return self.container_no


class BookingSlot(TimeStampedModel):
    date = models.DateField()
    hour = models.PositiveIntegerField(help_text='0-23')
    capacity = models.PositiveIntegerField(default=0)
    booked_count = models.PositiveIntegerField(default=0)
    is_closed = models.BooleanField(default=False)
    active_cranes = models.PositiveIntegerField(default=1)
    avg_load_minutes = models.PositiveIntegerField(default=30)
    active_gate_lanes = models.PositiveIntegerField(default=1)
    lane_rate_per_hour = models.PositiveIntegerField(default=10)
    yard_slots = models.PositiveIntegerField(default=20)

    class Meta:
        unique_together = ('date', 'hour')
        ordering = ('date', 'hour')

    def __str__(self):
        return f"{self.date} {self.hour:02d}:00"

    @property
    def available(self):
        return max(self.capacity - self.booked_count, 0)

    def recalculate_capacity(self):
        crane_capacity = int((60 / self.avg_load_minutes) * self.active_cranes) if self.avg_load_minutes else 0
        gate_capacity = self.lane_rate_per_hour * self.active_gate_lanes
        yard_capacity = self.yard_slots
        self.capacity = max(min(crane_capacity, gate_capacity, yard_capacity), 1)
        self.is_closed = self.booked_count >= self.capacity
        return self.capacity


class Trip(TimeStampedModel):
    STATUS_CHOICES = [
        ('CREATED', 'Created'),
        ('BOOKED', 'Booked'),
        ('APPROVED', 'Approved'),
        ('ARRIVED_GATE', 'Arrived Gate'),
        ('ENTERED_PORT', 'Entered Port'),
        ('AT_BERTH', 'At Berth'),
        ('LOADING_COMPLETE', 'Loading Complete'),
        ('PASSED_CUSTOMS', 'Passed Customs'),
        ('EXITED_PORT', 'Exited Port'),
        ('IN_TRANSIT', 'In Transit'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
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
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='CREATED')
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f"{self.trip_code} - {self.container.container_no}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self.slot.booked_count = Trip.objects.filter(slot=self.slot).count()
            self.slot.recalculate_capacity()
            self.slot.save(update_fields=['booked_count', 'capacity', 'is_closed', 'updated_at'])
            if not self.qr_token:
                self.qr_token = self.generate_qr_token()
                super().save(update_fields=['qr_token'])
            if not self.qr_image:
                self.generate_qr_image()

    def generate_qr_token(self):
        payload = {
            'trip_id': str(self.trip_code),
            'truck_plate': self.truck.plate_number,
            'slot_date': str(self.slot.date),
            'slot_hour': self.slot.hour,
            'container_no': self.container.container_no,
        }
        return signing.dumps(payload, salt='masar-trip')

    def generate_qr_image(self):
        if not self.qr_token:
            self.qr_token = self.generate_qr_token()
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(self.qr_token)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        filename = f"trip_{self.trip_code}.png"
        self.qr_image.save(filename, ContentFile(buffer.getvalue()), save=False)
        super().save(update_fields=['qr_image'])
        return self.qr_image.url if self.qr_image else ''


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

    def __str__(self):
        return f"{self.trip.trip_code} @ {self.scan_point.point_type}"


class Notification(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return self.title


class AuditLog(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=120)
    model_name = models.CharField(max_length=120)
    object_id = models.CharField(max_length=120, blank=True, null=True)
    details = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f"{self.action} - {self.model_name}"
