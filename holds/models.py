import uuid
from datetime import timedelta
from django.db import models, transaction
from django.utils import timezone

from inventory.models import Inventory


class HoldRequest(models.Model):
    """
    A patient's temporary 2-hour reservation on a specific inventory item
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        DENIED = "DENIED", "Denied"
        EXPIRED = "EXPIRED", "Expired"

    request_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.CASCADE,
        related_name="hold_requests",
        help_text="The specific inventory record being held. CASCADE means holds are removed if the inventory record is deleted."
    )
    patient_contact = models.CharField(
        max_length=20,
        blank=True,
        help_text=(
            "E.164 phone number. WRITE-ONLY — never returned in any API response. "
            "Blanked by purge_phi() on resolution. Masked as '+250 78•• •567' if displayed in dashboard."
        )
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        help_text="Always set to requested_at + 2 hours. Calculated in save()."
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Stamped when status transitions to APPROVED, DENIED, or EXPIRED."
    )

    class Meta:
        db_table = "hold_request"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(
                fields=["status", "expires_at"],
                name="idx_status_expires"
            ),
        ]

    def save(self, *args, **kwargs):
        """
        Auto-calculates expires_at on first save only
        """
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=2)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def purge_phi(self):
        self.patient_contact = ""
        self.save(update_fields=["patient_contact"])

    def approve(self):
        if self.status != self.Status.PENDING:
            raise ValueError(f"Cannot approve a hold with status '{self.status}'.")
        if self.is_expired():
            raise ValueError("Cannot approve an expired hold request.")

        with transaction.atomic():
            self.inventory.decrement()       # raises ValueError if qty == 0
            self.status = self.Status.APPROVED
            self.resolved_at = timezone.now()
            self.save(update_fields=["status", "resolved_at"])

        self.purge_phi()

    def deny(self):
        """
        Denies the hold. Inventory quantity is unchanged.
        """
        if self.status != self.Status.PENDING:
            raise ValueError(f"Cannot deny a hold with status '{self.status}'.")

        self.status = self.Status.DENIED
        self.resolved_at = timezone.now()
        self.save(update_fields=["status", "resolved_at"])
        self.purge_phi()

    def get_masked_contact(self):
        p = self.patient_contact
        if not p or len(p) < 8:
            return ""
        country = p[:4]
        head = p[4:6]
        tail = p[-3:]
        return f"{country} {head}•• •{tail}"

    def __str__(self):
        return f"Hold {self.request_id} — {self.status} — {self.inventory}"
