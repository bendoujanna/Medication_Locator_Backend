from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.exceptions import ValidationError

from authentication.firebase import FirebaseAuthentication
from authentication.permissions import (
    IsSuperuser,
    IsClinicStaff,
    IsClinicAdministrator,
    IsOwnClinic,
)
from clinics.models import Clinic, ClinicStaff
from clinics.serializers import (
    ClinicSerializer,
    ClinicStatusSerializer,
    ClinicStaffReadSerializer,
    ClinicStaffCreateSerializer,
    ClinicStaffUpdateSerializer,
    ClinicStaffStatusSerializer,
)


class ClinicListCreateView(APIView):
    """
    GET  /clinics/        — list all clinics (Superuser only)
    POST /clinics/        — create a new clinic (Superuser only)
    """
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsSuperuser]

    def get(self, request):
        is_active = request.query_params.get("is_active")
        qs = Clinic.objects.all()
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")

        # Manual pagination
        page_size = min(int(request.query_params.get("page_size", 20)), 100)
        page = int(request.query_params.get("page", 1))
        start = (page - 1) * page_size
        end = start + page_size
        total = qs.count()

        serializer = ClinicSerializer(qs[start:end], many=True)
        return Response({
            "count": total,
            "results": serializer.data,
        })

    def post(self, request):
        serializer = ClinicSerializer(data=request.data)
        if serializer.is_valid():
            clinic = serializer.save()
            return Response(ClinicSerializer(clinic).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClinicRetrieveUpdateView(APIView):
    """
    GET   /clinics/{clinic_id}/  — retrieve clinic details
    PATCH /clinics/{clinic_id}/  — update clinic profile (CA for own clinic, SU for any)
    """
    authentication_classes = [FirebaseAuthentication]

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsClinicStaff(), IsOwnClinic()]
        return [IsClinicAdministrator(), IsOwnClinic()]

    def get_object(self, clinic_id):
        try:
            return Clinic.objects.get(clinic_id=clinic_id)
        except (Clinic.DoesNotExist, ValidationError):
            return None

    def get(self, request, clinic_id):
        clinic = self.get_object(clinic_id)
        if not clinic:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Clinic not found.", "field": None}},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(ClinicSerializer(clinic).data)

    def patch(self, request, clinic_id):
        clinic = self.get_object(clinic_id)
        if not clinic:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Clinic not found.", "field": None}},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ClinicSerializer(clinic, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClinicStatusView(APIView):
    """PATCH /clinics/{clinic_id}/status/ — activate or deactivate a clinic"""
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsSuperuser]

    def patch(self, request, clinic_id):
        try:
            clinic = Clinic.objects.get(clinic_id=clinic_id)
        except Clinic.DoesNotExist:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Clinic not found.", "field": None}},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ClinicStatusSerializer(clinic, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Staff
class StaffListCreateView(APIView):
    """
    GET  /clinics/{clinic_id}/staff/  — list staff (CA/SU)
    POST /clinics/{clinic_id}/staff/  — provision new staff (CA/SU)
    """
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsClinicAdministrator, IsOwnClinic]

    def get_clinic(self, clinic_id):
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
        staff = ClinicStaff.objects.filter(clinic=clinic)
        serializer = ClinicStaffReadSerializer(staff, many=True)
        return Response({"count": staff.count(), "results": serializer.data})

    def post(self, request, clinic_id):
        clinic = self.get_clinic(clinic_id)
        if not clinic:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Clinic not found.", "field": None}},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ClinicStaffCreateSerializer(
            data=request.data,
            context={"clinic": clinic, "request": request}
        )
        if serializer.is_valid():
            staff = serializer.save()
            return Response(
                ClinicStaffReadSerializer(staff).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StaffRetrieveUpdateView(APIView):
    """
    GET   /clinics/{clinic_id}/staff/{staff_id}/  — retrieve staff member
    PATCH /clinics/{clinic_id}/staff/{staff_id}/  — update role
    """
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsClinicAdministrator, IsOwnClinic]

    def get_object(self, clinic_id, staff_id):
        try:
            return ClinicStaff.objects.select_related("clinic").get(
                staff_id=staff_id, clinic__clinic_id=clinic_id
            )
        except (ClinicStaff.DoesNotExist, ValidationError):
            return None

    def get(self, request, clinic_id, staff_id):
        staff = self.get_object(clinic_id, staff_id)
        if not staff:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Staff member not found.", "field": None}},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(ClinicStaffReadSerializer(staff).data)

    def patch(self, request, clinic_id, staff_id):
        staff = self.get_object(clinic_id, staff_id)
        if not staff:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Staff member not found.", "field": None}},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ClinicStaffUpdateSerializer(staff, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(ClinicStaffReadSerializer(staff).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StaffStatusView(APIView):
    """PATCH /clinics/{clinic_id}/staff/{staff_id}/status/ — activate/deactivate"""
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsClinicAdministrator, IsOwnClinic]

    def patch(self, request, clinic_id, staff_id):
        try:
            staff = ClinicStaff.objects.get(
                staff_id=staff_id, clinic__clinic_id=clinic_id
            )
        except ClinicStaff.DoesNotExist:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Staff member not found.", "field": None}},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ClinicStaffStatusSerializer(
            staff, data=request.data, partial=True,
            context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)