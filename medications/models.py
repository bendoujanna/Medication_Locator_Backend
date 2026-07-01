import uuid
from django.db import models


class ActiveIngredient(models.Model):
    """
    This table is seeded once at setup via the seed_eml management command
    and is read-only for all clinic staff. Only Superusers can modify it
    """
    ingredient_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(
        max_length=200,
        unique=True,
        help_text="Standardized INN (International Nonproprietary Name) e.g. 'Paracetamol'"
    )
    symptom_category = models.CharField(
        max_length=100,
        help_text="Clinical category e.g. 'Analgesic', 'Antibiotic', 'Antimalarial'"
    )
    ems_reference_code = models.CharField(
        max_length=50,
        blank=True,
        help_text="MSF Essential Medicines List reference code"
    )

    class Meta:
        db_table = "active_ingredient"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_substitute_medications(self):
        return self.medications.all()


class Medication(models.Model):
    """
    Brand-name drugs. Each must be linked to an ActiveIngredient via FK
    """

    class DosageForm(models.TextChoices):
        TABLET = "TABLET", "Tablet"
        CAPSULE = "CAPSULE", "Capsule"
        SYRUP = "SYRUP", "Syrup"
        INJECTION = "INJECTION", "Injection"
        CREAM = "CREAM", "Cream"
        DROPS = "DROPS", "Drops"
        SACHET = "SACHET", "Sachet"
        OTHER = "OTHER", "Other"

    medication_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    ingredient = models.ForeignKey(
        ActiveIngredient,
        on_delete=models.PROTECT,
        related_name="medications",
        help_text="The standardized active ingredient this brand is built on. PROTECT prevents deleting an ingredient that has medications registered against it."
    )
    brand_name = models.CharField(
        max_length=200,
        help_text="Local brand name e.g. 'Doliprane', 'Panadol'"
    )
    dosage_form = models.CharField(
        max_length=20,
        choices=DosageForm.choices
    )
    strength = models.CharField(
        max_length=100,
        help_text="e.g. '500mg', '250mg/5ml', 'Standard'"
    )

    class Meta:
        db_table = "medication"
        ordering = ["brand_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["ingredient", "brand_name", "dosage_form"],
                name="unique_medication_packaging"
            )
        ]

    def __str__(self):
        return f"{self.brand_name} {self.strength} ({self.get_dosage_form_display()})"

    def get_full_name(self):
        return f"{self.brand_name} {self.strength} ({self.get_dosage_form_display()})"
