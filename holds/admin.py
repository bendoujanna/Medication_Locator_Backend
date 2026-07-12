from django.contrib import admin
from holds.models import HoldRequest


@admin.register(HoldRequest)
class HoldRequestAdmin(admin.ModelAdmin):
    list_display = [
        "request_id", "get_medication", "get_clinic",
        "status", "requested_at", "expires_at", "resolved_at"
    ]
    list_filter = ["status"]
    search_fields = ["inventory__medication__brand_name", "inventory__clinic__name"]
    readonly_fields = [
        "request_id", "inventory", "patient_contact",
        "requested_at", "expires_at", "resolved_at"
    ]
    # patient_contact is shown read-only for audit purposes but will be blank once purge_phi() has run
    fieldsets = [
        ("Record", {"fields": ["request_id", "inventory"]}),
        ("Patient (PHI — purged on resolution)", {"fields": ["patient_contact"]}),
        ("Status", {"fields": ["status", "requested_at", "expires_at", "resolved_at"]}),
    ]

    @admin.display(description="Medication")
    def get_medication(self, obj):
        return obj.inventory.medication.brand_name

    @admin.display(description="Clinic")
    def get_clinic(self, obj):
        return obj.inventory.clinic.name