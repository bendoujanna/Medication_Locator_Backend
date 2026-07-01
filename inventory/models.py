import uuid
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import F
from clinics.models import Clinic
from medications.models import Medication


class Inventory(models.Model):
    """
    The operational core of the system
    """

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        LOW_STOCK = "LOW_STOCK", "Low Stock"
        OUT_OF_STOCK = "OUT_OF_STOCK", "Out of Stock"

    inventory_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    clinic = models.ForeignKey(
        Clinic,
        on_delete=models.CASCADE,
        related_name="inventory"
    )
    medication = models.ForeignKey(
        Medication,
        on_delete=models.PROTECT,
        related_name="inventory",
        help_text="PROTECT prevents deleting a medication that is actively tracked in inventory"
    )
    quantity_on_hand = models.PositiveIntegerField(
        default=0,
        help_text="Current physical units in stock. NEVER exposed to client-facing endpoints."
    )
    low_stock_threshold = models.PositiveIntegerField(
        default=10,
        help_text="A StockAlert fires when quantity_on_hand drops to or below this value (FR 4.2)"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OUT_OF_STOCK,
        editable=False,
        help_text="Computed automatically on every save — never set directly by serializers"
    )
    is_out_of_stock_override = models.BooleanField(
        default=False,
        help_text="Master toggle (FR 3.2). When True, forces status to OUT_OF_STOCK regardless of quantity_on_hand."
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        help_text="Auto-stamped on every save — used by the dashboard 'Last updated N min ago' display"
    )

    class Meta:
        db_table = "inventory"
        # One record per medication per clinic — enforced at DB level
        ordering = ["medication__brand_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["clinic", "medication"],
                name="unique_clinic_medication"
            )
        ]

    def compute_status(self):
        if self.is_out_of_stock_override:
            return self.Status.OUT_OF_STOCK
        if self.quantity_on_hand == 0:
            return self.Status.OUT_OF_STOCK
        if self.quantity_on_hand <= self.low_stock_threshold:
            return self.Status.LOW_STOCK
        return self.Status.AVAILABLE

    def save(self, *args, **kwargs):

        self.status = self.compute_status()
        super().save(*args, **kwargs)

    def decrement(self):

        if self.quantity_on_hand <= 0:
            raise ValueError(
                f"Cannot decrement {self.medication.brand_name} — quantity is already 0."
            )
        self.quantity_on_hand -= 1
        self.save()

    def __str__(self):
        return (
            f"{self.medication.brand_name} @ {self.clinic.name} "
            f"— {self.status} ({self.quantity_on_hand} units)"
        )


class StockAlert(models.Model):

    class AlertType(models.TextChoices):
        LOW_STOCK = "LOW_STOCK", "Low Stock"
        OUT_OF_STOCK = "OUT_OF_STOCK", "Out of Stock"

    alert_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.CASCADE,
        related_name="alerts"
    )
    staff = models.ForeignKey(
        "clinics.ClinicStaff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alerts",
        help_text="The staff member this alert is targeted at. Null = broadcast to all clinic staff."
    )
    alert_type = models.CharField(
        max_length=20,
        choices=AlertType.choices
    )
    quantity_at_trigger = models.PositiveIntegerField(
        help_text="Snapshot of quantity_on_hand at the exact moment the alert fired"
    )
    is_resolved = models.BooleanField(default=False)
    triggered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "stock_alert"
        ordering = ["-triggered_at"]

    def resolve(self):
        """Marks the alert as acknowledged by staff."""
        self.is_resolved = True
        self.save(update_fields=["is_resolved"])

    def __str__(self):
        return (
            f"{self.get_alert_type_display()} — "
            f"{self.inventory.medication.brand_name} @ {self.inventory.clinic.name} "
            f"— {self.triggered_at:%Y-%m-%d %H:%M}"
        )

