from django.urls import path
from . import views

inventory_urlpatterns = [
    path("", views.InventoryListCreateView.as_view()),
    path("<uuid:inventory_id>/", views.InventoryRetrieveUpdateDeleteView.as_view()),
    path("<uuid:inventory_id>/threshold/", views.ThresholdUpdateView.as_view()),
]

alert_urlpatterns = [
    path("", views.StockAlertListView.as_view()),
    path("<uuid:alert_id>/resolve/", views.StockAlertResolveView.as_view()),
]
