import firebase_admin.auth as firebase_auth
from rest_framework import serializers

from clinics.models import Clinic, ClinicStaff
from authentication.firebase import (
    create_firebase_user,
    delete_firebase_user,
    deactivate_firebase_user,
    reactivate_firebase_user,
    revoke_firebase_tokens,
)


class ClinicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinic
        fields = [
            "clinic_id",
            "name",
            "address",
            "latitude",
            "longitude",
            "operating_hours",
            "emergency_contact",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["clinic_id", "created_at"]

    def validate_latitude(self, value):
        if not (-90 <= value <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        if not (-180 <= value <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value


class ClinicStatusSerializer(serializers.ModelSerializer):
    """Minimal serializer for the activate/deactivate endpoint"""
    class Meta:
        model = Clinic
        fields = ["clinic_id", "is_active"]
        read_only_fields = ["clinic_id"]


class ClinicStaffReadSerializer(serializers.ModelSerializer):
    """
    Read serializer, never exposes firebase_uid or any credential
    Used for list, retrieve, and responses after create/update
    """
    initials = serializers.SerializerMethodField()

    class Meta:
        model = ClinicStaff
        fields = [
            "staff_id",
            "clinic_id",
            "username",
            "full_name",
            "initials",
            "role",
            "is_active",
            "created_at",
        ]
        read_only_fields = fields

    def get_initials(self, obj):
        return obj.get_initials()


class ClinicStaffCreateSerializer(serializers.Serializer):
    """
    Serializer for staff provisioning.
    Accepts email + temporary password, calls Firebase, then
    creates the ClinicStaff row. The email becomes the Firebase
    credential
    """
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        min_length=10,
        help_text="Temporary password, staff should change this on first login"
    )
    username = serializers.CharField(max_length=50)
    full_name = serializers.CharField(max_length=200, required=False, default="")
    role = serializers.ChoiceField(choices=ClinicStaff.Role.choices)

    def validate_username(self, value):
        if ClinicStaff.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_email(self, value):
        """Check Firebase for duplicate email before attempting creation"""
        try:
            firebase_auth.get_user_by_email(value)
            raise serializers.ValidationError(
                "A Firebase account with this email already exists."
            )
        except firebase_auth.UserNotFoundError:
            return value

    def create(self, validated_data):
        """
          1. Create Firebase user, get uid
          2. Create ClinicStaff row with that uid
        If step 2 fails, step 1 is rolled back (Firebase user deleted)
        """
        clinic = self.context["clinic"]
        firebase_uid = None

        try:
            firebase_uid = create_firebase_user(
                email=validated_data["email"],
                password=validated_data["password"],
                display_name=validated_data.get("full_name") or validated_data["email"],
            )
            staff = ClinicStaff.objects.create(
                clinic=clinic,
                firebase_uid=firebase_uid,
                username=validated_data["username"],
                full_name=validated_data.get("full_name", ""),
                role=validated_data["role"],
            )
            return staff
        except Exception:
            # Roll back the Firebase user if the Django row creation failed
            if firebase_uid:
                delete_firebase_user(firebase_uid)
            raise


class ClinicStaffUpdateSerializer(serializers.ModelSerializer):
    """Update role only, username and firebase_uid are immutable"""
    class Meta:
        model = ClinicStaff
        fields = ["role"]

    def validate_role(self, value):
        if value not in [r[0] for r in ClinicStaff.Role.choices]:
            raise serializers.ValidationError(f"Invalid role: {value}")
        return value


class ClinicStaffStatusSerializer(serializers.ModelSerializer):
    """Handles activate/deactivate, also syncs state to Firebase"""
    class Meta:
        model = ClinicStaff
        fields = ["staff_id", "is_active"]
        read_only_fields = ["staff_id"]

    def validate(self, attrs):
        request = self.context["request"]
        staff = self.instance
        # Prevent a CA from deactivating themselves
        requester = getattr(request, "clinic_staff", None)
        if requester and requester.staff_id == staff.staff_id and not attrs.get("is_active", True):
            raise serializers.ValidationError(
                {"is_active": "You cannot deactivate your own account."}
            )
        return attrs

    def update(self, instance, validated_data):
        is_active = validated_data["is_active"]
        instance.is_active = is_active
        instance.save(update_fields=["is_active"])

        if is_active:
            reactivate_firebase_user(instance.firebase_uid)
        else:
            deactivate_firebase_user(instance.firebase_uid)
            revoke_firebase_tokens(instance.firebase_uid)

        return instance
