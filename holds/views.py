from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.core.exceptions import ValidationError

from authentication.firebase import FirebaseAuthentication
from authentication.permissions import IsClinicStaff, IsOwnClinic
from holds.models import HoldRequest
from holds.serializers import (
    HoldRequestCreateSerializer,
    HoldRequestPublicSerializer,
    HoldRequestClinicSerializer,
    HoldRequestProcessSerializer,
)
from inventory.serializers import InventorySerializer


# Client-facing
class HoldRequestCreateView(APIView):
    """
    POST /hold-requests/
    Public. Rate-limited to 3 active holds per phone number.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        # Anti-spam: max 3 active holds per contact number
        patient_contact = request.data.get("patient_contact", "")
        if patient_contact:
            active_count = HoldRequest.objects.filter(
                patient_contact=patient_contact,
                status=HoldRequest.Status.PENDING
            ).count()
            if active_count >= 3:
                return Response(
                    {"error": {"code": "TOO_MANY_HOLDS", "message": "You already have 3 active hold requests. Please wait for one to resolve.", "field": None}},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )

        serializer = HoldRequestCreateSerializer(data=request.data)
        if serializer.is_valid():
            hold = serializer.save()
            return Response(
                HoldRequestPublicSerializer(hold).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HoldRequestStatusView(APIView):
    """
    GET    /hold-requests/{request_id}/  — client polls for status updates
    DELETE /hold-requests/{request_id}/  — client cancels a pending hold
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def get_object(self, request_id):
        try:
            return HoldRequest.objects.select_related(
                "inventory", "inventory__clinic", "inventory__medication"
            ).get(request_id=request_id)
        except (HoldRequest.DoesNotExist, ValidationError):
            return None

    def get(self, request, request_id):
        hold = self.get_object(request_id)
        if not hold:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Hold request not found.", "field": None}},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(HoldRequestPublicSerializer(hold).data)

    def delete(self, request, request_id):
        hold = self.get_object(request_id)
        if not hold:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Hold request not found.", "field": None}},
                status=status.HTTP_404_NOT_FOUND
            )
        if hold.status != HoldRequest.Status.PENDING:
            return Response(
                {"error": {"code": "CANNOT_CANCEL", "message": f"Cannot cancel a hold with status '{hold.status}'.", "field": None}},
                status=status.HTTP_400_BAD_REQUEST
            )
        hold.status = HoldRequest.Status.EXPIRED
        from django.utils import timezone
        hold.resolved_at = timezone.now()
        hold.save(update_fields=["status", "resolved_at"])
        hold.purge_phi()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Clinic-facing
class ClinicHoldRequestListView(APIView):
    """
    GET /clinics/{clinic_id}/hold-requests/
    The inbox polled every 30s by the clinic dashboard.
    Returns pending_count for the notification badge.
    """
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsClinicStaff, IsOwnClinic]

    def get(self, request, clinic_id):
        qs = HoldRequest.objects.select_related(
            "inventory", "inventory__medication", "inventory__clinic"
        ).filter(inventory__clinic__clinic_id=clinic_id)

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        pending_count = qs.filter(status=HoldRequest.Status.PENDING).count()
        serializer = HoldRequestClinicSerializer(qs, many=True)
        return Response({
            "count": qs.count(),
            "pending_count": pending_count,
            "results": serializer.data,
        })


class HoldRequestProcessView(APIView):
    """
    PATCH /clinics/{clinic_id}/hold-requests/{request_id}/
    Approve or deny a hold. Atomic, inventory is decremented inside the model.
    """
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsClinicStaff, IsOwnClinic]

    def patch(self, request, clinic_id, request_id):
        try:
            hold = HoldRequest.objects.select_related(
                "inventory", "inventory__medication", "inventory__clinic"
            ).get(
                request_id=request_id,
                inventory__clinic__clinic_id=clinic_id
            )
        except (HoldRequest.DoesNotExist, ValidationError):
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Hold request not found.", "field": None}},
                status=status.HTTP_404_NOT_FOUND
            )

        if hold.status != HoldRequest.Status.PENDING:
            return Response(
                {"error": {"code": "ALREADY_RESOLVED", "message": f"This hold is already '{hold.status}'.", "field": None}},
                status=status.HTTP_400_BAD_REQUEST
            )

        if hold.is_expired():
            return Response(
                {"error": {"code": "HOLD_EXPIRED", "message": "This hold has passed its 2-hour window.", "field": None}},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = HoldRequestProcessSerializer(hold, data=request.data)
        if serializer.is_valid():
            try:
                hold = serializer.save()
            except ValueError as e:
                return Response(
                    {"error": {"code": "INSUFFICIENT_STOCK", "message": str(e), "field": None}},
                    status=status.HTTP_400_BAD_REQUEST
                )
            hold.inventory.refresh_from_db()
            return Response({
                "request_id": str(hold.request_id),
                "status": hold.status,
                "re-solved_at": hold.resolved_at,
                "inventory": InventorySerializer(hold.inventory).data,
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
