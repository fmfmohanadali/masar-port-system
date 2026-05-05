
from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from .models import (
    UserProfile, Company, Driver, Truck, Container, BookingSlot,
    Trip, ScanPoint, ScanEvent, Notification, AuditLog, TransportRequest, TransportOffer, TransportPayment
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
        fields = '__all__'
        read_only_fields = ['trip_code', 'qr_token', 'qr_image', 'created_at', 'updated_at']

    def get_slot_label(self, obj):
        return f"{obj.slot.date} {obj.slot.hour:02d}:00"

    def get_qr_image_url(self, obj):
        request = self.context.get('request')
        if obj.qr_image:
            # استخدام request.build_absolute_uri لضمان الحصول على http://domain.com/media/...
            url = obj.qr_image.url
            if request is not None:
                return request.build_absolute_uri(url)
            # حل احتياطي في حال عدم وجود request (مثلاً عند استدعاء السيرياليزر من خارج الـ view)
            return f"http://localhost:8000{url}" # تأكد من تغيير هذا في الإنتاج
        return None


class QuickCreateTripSerializer(serializers.Serializer):
    container_no = serializers.CharField(max_length=30)
    truck_plate = serializers.CharField(max_length=50)
    driver_name = serializers.CharField(max_length=255)
    driver_phone = serializers.CharField(max_length=30)
    destination = serializers.CharField(max_length=255)
    carrier_company_name = serializers.CharField(max_length=255)
    slot_datetime = serializers.DateTimeField()
    notes = serializers.CharField(required=False, allow_blank=True)

class TransportOfferSerializer(serializers.ModelSerializer):
    carrier Meta:    carrier_company_name = serializers.CharField(source='carrier_company.name', read_only=True)
        model = TransportOffer
        fields = '__all__'


class TransportPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportPayment
        fields = '__all__'


class TransportRequestSerializer(serializers.ModelSerializer):
    requester_username = serializers.CharField(source='requester.username', read_only=True)
    selected_carrier_name = serializers.CharField(source='selected_carrier.name', read_only=True)
    assigned_driver_name = serializers.CharField(source='assigned_driver.full_name', read_only=True)
    assigned_truck_plate = serializers.CharField(source='assigned_truck.plate_number', read_only=True)
    slot_label = serializers.SerializerMethodField()
    linked_trip_code = serializers.CharField(source='linked_trip.trip_code', read_only=True)
    qr_token = serializers.CharField(source='linked_trip.qr_token', read_only=True)
    qr_image_url = serializers.SerializerMethodField()
    offers = TransportOfferSerializer(many=True, read_only=True)
    payment = TransportPaymentSerializer(read_only=True)

    class Meta:
        model = TransportRequest
        fields = '__all__'
        read_only_fields = [
            'requester',
            'status',
            'selected_carrier',
            'agreed_price',
            'assigned_driver',
            'assigned_truck',
            'slot',
            'linked_trip',
            'created_at',
            'updated_at',
        ]

    def get_slot_label(self, obj):
        if not obj.slot:
            return None
        return f"{obj.slot.date} {obj.slot.hour:02d}:00"

    def get_qr_image_url(self, obj):
        request = self.context.get('request')
        trip = obj.linked_trip

        if not trip or not trip.qr_image:
            return None

        url = trip.qr_image.url

        if request is not None:
            return request.build_absolute_uri(url)

        return url



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