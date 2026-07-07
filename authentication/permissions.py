from rest_framework.permissions import BasePermission

class IsSuperuser(BasePermission):
    """
    Grants access only to Django superusers (system operators).
    Used for: clinic provisioning, EML management.
    Superusers authenticate via Django admin — not Firebase.
    """
    message = "This action requires superuser privileges."

    def has_permission(self, request, view):
        return bool(
            request.user
            and hasattr(request.user, "is_superuser")
            and request.user.is_superuser
        )


class IsClinicStaff(BasePermission):
    """
    Grants access to any authenticated clinic staff member —
    both ADMINISTRATOR and STANDARD_PHARMACIST roles.
    The baseline permission for all clinic portal endpoints.
    """
    message = "Authentication required. Please log in to the clinic portal."

    def has_permission(self, request, view):
        return bool(getattr(request, "clinic_staff", None))


class IsClinicAdministrator(BasePermission):
    """
    Grants access only to staff with the ADMINISTRATOR role.
    Used for: staff management, facility profile edits, threshold configuration.
    """
    message = "This action requires Clinic Administrator privileges."

    def has_permission(self, request, view):
        staff = getattr(request, "clinic_staff", None)
        if staff is None:
            return False
        return staff.is_administrator()


class IsOwnClinic(BasePermission):
    """
    Ensures staff can only access resources belonging to their own clinic.
    Applied to all Inventory, HoldRequest, and StockAlert views.
    """
    message = "You do not have permission to access another clinic's resources."

    def has_permission(self, request, view):
        staff = getattr(request, "clinic_staff", None)
        if staff is None:
            return False

        if hasattr(request.user, "is_superuser") and request.user.is_superuser:
            return True

        url_clinic_id = view.kwargs.get("clinic_id")
        if url_clinic_id is None:
            return True

        return str(staff.clinic.clinic_id) == str(url_clinic_id)

    def has_object_permission(self, request, view, obj):
        """
        Object-level check for retrieve/update/delete on individual records.
        Resolves the clinic_id from the object itself, since it may be nested
        """
        staff = getattr(request, "clinic_staff", None)
        if staff is None:
            return False

        if hasattr(request.user, "is_superuser") and request.user.is_superuser:
            return True

        clinic_id = (
            getattr(obj, "clinic_id", None)
            or getattr(getattr(obj, "clinic", None), "clinic_id", None)
            or getattr(getattr(obj, "inventory", None), "clinic_id", None)
        )

        if clinic_id is None:
            return True

        return str(staff.clinic.clinic_id) == str(clinic_id)
