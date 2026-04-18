from django.contrib.auth.models import User
from rest_framework import serializers
from .models import (
    UserProfile, Company, Driver, Truck, Container, BookingSlot,
    Trip, ScanPoint, ScanEvent, Notification, AuditLog
)


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['role', 'phone']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'profile']


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'


class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = '__all__'


class TruckSerializer(serializers.ModelSerializer):
    owner_company_name = serializers.CharField(source='owner_company.name', read_only=True)

    class Meta:
        model = Truck
        fields = '__all__'


class ContainerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Container
        fields = '__all__'


class BookingSlotSerializer(serializers.ModelSerializer):
    available = serializers.IntegerField(read_only=True)

    class Meta:
        model = BookingSlot
        fields = '__all__'


class TripSerializer(serializers.ModelSerializer):
    broker_username = serializers.CharField(source='broker.username', read_only=True)
    carrier_company_name = serializers.CharField(source='carrier_company.name', read_only=True)
    truck_plate = serializers.CharField(source='truck.plate_number', read_only=True)
    driver_name = serializers.CharField(source='driver.full_name', read_only=True)
    container_no = serializers.CharField(source='container.container_no', read_only=True)

    slot_label = serializers.SerializerMethodField()
    qr_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            'id',
            'trip_code',
            'status',
            'destination',
            'notes',
            'slot_datetime',
            'slot_label',
            'broker_username',
            'carrier_company_name',
            'truck_plate',
            'driver_name',
            'container_no',
            'qr_token',
            'qr_image_url',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'trip_code',
            'qr_token',
            'created_at',
            'updated_at',
        ]

    def get_slot_label(self, obj):
        if obj.slot:
            try:
                return f"{obj.slot.date} {obj.slot.hour:02d}:00"
            except Exception:
                return str(obj.slot)
        return ""

    def get_qr_image_url(self, obj):
        """
        IMPORTANT:
        On Render Free, local media files are not reliable.
        This must NEVER raise an exception.
        """
        qr_file = getattr(obj, 'qr_image', None)
        if not qr_file:
            return None

        try:
            url = qr_file.url
        except Exception:
            return None

        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url


class QuickCreateTripSerializer(serializers.Serializer):
    container_no = serializers.CharField(max_length=30)
    truck_plate = serializers.CharField(max_length=50)
    driver_name = serializers.CharField(max_length=255)
    driver_phone = serializers.CharField(max_length=30)
    destination = serializers.CharField(max_length=255)
    carrier_company_name = serializers.CharField(max_length=255)
    slot_datetime = serializers.DateTimeField()
    notes = serializers.CharField(required=False, allow_blank=True)


class ScanPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanPoint
        fields = '__all__'


class ScanEventSerializer(serializers.ModelSerializer):
    trip_code = serializers.CharField(source='trip.trip_code', read_only=True)
    scan_point_name = serializers.CharField(source='scan_point.name', read_only=True)
    scanned_by_name = serializers.CharField(source='scanned_by.username', read_only=True)

    class Meta:
        model = ScanEvent
        fields = '__all__'


class ScanActionSerializer(serializers.Serializer):
    token = serializers.CharField()
    point_type = serializers.CharField()
    note = serializers.CharField(required=False, allow_blank=True)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = '__all__'