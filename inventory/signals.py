# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import Inventory, StockAlert
#
# @receiver(post_save, sender=Inventory)
# def create_stock_alert_on_low_stock(sender, instance, **kwargs):
#
#     if instance.status not in (Inventory.Status.LOW_STOCK, Inventory.Status.OUT_OF_STOCK):
#         return
#
#     alert_type = (
#         StockAlert.AlertType.OUT_OF_STOCK
#         if instance.status == Inventory.Status.OUT_OF_STOCK
#         else StockAlert.AlertType.LOW_STOCK
#     )
#
#     already_exists = StockAlert.objects.filter(
#         inventory=instance,
#         alert_type=alert_type,
#         is_resolved=False
#     ).exists()
#
#     if not already_exists:
#         StockAlert.objects.create(
#             inventory=instance,
#             alert_type=alert_type,
#             quantity_at_trigger=instance.quantity_on_hand
#         )

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Inventory, StockAlert

@receiver(post_save, sender=Inventory)
def manage_stock_alerts(sender, instance, **kwargs):
    """
    Intelligently manages stock alerts to ensure they perfectly match
    the current inventory status.
    """

    if instance.status == Inventory.Status.IN_STOCK:
        StockAlert.objects.filter(
            inventory=instance,
            is_resolved=False
        ).update(is_resolved=True)
        return

    target_alert_type = (
        StockAlert.AlertType.OUT_OF_STOCK
        if instance.status == Inventory.Status.OUT_OF_STOCK
        else StockAlert.AlertType.LOW_STOCK
    )

    StockAlert.objects.filter(
        inventory=instance,
        is_resolved=False
    ).exclude(
        alert_type=target_alert_type
    ).update(is_resolved=True)

    already_exists = StockAlert.objects.filter(
        inventory=instance,
        alert_type=target_alert_type,
        is_resolved=False
    ).exists()

    if not already_exists:
        StockAlert.objects.create(
            inventory=instance,
            alert_type=target_alert_type,
            quantity_at_trigger=instance.quantity_on_hand
        )