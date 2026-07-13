from rest_framework import serializers
from medications.models import ActiveIngredient, Medication


class ActiveIngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActiveIngredient
        fields = ["ingredient_id", "name", "symptom_category", "ems_reference_code"]
        read_only_fields = ["ingredient_id"]


class ActiveIngredientDetailSerializer(serializers.ModelSerializer):
    """Includes nested medications list — used for retrieve endpoint."""
    medications = serializers.SerializerMethodField()

    class Meta:
        model = ActiveIngredient
        fields = ["ingredient_id", "name", "symptom_category", "ems_reference_code", "medications"]
        read_only_fields = fields

    def get_medications(self, obj):
        return MedicationSerializer(obj.medications.all(), many=True).data


class MedicationSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(
        source="ingredient.name", read_only=True
    )
    symptom_category = serializers.CharField(
        source="ingredient.symptom_category", read_only=True
    )

    class Meta:
        model = Medication
        fields = [
            "medication_id",
            "brand_name",
            "dosage_form",
            "strength",
            "ingredient_id",
            "ingredient_name",
            "symptom_category",
        ]
        read_only_fields = ["medication_id", "ingredient_name", "symptom_category"]

    def validate_ingredient_id(self, value):
        if not ActiveIngredient.objects.filter(ingredient_id=value).exists():
            raise serializers.ValidationError(
                "This ingredient does not exist in the Essential Medicines List."
            )
        return value

    def validate(self, attrs):
        # unique_together check at serializer level for a clear error message
        brand = attrs.get("brand_name")
        ingredient = attrs.get("ingredient_id")
        form = attrs.get("dosage_form")
        if brand and ingredient and form:
            qs = Medication.objects.filter(
                brand_name=brand, ingredient_id=ingredient, dosage_form=form
            )
            if self.instance:
                qs = qs.exclude(medication_id=self.instance.medication_id)
            if qs.exists():
                raise serializers.ValidationError(
                    "This brand name + ingredient + dosage form combination already exists."
                )
        return attrs
