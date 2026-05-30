from django.contrib.auth import authenticate
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse

from rest_framework import status, viewsets, permissions
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Company,
    Driver,
    Truck,
    Container,
    BookingSlot,
    Trip,
    ScanPoint,
    ScanEvent,
    Notification,
    TransportRequest,
    TransportOffer,
    TransportPayment,
)

from .serializers import (
    LoginSerializer,
    UserSerializer,
    CompanySerializer,
    DriverSerializer,
    TruckSerializer,
    ContainerSerializer,
    BookingSlotSerializer,
    TripSerializer,
    QuickCreateTripSerializer,
    ScanPointSerializer,
    ScanEventSerializer,
    ScanActionSerializer,
    NotificationSerializer,
    TransportRequestSerializer,
    TransportOfferSerializer,
    TransportPaymentSerializer,
)

from .permissions import CanScan
from .services import (
    quick_create_trip,
    scan_trip,
    dashboard_summary_for,
    turnaround_report_for,
    audit,
)


def health(request):
    return JsonResponse({"status": "ok"})


class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )

        if not user:
            return Response(
                {"detail": "بيانات الدخول غير صحيحة"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token, _ = Token.objects.get_or_create(user=user)
        audit(user, "LOGIN", "User", user.id, "API login")

        return Response(
            {
                "token": token.key,
                "user": UserSerializer(user).data,
            }
        )


class LogoutAPIView(APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        audit(request.user, "LOGOUT", "User", request.user.id, "API logout")
        return Response({"success": True})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def dashboard_summary(request):
    summary = dashboard_summary_for(request.user)

    return Response(
        {
            "total_trips": summary["total_trips"],
            "waiting_trips": summary["waiting_trips"],
            "inside_port": summary["inside_port"],
            "delivered": summary["delivered"],
            "recent_trips": TripSerializer(
                summary["recent_trips"],
                many=True,
                context={"request": request},
            ).data,
        }
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def turnaround_report(request):
    return Response({"results": turnaround_report_for(request.user)})


class TripViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TripSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        role = getattr(getattr(user, "profile", None), "role", "broker")

        qs = Trip.objects.select_related(
            "broker",
            "carrier_company",
            "truck",
            "driver",
            "container",
            "slot",
        ).all()

        if role == "broker":
            qs = qs.filter(broker=user)

        search = self.request.query_params.get("search")
        status_filter = self.request.query_params.get("status")

        if search:
            qs = qs.filter(
                Q(container__container_no__icontains=search)
                | Q(truck__plate_number__icontains=search)
                | Q(driver__full_name__icontains=search)
                | Q(destination__icontains=search)
            )

        if status_filter:
            qs = qs.filter(status=status_filter)

        return qs

    def _ensure_qr_token(self, trip, regenerate=False):
        if regenerate or not trip.qr_token:
            trip.qr_token = trip.generate_qr_token()
            trip.save(update_fields=["qr_token"])

        if not trip.qr_image:
            try:
                trip.generate_qr_image()
            except Exception:
                pass

        return trip

    @action(detail=False, methods=["post"])
    def quick_create(self, request):
        serializer = QuickCreateTripSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            trip = quick_create_trip(
                broker_user=request.user,
                data=serializer.validated_data,
            )
            trip = self._ensure_qr_token(trip)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            TripSerializer(trip, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def generate_qr(self, request, pk=None):
        trip = self.get_object()
        trip = self._ensure_qr_token(trip, regenerate=True)

        return Response(
            TripSerializer(trip, context={"request": request}).data
        )

    @action(detail=True, methods=["post"])
    def mark_delivered(self, request, pk=None):
        trip = self.get_object()
        trip.status = "DELIVERED"
        trip.save(update_fields=["status", "updated_at"])

        audit(
            request.user,
            "UPDATE",
            "Trip",
            trip.trip_code,
            "Marked as delivered",
        )

        return Response({"status": trip.status})


class BookingSlotViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BookingSlot.objects.all()
    serializer_class = BookingSlotSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get"])
    def available(self, request):
        date_str = request.query_params.get("date")
        qs = self.get_queryset().filter(is_closed=False)

        if date_str:
            qs = qs.filter(date=date_str)

        return Response(BookingSlotSerializer(qs, many=True).data)


class CompanyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]


class DriverViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer
    permission_classes = [permissions.IsAuthenticated]


class TruckViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Truck.objects.select_related('owner_company').filter(is_active=True)
    serializer_class = TruckSerializer
    permission_classes = [permissions.IsAuthenticated]


class ScanPointViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ScanPoint.objects.filter(is_active=True)
    serializer_class = ScanPointSerializer
    permission_classes = [permissions.IsAuthenticated]


class ScanEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ScanEvent.objects.select_related(
        "trip",
        "scan_point",
        "scanned_by",
    ).all()
    serializer_class = ScanEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[CanScan],
    )
    def scan(self, request):
        serializer = ScanActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            trip, event = scan_trip(
                token=serializer.validated_data["token"],
                point_type=serializer.validated_data["point_type"],
                user=request.user,
                note=serializer.validated_data.get("note", ""),
            )
        except Exception as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "trip": TripSerializer(
                    trip,
                    context={"request": request},
                ).data,
                "event": ScanEventSerializer(event).data,
            }
        )


class TransportRequestViewSet(viewsets.ModelViewSet):
    serializer_class = TransportRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        role = getattr(getattr(user, "profile", None), "role", "broker")

        qs = (
            TransportRequest.objects.select_related(
                "requester",
                "selected_carrier",
                "assigned_driver",
                "assigned_truck",
                "slot",
                "linked_trip",
            )
            .prefetch_related("offers")
            .all()
        )

        if role == "broker":
            qs = qs.filter(requester=user)

        return qs

    def perform_create(self, serializer):
        obj = serializer.save(requester=self.request.user, status="DRAFT")

        audit(
            self.request.user,
            "CREATE",
            "TransportRequest",
            obj.id,
            f"Created transport request for container {obj.container_no}",
        )

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        obj = self.get_object()
        obj.status = "VERIFIED"
        obj.save(update_fields=["status", "updated_at"])

        audit(
            request.user,
            "UPDATE",
            "TransportRequest",
            obj.id,
            "Verified transport request",
        )

        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"])
    def send_offers(self, request, pk=None):
        obj = self.get_object()
        obj.status = "OFFERS_SENT"
        obj.save(update_fields=["status", "updated_at"])

        audit(
            request.user,
            "UPDATE",
            "TransportRequest",
            obj.id,
            "Offers sent",
        )

        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"])
    def select_offer(self, request, pk=None):
        obj = self.get_object()
        offer_id = request.data.get("offer_id")

        if not offer_id:
            return Response(
                {"detail": "offer_id مطلوب"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            offer = obj.offers.get(id=offer_id)
        except TransportOffer.DoesNotExist:
            return Response(
                {"detail": "العرض غير موجود"},
                status=status.HTTP_404_NOT_FOUND,
            )

        obj.selected_carrier = offer.carrier_company
        obj.agreed_price = offer.price
        obj.status = "CARRIER_SELECTED"
        obj.save(
            update_fields=[
                "selected_carrier",
                "agreed_price",
                "status",
                "updated_at",
            ]
        )

        obj.offers.exclude(id=offer.id).update(status="REJECTED")
        offer.status = "ACCEPTED"
        offer.save(update_fields=["status", "updated_at"])

        audit(
            request.user,
            "UPDATE",
            "TransportRequest",
            obj.id,
            "Carrier offer selected",
        )

        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        obj = self.get_object()
        amount = request.data.get("amount") or obj.agreed_price

        if not amount:
            return Response(
                {"detail": "amount مطلوب أو يجب وجود سعر متفق"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment, _ = TransportPayment.objects.get_or_create(
            request=obj,
            defaults={
                "amount": amount,
                "method": request.data.get("method", "manual"),
                "transaction_ref": request.data.get("transaction_ref", ""),
            },
        )

        payment.amount = amount
        payment.method = request.data.get("method", payment.method or "manual")
        payment.transaction_ref = request.data.get(
            "transaction_ref",
            payment.transaction_ref or "",
        )
        payment.status = "PAID"
        payment.paid_at = timezone.now()
        payment.save()

        obj.status = "PAID"
        obj.save(update_fields=["status", "updated_at"])

        audit(
            request.user,
            "PAYMENT",
            "TransportRequest",
            obj.id,
            "Payment marked as paid",
        )

        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"])
    def assign_driver(self, request, pk=None):
        obj = self.get_object()

        driver_id = request.data.get("driver_id")
        truck_id = request.data.get("truck_id")

        if not driver_id or not truck_id:
            return Response(
                {"detail": "driver_id و truck_id مطلوبان"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            driver = Driver.objects.get(id=driver_id)
            truck = Truck.objects.get(id=truck_id)
        except (Driver.DoesNotExist, Truck.DoesNotExist):
            return Response(
                {"detail": "السائق أو الشاحنة غير موجود"},
                status=status.HTTP_404_NOT_FOUND,
            )

        obj.assigned_driver = driver
        obj.assigned_truck = truck
        obj.status = "DRIVER_ASSIGNED"
        obj.save(
            update_fields=[
                "assigned_driver",
                "assigned_truck",
                "status",
                "updated_at",
            ]
        )

        audit(
            request.user,
            "UPDATE",
            "TransportRequest",
            obj.id,
            "Driver and truck assigned",
        )

        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"])
    def book_slot(self, request, pk=None):
        obj = self.get_object()
        slot_id = request.data.get("slot_id")

        if not slot_id:
            return Response(
                {"detail": "slot_id مطلوب"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            slot = BookingSlot.objects.get(id=slot_id)
        except BookingSlot.DoesNotExist:
            return Response(
                {"detail": "الموعد غير موجود"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if slot.is_closed:
            return Response(
                {"detail": "الموعد مغلق أو ممتلئ"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        obj.slot = slot
        obj.status = "PORT_SLOT_BOOKED"
        obj.save(update_fields=["slot", "status", "updated_at"])

        audit(
            request.user,
            "UPDATE",
            "TransportRequest",
            obj.id,
            "Port slot booked",
        )

        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"])
    def issue_qr(self, request, pk=None):
        obj = self.get_object()

        if not obj.selected_carrier:
            return Response(
                {"detail": "يجب اختيار شركة النقل أولاً"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not obj.assigned_driver or not obj.assigned_truck:
            return Response(
                {"detail": "يجب تخصيص السائق والشاحنة أولاً"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not obj.slot:
            return Response(
                {"detail": "يجب حجز موعد الميناء أولاً"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not obj.linked_trip:
            container, _ = Container.objects.get_or_create(
                container_no=obj.container_no,
                defaults={
                    "destination": obj.destination,
                    "customs_status": "released",
                },
            )

            if container.destination != obj.destination:
                container.destination = obj.destination
                container.save(update_fields=["destination", "updated_at"])

            trip = Trip.objects.create(
                broker=obj.requester,
                carrier_company=obj.selected_carrier,
                truck=obj.assigned_truck,
                driver=obj.assigned_driver,
                container=container,
                slot=obj.slot,
                destination=obj.destination,
                status="BOOKED",
                notes=f"Transport request #{obj.id}",
            )

            trip.qr_token = trip.generate_qr_token()
            trip.save(update_fields=["qr_token"])
            try:
                trip.generate_qr_image()
            except Exception:
                pass

            obj.linked_trip = trip

        obj.status = "QR_ISSUED"
        obj.save(update_fields=["linked_trip", "status", "updated_at"])

        audit(
            request.user,
            "UPDATE",
            "TransportRequest",
            obj.id,
            "QR issued",
        )

        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["get"])
    def check_completion(self, request, pk=None):
        obj = self.get_object()
        if not obj.linked_trip:
            return Response({
                "can_complete": False,
                "reason": "لا توجد رحلة مرتبطة",
            })

        trip = obj.linked_trip
        passed = list(
            trip.scan_events.select_related("scan_point")
            .values_list("scan_point__point_type", flat=True)
        )
        all_points = ["ENTRY_GATE", "BERTH", "CUSTOMS_ZONE", "EXIT_GATE", "DELIVERY"]
        missing = [p for p in all_points if p not in passed]
        can_complete = trip.status == "DELIVERED" and len(missing) == 0

        if can_complete and obj.status == "QR_ISSUED":
            obj.status = "COMPLETED"
            obj.save(update_fields=["status", "updated_at"])

        return Response({
            "can_complete": can_complete,
            "trip_status": trip.status,
            "scan_points_passed": passed,
            "missing_points": missing,
            "transport_status": obj.status,
        })


class TransportOfferViewSet(viewsets.ModelViewSet):
    serializer_class = TransportOfferSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = TransportOffer.objects.select_related(
            "request",
            "carrier_company",
        ).all()

        request_id = self.request.query_params.get("request_id")

        if request_id:
            qs = qs.filter(request_id=request_id)

        return qs


class TransportPaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TransportPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        role = getattr(getattr(user, "profile", None), "role", "broker")

        qs = TransportPayment.objects.select_related("request").all()

        if role == "broker":
            qs = qs.filter(request__requester=user)

        return qs


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=["is_read"])

        return Response(NotificationSerializer(notification).data)

