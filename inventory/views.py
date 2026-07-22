from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from authentication.firebase import FirebaseAuthentication
from authentication.permissions import (
    IsClinicStaff,
    IsClinicAdministrator,
    IsOwnClinic,
)
from inventory.models import Inventory, StockAlert
from inventory.serializers import (
    InventorySerializer,
    InventoryUpdateSerializer,
    ThresholdSerializer,
    StockAlertSerializer,
)


def _get_inventory(clinic_id, inventory_id):
    try:
        return Inventory.objects.select_related(
            "clinic", "medication", "medication__ingredient"
        ).get(inventory_id=inventory_id, clinic__clinic_id=clinic_id)
    except (Inventory.DoesNotExist, ValidationError):
        return None

# Inventory
class InventoryListCreateView(APIView):
    """
    GET  /clinics/{clinic_id}/inventory/  — list inventory
    POST /clinics/{clinic_id}/inventory/  — add medication to inventory
    """
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsClinicStaff, IsOwnClinic]

    def get_clinic(self, clinic_id):
        from clinics.models import Clinic
        try:
            return Clinic.objects.get(clinic_id=clinic_id)
        except (Clinic.DoesNotExist, ValidationError):
            return None

    def get(self, request, clinic_id):
        clinic = self.get_clinic(clinic_id)
        if not clinic:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Clinic not found.", "field": None}},
                status=status.HTTP_404_NOT_FOUND
            )
        qs = Inventory.objects.select_related(
            "medication", "medication__ingredient"
        ).filter(clinic=clinic)

        # Filters
        status_filter = request.query_params.get("status")
        search = request.query_params.get("search")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        if search:
            qs = qs.filter(medication__brand_name__icontains=search)

        serializer = InventorySerializer(qs, many=True)
        return Response({"count": qs.count(), "results": serializer.data})

    def post(self, request, clinic_id):
        clinic = self.get_clinic(clinic_id)
        if not clinic:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Clinic not found.", "field": None}},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = InventorySerializer(
            data=request.data,
            context={"clinic": clinic}
        )
        if serializer.is_valid():
            inventory = serializer.save()
            return Response(
                InventorySerializer(inventory).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InventoryRetrieveUpdateDeleteView(APIView):
    """
    GET    /clinics/{clinic_id}/inventory/{inventory_id}/
    PATCH  /clinics/{clinic_id}/inventory/{inventory_id}/  — quick-toggle update
    DELETE /clinics/{clinic_id}/inventory/{inventory_id}/  — CA only
    """
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsClinicStaff, IsOwnClinic]

    def get(self, request, clinic_id, inventory_id):
        inventory = _get_inventory(clinic_id, inventory_id)
        if not inventory:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Inventory record not found.", "field": None}},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(InventorySerializer(inventory).data)

    def patch(self, request, clinic_id, inventory_id):
        inventory = _get_inventory(clinic_id, inventory_id)
        if not inventory:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Inventory record not found.", "field": None}},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = InventoryUpdateSerializer(inventory, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # Reload to get recomputed status from save()
            inventory.refresh_from_db()
            return Response(InventorySerializer(inventory).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, clinic_id, inventory_id):
        # Only Administrators can delete inventory records
        staff = getattr(request, "clinic_staff", None)
        if not staff or not staff.is_administrator():
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "Only Administrators can remove inventory records.", "field": None}},
                status=status.HTTP_403_FORBIDDEN
            )
        inventory = _get_inventory(clinic_id, inventory_id)
        if not inventory:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Inventory record not found.", "field": None}},
                status=status.HTTP_404_NOT_FOUND
            )
        # cannot delete while active holds exist
        active_holds = inventory.hold_requests.filter(status="PENDING").exists()
        if active_holds:
            return Response(
                {"error": {"code": "ACTIVE_HOLDS_EXIST", "message": "Cannot remove this record while pending hold requests exist.", "field": None}},
                status=status.HTTP_409_CONFLICT
            )
        inventory.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ThresholdUpdateView(APIView):
    """PATCH /clinics/{clinic_id}/inventory/{inventory_id}/threshold/"""
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsClinicAdministrator, IsOwnClinic]

    def patch(self, request, clinic_id, inventory_id):
        inventory = _get_inventory(clinic_id, inventory_id)
        if not inventory:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Inventory record not found.", "field": None}},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ThresholdSerializer(inventory, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            inventory.refresh_from_db()
            return Response(ThresholdSerializer(inventory).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Stock Alerts
class StockAlertListView(APIView):
    """GET /clinics/{clinic_id}/alerts/"""
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsClinicStaff, IsOwnClinic]

    def get(self, request, clinic_id):
        qs = StockAlert.objects.select_related(
            "inventory", "inventory__medication"
        ).filter(inventory__clinic__clinic_id=clinic_id)

        is_resolved = request.query_params.get("is_resolved")
        alert_type = request.query_params.get("alert_type")
        if is_resolved is not None:
            qs = qs.filter(is_resolved=is_resolved.lower() == "true")
        if alert_type:
            qs = qs.filter(alert_type=alert_type.upper())

        unresolved_count = qs.filter(is_resolved=False).count()
        serializer = StockAlertSerializer(qs, many=True)
        return Response({
            "count": qs.count(),
            "unresolved_count": unresolved_count,
            "results": serializer.data,
        })


class StockAlertResolveView(APIView):
    """PATCH /clinics/{clinic_id}/alerts/{alert_id}/resolve/"""
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsClinicStaff, IsOwnClinic]

    def patch(self, request, clinic_id, alert_id):
        try:
            alert = StockAlert.objects.get(
                alert_id=alert_id,
                inventory__clinic__clinic_id=clinic_id
            )
        except (StockAlert.DoesNotExist, ValidationError):
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Alert not found.", "field": None}},
                status=status.HTTP_404_NOT_FOUND
            )
        if alert.is_resolved:
            return Response(
                {"error": {"code": "ALREADY_RESOLVED", "message": "This alert has already been resolved.", "field": None}},
                status=status.HTTP_400_BAD_REQUEST
            )
        alert.resolve()
        return Response({"alert_id": str(alert.alert_id), "is_resolved": True})
