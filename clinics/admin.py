from django.contrib import admin
from clinics.models import Clinic, ClinicStaff


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ["name", "address", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "address"]
    readonly_fields = ["clinic_id", "created_at"]
    ordering = ["name"]


@admin.register(ClinicStaff)
class ClinicStaffAdmin(admin.ModelAdmin):
    list_display = ["username", "full_name", "role", "clinic", "is_active", "created_at"]
    list_filter = ["role", "is_active", "clinic"]
    search_fields = ["username", "full_name", "firebase_uid"]
    readonly_fields = ["staff_id", "created_at"]  #add firebase_uid
    ordering = ["clinic", "username"]

    # firebase_uid is read-only for debugging provisioning issues
    fieldsets = [
        ("Identity", {"fields": ["staff_id", "username", "full_name", "firebase_uid"]}),
        ("Access", {"fields": ["clinic", "role", "is_active"]}),
        ("Meta", {"fields": ["created_at"]}),
    ]