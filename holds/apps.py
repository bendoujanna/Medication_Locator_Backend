from django.apps import AppConfig
import os

class HoldsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "holds"

    def ready(self):

        if os.environ.get("RUN_MAIN") != "true":
            from holds.tasks import start_scheduler
            start_scheduler()
