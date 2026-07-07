from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from authentication.firebase import FirebaseAuthentication
from authentication.permissions import IsClinicStaff


class MeView(APIView):
    """
    GET /api/v1/auth/me/
    Returns the currently authenticated staff member's profile.
    """
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsClinicStaff]

    def get(self, request):
        staff = request.clinic_staff
        return Response({
            "staff_id": str(staff.staff_id),
            "username": staff.username,
            "full_name": staff.full_name,
            "initials": staff.get_initials(),
            "role": staff.role,
            "role_label": staff.get_role_display(),
            "is_administrator": staff.is_administrator(),
            "clinic": {
                "clinic_id": str(staff.clinic.clinic_id),
                "name": staff.clinic.name,
                "address": staff.clinic.address,
                "latitude": staff.clinic.latitude,
                "longitude": staff.clinic.longitude,
            },
        })


class HealthCheckView(APIView):
    """
    GET /api/v1/health/
    Public endpoint used by UptimeRobot to keep the Render.com
    free-tier service warm
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"})
