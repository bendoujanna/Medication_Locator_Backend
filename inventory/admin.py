from django.contrib import admin
from inventory.models import Inventory, StockAlert


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = [
        "medication", "clinic", "quantity_on_hand",
        "low_stock_threshold", "status", "is_out_of_stock_override", "last_updated"
    ]
    list_filter = ["status", "clinic", "is_out_of_stock_override"]
    search_fields = ["medication__brand_name", "clinic__name"]
    readonly_fields = ["inventory_id", "status", "last_updated"]
    fieldsets = [
        ("Record", {"fields": ["inventory_id", "clinic", "medication"]}),
        ("Stock", {"fields": [
            "quantity_on_hand", "low_stock_threshold",
            "is_out_of_stock_override", "status"
        ]}),
        ("Timestamps", {"fields": ["last_updated"]}),
    ]


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = [
        "inventory", "alert_type", "quantity_at_trigger",
        "is_resolved", "triggered_at"
    ]
    list_filter = ["alert_type", "is_resolved"]
    search_fields = ["inventory__medication__brand_name", "inventory__clinic__name"]
    readonly_fields = ["alert_id", "triggered_at"]
    actions = ["mark_resolved"]

    @admin.action(description="Mark selected alerts as resolved")
    def mark_resolved(self, request, queryset):
        queryset.update(is_resolved=True)