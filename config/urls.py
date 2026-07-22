from django.contrib import admin
from django.urls import path, include

from authentication.views import HealthCheckView
from clinics.urls import urlpatterns as clinic_urlpatterns
from inventory.urls import inventory_urlpatterns, alert_urlpatterns
from holds.urls import clinic_hold_urlpatterns
from medications.urls import urlpatterns as ingredient_urlpatterns, medication_urlpatterns
from holds.urls import urlpatterns as hold_urlpatterns
from search.urls import urlpatterns as search_urlpatterns, routing_urlpatterns

# All clinic-nested routes share the /api/v1/clinics/{clinic_id}/ prefix
clinic_nested = [
    path("inventory/", include(inventory_urlpatterns)),
    path("alerts/", include(alert_urlpatterns)),
    path("hold-requests/", include(clinic_hold_urlpatterns)),
    path("staff/", include("clinics.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),

    # Health check, used by UptimeRobot to keep Render.com warm
    path("api/v1/health/", HealthCheckView.as_view()),

    # Authentication, profile endpoint
    path("api/v1/auth/", include("authentication.urls")),

    # Ingredients (EML)
    path("api/v1/ingredients/", include(ingredient_urlpatterns)),

    # Medications
    path("api/v1/medications/", include(medication_urlpatterns)),

    # Clinics, base CRUD
    path("api/v1/clinics/", include(clinic_urlpatterns)),

    # Clinic-nested resources
    path("api/v1/clinics/<uuid:clinic_id>/", include(clinic_nested)),

    # Hold requests, client-facing (no auth)
    path("api/v1/hold-requests/", include(hold_urlpatterns)),

    # Search, public
    path("api/v1/search/", include(search_urlpatterns)),

    # Routing proxy, public
    path("api/v1/routing/", include(routing_urlpatterns)),
]
