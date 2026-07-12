from django.apps import AppConfig


class HoldsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "holds"

    def ready(self):
        """
        Start the background scheduler when Django finishes booting.
        The scheduler runs expire_stale_holds() every 5 minutes.
        """
        import os
        if os.environ.get("RUN_MAIN") != "true":
            from holds.tasks import start_scheduler
            start_scheduler()
