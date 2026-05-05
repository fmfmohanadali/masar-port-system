from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from .views import (
    LoginAPIView, LogoutAPIView, me, dashboard_summary, turnaround_report,
    TripViewSet, BookingSlotViewSet, ScanPointViewSet, ScanEventViewSet, NotificationViewSet,
    health,TransportRequestViewSet, TransportOfferViewSet, TransportPaymentViewSet
)

router = DefaultRouter()
router.register('trips', TripViewSet, basename='trip')
router.register('booking-slots', BookingSlotViewSet, basename='booking-slot')
router.register('scan-points', ScanPointViewSet, basename='scan-point')
router.register('scan-events', ScanEventViewSet, basename='scan-event')
router.register('notifications', NotificationViewSet, basename='notification')
router.register('transport-requests', TransportRequestViewSet, basename='transport-request')
router.register('transport-offers', TransportOfferViewSet, basename='transport-offer')
router.register('transport-payments', TransportPaymentViewSet, basename='transport-payment')

urlpatterns = [
    path('auth/login/', LoginAPIView.as_view(), name='auth-login'),
    path('auth/logout/', LogoutAPIView.as_view(), name='auth-logout'),
    path('me/', me, name='me'),
    path('dashboard/summary/', dashboard_summary, name='dashboard-summary'),
    path('reports/turnaround/', turnaround_report, name='reports-turnaround'),
    path('health/', health, name='health'),
    path('', include(router.urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
