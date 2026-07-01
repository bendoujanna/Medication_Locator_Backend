import uuid
from django.db import models


class Clinic(models.Model):
    """
    Master record for a registered health facility.
    Created exclusively by a Superuser
    no public sign-up path exists.
    GPS coordinates are fed directly to Leaflet.js for
    map rendering on the Client Portal.
    """
    clinic_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=500)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text="GPS latitude — fed to Leaflet.js for map pin placement"
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text="GPS longitude — fed to Leaflet.js for map pin placement"
    )
    operating_hours = models.CharField(
        max_length=300,
        blank=True,
        help_text="Free-text schedule e.g. 'Mon–Fri 07:00–18:00, Sat 08:00–13:00'"
    )
    emergency_contact = models.CharField(
        max_length=20,
        blank=True,
        help_text="E.164 phone number e.g. '+250788123456'"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Inactive clinics are hidden from search results but not deleted"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "clinic"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ClinicStaff(models.Model):
    """
    Profile and role record for clinic portal staff.
    """

    class Role(models.TextChoices):
        ADMINISTRATOR = "ADMINISTRATOR", "Administrator"
        STANDARD_PHARMACIST = "STANDARD_PHARMACIST", "Standard Pharmacist"

    staff_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    clinic = models.ForeignKey(
        Clinic,
        on_delete=models.CASCADE,
        related_name="staff",
        help_text="The clinic this staff member belongs to"
    )
    firebase_uid = models.CharField(
        max_length=128,
        unique=True,
        help_text="Firebase Authentication UID — the link between this row and Firebase credentials"
    )
    username = models.CharField(
        max_length=50,
        unique=True,
        help_text="Display identifier shown in the dashboard UI"
    )
    full_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Display name for the staff accounts card in Admin Settings"
    )
    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.STANDARD_PHARMACIST
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive staff cannot authenticate — mirrored to Firebase via firebase_admin.auth.update_user(disabled=True)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "clinic_staff"
        ordering = ["username"]

    def __str__(self):
        return f"{self.username} ({self.get_role_display()}) — {self.clinic.name}"

    def is_administrator(self):
        return self.role == self.Role.ADMINISTRATOR

    def get_initials(self):
        """
        Returns up to 2 initials for the Avatar UI component.
        """
        parts = self.full_name.strip().split()
        return "".join(p[0].upper() for p in parts[:2]) if parts else self.username[:2].upper()
