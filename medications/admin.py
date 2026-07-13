from django.contrib import admin
from medications.models import ActiveIngredient, Medication


@admin.register(ActiveIngredient)
class ActiveIngredientAdmin(admin.ModelAdmin):
    list_display = ["name", "symptom_category", "ems_reference_code"]
    search_fields = ["name", "symptom_category", "ems_reference_code"]
    readonly_fields = ["ingredient_id"]


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ["brand_name", "strength", "dosage_form", "ingredient"]
    list_filter = ["dosage_form", "ingredient__symptom_category"]
    search_fields = ["brand_name", "ingredient__name"]
    readonly_fields = ["medication_id"]
    autocomplete_fields = ["ingredient"]
