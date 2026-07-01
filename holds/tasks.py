"""
Scheduled task: expire stale holds and purge PHI
"""
from django.utils import timezone


def expire_stale_holds():
    # Import inside the function to avoid circular imports at module load time.
    from apps.holds.models import HoldRequest

    now = timezone.now()
    stale_holds = HoldRequest.objects.filter(
        status=HoldRequest.Status.PENDING,
        expires_at__lte=now
    )

    expired_count = 0
    for hold in stale_holds:
        hold.status = HoldRequest.Status.EXPIRED
        hold.resolved_at = now
        hold.save(update_fields=["status", "resolved_at"])
        hold.purge_phi()
        expired_count += 1

    if expired_count:
        print(f"[HoldExpiry] Expired and purged PHI for {expired_count} hold(s) at {now:%Y-%m-%d %H:%M:%S} UTC")


def start_scheduler():

    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        expire_stale_holds,
        trigger=IntervalTrigger(minutes=5),
        id="expire_stale_holds",
        replace_existing=True
    )
    scheduler.start()
    print("[HoldExpiry] Scheduler started — running every 5 minutes.")
