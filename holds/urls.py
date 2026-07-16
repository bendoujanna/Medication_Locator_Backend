from django.urls import path
from . import views

# Client-facing
urlpatterns = [
    path("", views.HoldRequestCreateView.as_view()),
    path("<uuid:request_id>/", views.HoldRequestStatusView.as_view()),
]

# Clinic-facing nested under /clinics/{clinic_id}/ in the root router
clinic_hold_urlpatterns = [
    path("", views.ClinicHoldRequestListView.as_view()),
    path("<uuid:request_id>/", views.HoldRequestProcessView.as_view()),
]
