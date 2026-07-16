import re
from rest_framework import serializers
from django.utils import timezone

from holds.models import HoldRequest
from inventory.models import Inventory


class HoldRequestCreateSerializer(serializers.Serializer):
    """
    Client-facing create serializer (POST /hold-requests/).
    No authentication required — public endpoint.
    patient_contact is write-only: stored in the model but never
    returned in any response.
    """
    inventory_id = serializers.UUIDField()
    patient_contact = serializers.CharField(max_length=20)

    def validate_inventory_id(self, value):
        try:
            inv = Inventory.objects.select_related("clinic", "medication").get(
                inventory_id=value
            )
        except Inventory.DoesNotExist:
            raise serializers.ValidationError("Inventory record not found.")

        if inv.status == Inventory.Status.OUT_OF_STOCK:
            raise serializers.ValidationError(
                "This medicine is currently out of stock and cannot be held."
            )
        self._inventory = inv
        return value

    def validate_patient_contact(self, value):
        if not re.match(r"^\+[1-9]\d{7,14}$", value):
            raise serializers.ValidationError(
                "Enter a valid phone number in international format e.g. +250781234567"
            )
        return value

    def create(self, validated_data):
        inventory = getattr(self, "_inventory", None) or \
            Inventory.objects.get(inventory_id=validated_data["inventory_id"])
        hold = HoldRequest.objects.create(
            inventory=inventory,
            patient_contact=validated_data["patient_contact"],
        )
        return hold


class HoldRequestPublicSerializer(serializers.ModelSerializer):
    """
    Read serializer for the client polling endpoint.
    Deliberately excludes patient_contact — it is write-only.
    Also exposes clinic_name and medication_name for the Pending screen UI.
    """
    clinic_name = serializers.CharField(
        source="inventory.clinic.name", read_only=True
    )
    medication_name = serializers.SerializerMethodField()
    address = serializers.CharField(
        source="inventory.clinic.address", read_only=True
    )

    class Meta:
        model = HoldRequest
        fields = [
            "request_id",
            "inventory_id",
            "clinic_name",
            "medication_name",
            "address",
            "status",
            "requested_at",
            "expires_at",
            "resolved_at",
        ]
        read_only_fields = fields

    def get_medication_name(self, obj):
        return obj.inventory.medication.get_full_name()


class HoldRequestClinicSerializer(serializers.ModelSerializer):
    """
    Clinic-side serializer for the hold request inbox.
    Shows the masked phone number, never the raw patient_contact.
    """
    patient_contact_masked = serializers.SerializerMethodField()
    medication_name = serializers.SerializerMethodField()
    dosage_label = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = HoldRequest
        fields = [
            "request_id",
            "inventory_id",
            "medication_name",
            "dosage_label",
            "patient_contact_masked",
            "status",
            "requested_at",
            "expires_at",
            "resolved_at",
            "time_ago",
        ]
        read_only_fields = fields

    def get_patient_contact_masked(self, obj):
        return obj.get_masked_contact()

    def get_medication_name(self, obj):
        return obj.inventory.medication.brand_name

    def get_dosage_label(self, obj):
        med = obj.inventory.medication
        return f"{med.get_dosage_form_display()} · {med.strength}"

    def get_time_ago(self, obj):
        diff = timezone.now() - obj.requested_at
        minutes = int(diff.total_seconds() // 60)
        if minutes < 1:
            return "just now"
        if minutes < 60:
            return f"{minutes} min ago"
        hours = minutes // 60
        return f"{hours} hr{'s' if hours > 1 else ''} ago"


class HoldRequestProcessSerializer(serializers.Serializer):
    """
    Serializer for the approve/deny action (PATCH).
    Calls the model's approve() or deny() method which handles
    the atomic transaction internally.
    """
    action = serializers.ChoiceField(choices=["APPROVE", "DENY"])

    def update(self, instance, validated_data):
        action = validated_data["action"]
        if action == "APPROVE":
            instance.approve()
        else:
            instance.deny()
        instance.refresh_from_db()
        return instance