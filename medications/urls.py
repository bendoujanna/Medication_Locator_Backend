from django.urls import path
from . import views

urlpatterns = [
    path("", views.IngredientListCreateView.as_view()),
    path("<uuid:ingredient_id>/", views.IngredientRetrieveUpdateView.as_view()),
]

medication_urlpatterns = [
    path("", views.MedicationListCreateView.as_view()),
    path("<uuid:medication_id>/", views.MedicationRetrieveUpdateView.as_view()),
]
