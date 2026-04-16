from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LoginAPIView, LogoutAPIView, me, dashboard_summary, turnaround_report,
    TripViewSet, BookingSlotViewSet, ScanPointViewSet, ScanEventViewSet, NotificationViewSet
)

router = DefaultRouter()
router.register('trips', TripViewSet, basename='trip')
router.register('booking-slots', BookingSlotViewSet, basename='booking-slot')
router.register('scan-points', ScanPointViewSet, basename='scan-point')
router.register('scan-events', ScanEventViewSet, basename='scan-event')
router.register('notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('auth/login/', LoginAPIView.as_view(), name='auth-login'),
    path('auth/logout/', LogoutAPIView.as_view(), name='auth-logout'),
    path('me/', me, name='me'),
    path('dashboard/summary/', dashboard_summary, name='dashboard-summary'),
    path('reports/turnaround/', turnaround_report, name='reports-turnaround'),
    path('', include(router.urls)),
]
