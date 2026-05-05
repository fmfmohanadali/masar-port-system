from django.contrib import admin
from .models import (
    UserProfile, Company, Driver, Truck, Container,
    BookingSlot, Trip, ScanPoint, ScanEvent, Notification, AuditLog,TransportRequest, TransportOffer, TransportPayment
)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone', 'created_at')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email', 'phone')


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'company_type', 'contact_name', 'contact_phone')
    list_filter = ('company_type',)
    search_fields = ('name', 'contact_name', 'contact_phone')


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'national_id')
    search_fields = ('full_name', 'phone', 'national_id')


@admin.register(Truck)
class TruckAdmin(admin.ModelAdmin):
    list_display = ('plate_number', 'owner_company', 'truck_type', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('plate_number',)


@admin.register(Container)
class ContainerAdmin(admin.ModelAdmin):
    list_display = ('container_no', 'destination', 'customs_status', 'weight')
    search_fields = ('container_no', 'destination')
    list_filter = ('customs_status',)


@admin.register(BookingSlot)
class BookingSlotAdmin(admin.ModelAdmin):
    list_display = ('date', 'hour', 'capacity', 'booked_count', 'is_closed')
    list_filter = ('date', 'is_closed')


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('trip_code', 'container', 'truck', 'driver', 'destination', 'status', 'slot')
    list_filter = ('status', 'slot__date')
    search_fields = ('container__container_no', 'truck__plate_number', 'driver__full_name', 'destination')


@admin.register(ScanPoint)
class ScanPointAdmin(admin.ModelAdmin):
    list_display = ('name', 'point_type', 'is_active')
    list_filter = ('point_type', 'is_active')


@admin.register(ScanEvent)
class ScanEventAdmin(admin.ModelAdmin):
    list_display = ('trip', 'scan_point', 'scanned_by', 'scanned_at')
    list_filter = ('scan_point', 'scanned_at')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'is_read', 'created_at')
    list_filter = ('is_read',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'model_name', 'object_id', 'user', 'created_at')
    list_filter = ('action', 'model_name')

@admin.register(TransportRequest)
class TransportRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'container_no',
        'bl_no',
        'requester',
        'selected_carrier',
        'status',
        'agreed_price',
        'created_at',
    )
    list_filter = ('status', 'arrival_port', 'created_at')
    search_fields = (
        'container_no',
        'bl_no',
        'vessel_name',
        'destination',
        'requester__username',
        'selected_carrier__name',
    )


@admin.register(TransportOffer)
class TransportOfferAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'request',
        'carrier_company',
        'price',
        'status',
        'estimated_pickup_at',
    )
    list_filter = ('status', 'carrier_company')
    search_fields = (
        'request__container_no',
        'carrier_company__name',
    )


@admin.register(TransportPayment)
class TransportPaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'request',
        'amount',
        'method',
        'status',
        'transaction_ref',
        'paid_at',
    )
    list_filter = ('status', 'method')
    search_fields = (
        'request__container_no',
        'transaction_ref',
    )