from django.urls import path
from . import views

urlpatterns = [
    path("", views.ClinicListCreateView.as_view()),
    path("<uuid:clinic_id>/", views.ClinicRetrieveUpdateView.as_view()),
    path("<uuid:clinic_id>/status/", views.ClinicStatusView.as_view()),
    path("<uuid:clinic_id>/staff/", views.StaffListCreateView.as_view()),
    path("<uuid:clinic_id>/staff/<uuid:staff_id>/", views.StaffRetrieveUpdateView.as_view()),
    path("<uuid:clinic_id>/staff/<uuid:staff_id>/status/", views.StaffStatusView.as_view()),
]
