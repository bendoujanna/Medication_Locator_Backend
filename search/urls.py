from django.urls import path
from . import views

urlpatterns = [
    path("", views.MedicationSearchView.as_view()),
    path("substitutes/", views.SmartSubstituteView.as_view()),
    path("map-pins/", views.MapPinsView.as_view()),
]

routing_urlpatterns = [
    path("transit-time/", views.TransitTimeView.as_view()),
]
