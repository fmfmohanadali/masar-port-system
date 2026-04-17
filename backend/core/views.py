from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import status, viewsets, permissions
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Company, Driver, Truck, Container, BookingSlot, Trip, ScanPoint, ScanEvent, Notification
from .serializers import (
    LoginSerializer, UserSerializer, CompanySerializer, DriverSerializer,
    TruckSerializer, ContainerSerializer, BookingSlotSerializer, TripSerializer,
    QuickCreateTripSerializer, ScanPointSerializer, ScanEventSerializer,
    ScanActionSerializer, NotificationSerializer
)
from .permissions import IsOpsOrAdmin, CanScan
from .services import quick_create_trip, scan_trip, dashboard_summary_for, turnaround_report_for, audit
from django.http import JsonResponse

def health(request):
    return JsonResponse({"status": "ok"})

class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(username=serializer.validated_data['username'], password=serializer.validated_data['password'])
        if not user:
            return Response({'detail': 'بيانات الدخول غير صحيحة'}, status=status.HTTP_400_BAD_REQUEST)
        token, _ = Token.objects.get_or_create(user=user)
        audit(user, 'LOGIN', 'User', user.id, 'API login')
        return Response({'token': token.key, 'user': UserSerializer(user).data})


class LogoutAPIView(APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        audit(request.user, 'LOGOUT', 'User', request.user.id, 'API logout')
        return Response({'success': True})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_summary(request):
    summary = dashboard_summary_for(request.user)
    return Response({
        'total_trips': summary['total_trips'],
        'waiting_trips': summary['waiting_trips'],
        'inside_port': summary['inside_port'],
        'delivered': summary['delivered'],
        'recent_trips': TripSerializer(summary['recent_trips'], many=True, context={'request': request}).data,
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def turnaround_report(request):
    return Response({'results': turnaround_report_for(request.user)})


class TripViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TripSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        role = getattr(getattr(user, 'profile', None), 'role', 'broker')
        qs = Trip.objects.select_related('broker', 'carrier_company', 'truck', 'driver', 'container', 'slot').all()
        if role == 'broker':
            qs = qs.filter(broker=user)

        search = self.request.query_params.get('search')
        status_filter = self.request.query_params.get('status')
        if search:
            qs = qs.filter(
                Q(container__container_no__icontains=search) |
                Q(truck__plate_number__icontains=search) |
                Q(driver__full_name__icontains=search) |
                Q(destination__icontains=search)
            )
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    @action(detail=False, methods=['post'])
    def quick_create(self, request):
        serializer = QuickCreateTripSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            trip = quick_create_trip(broker_user=request.user, data=serializer.validated_data)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(TripSerializer(trip, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def generate_qr(self, request, pk=None):
        trip = self.get_object()
        trip.qr_token = trip.generate_qr_token()
        trip.generate_qr_image()
        trip.save(update_fields=['qr_token'])
        return Response(TripSerializer(trip, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def mark_delivered(self, request, pk=None):
        trip = self.get_object()
        trip.status = 'DELIVERED'
        trip.save(update_fields=['status', 'updated_at'])
        audit(request.user, 'UPDATE', 'Trip', trip.trip_code, 'Marked as delivered')
        return Response({'status': trip.status})


class BookingSlotViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BookingSlot.objects.all()
    serializer_class = BookingSlotSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def available(self, request):
        date_str = request.query_params.get('date')
        qs = self.get_queryset().filter(is_closed=False)
        if date_str:
            qs = qs.filter(date=date_str)
        return Response(BookingSlotSerializer(qs, many=True).data)


class ScanPointViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ScanPoint.objects.filter(is_active=True)
    serializer_class = ScanPointSerializer
    permission_classes = [permissions.IsAuthenticated]


class ScanEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ScanEvent.objects.select_related('trip', 'scan_point', 'scanned_by').all()
    serializer_class = ScanEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'], permission_classes=[CanScan])
    def scan(self, request):
        serializer = ScanActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            trip, event = scan_trip(
                token=serializer.validated_data['token'],
                point_type=serializer.validated_data['point_type'],
                user=request.user,
                note=serializer.validated_data.get('note', '')
            )
        except Exception as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'trip': TripSerializer(trip, context={'request': request}).data,
            'event': ScanEventSerializer(event).data,
        })


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response(NotificationSerializer(notification).data)
