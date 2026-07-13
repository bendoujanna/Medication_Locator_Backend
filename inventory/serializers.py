from rest_framework import serializers
from inventory.models import Inventory, StockAlert
from medications.serializers import MedicationSerializer


class InventorySerializer(serializers.ModelSerializer):
    medication = MedicationSerializer(read_only=True)
    medication_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Inventory
        fields = [
            "inventory_id",
            "clinic_id",
            "medication",
            "medication_id",
            "quantity_on_hand",
            "low_stock_threshold",
            "status",
            "is_out_of_stock_override",
            "last_updated",
        ]
        read_only_fields = [
            "inventory_id",
            "clinic_id",
            "status",
            "last_updated",
            "medication",
        ]

    def validate_quantity_on_hand(self, value):
        if value < 0:
            raise serializers.ValidationError("Quantity cannot be negative.")
        return value

    def validate_medication_id(self, value):
        from medications.models import Medication
        if not Medication.objects.filter(medication_id=value).exists():
            raise serializers.ValidationError("Medication not found.")
        return value

    def validate(self, attrs):
        # unique_together check for clinic + medication
        if self.instance is None:  # only on create
            clinic = self.context["clinic"]
            medication_id = attrs.get("medication_id")
            if Inventory.objects.filter(
                clinic=clinic, medication_id=medication_id
            ).exists():
                raise serializers.ValidationError(
                    "This medication is already tracked for this clinic."
                )
        return attrs

    def create(self, validated_data):
        clinic = self.context["clinic"]
        return Inventory.objects.create(clinic=clinic, **validated_data)


class InventoryUpdateSerializer(serializers.ModelSerializer):
    """
    Partial update serializer for the quick-toggle +/- and override switch.
    status is always recomputed by Inventory.save() — never accepted as input.
    """
    class Meta:
        model = Inventory
        fields = [
            "quantity_on_hand",
            "is_out_of_stock_override",
        ]

    def validate_quantity_on_hand(self, value):
        if value < 0:
            raise serializers.ValidationError("Quantity cannot be negative.")
        return value


class ThresholdSerializer(serializers.ModelSerializer):
    """Dedicated serializer for the threshold configuration endpoint (FR 4.2)."""
    class Meta:
        model = Inventory
        fields = ["inventory_id", "low_stock_threshold", "status"]
        read_only_fields = ["inventory_id", "status"]

    def validate_low_stock_threshold(self, value):
        if value < 1:
            raise serializers.ValidationError("Threshold must be at least 1.")
        return value


class StockAlertSerializer(serializers.ModelSerializer):
    medication_name = serializers.CharField(
        source="inventory.medication.brand_name", read_only=True
    )
    low_stock_threshold = serializers.IntegerField(
        source="inventory.low_stock_threshold", read_only=True
    )

    class Meta:
        model = StockAlert
        fields = [
            "alert_id",
            "inventory_id",
            "medication_name",
            "alert_type",
            "quantity_at_trigger",
            "low_stock_threshold",
            "is_resolved",
            "triggered_at",
        ]
        read_only_fields = fields
