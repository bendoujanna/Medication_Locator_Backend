from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.core.exceptions import ValidationError
from clinics.models import Clinic
from inventory.models import Inventory
from medications.models import ActiveIngredient, Medication
from search.utils import haversine_km, eta_label, get_osrm_transit
from search.serializers import (
    SearchResultSerializer,
    SubstituteResultSerializer,
    MapPinSerializer,
    TransitTimeSerializer,
)


def _build_result(inventory, clinic, lat, lng):
    """
    Constructs a single search result dict from an Inventory record
    """
    distance = haversine_km(lat, lng, clinic.latitude, clinic.longitude)
    med = inventory.medication
    return {
        "clinic_id": clinic.clinic_id,
        "clinic_name": clinic.name,
        "address": clinic.address,
        "latitude": clinic.latitude,
        "longitude": clinic.longitude,
        "distance_km": distance,
        "operating_hours": clinic.operating_hours,
        "medication": {
            "inventory_id": inventory.inventory_id,
            "brand_name": med.brand_name,
            "dosage_form": med.get_dosage_form_display(),
            "strength": med.strength,
        },
        "traffic_light_status": inventory.status,
        "hold_available": inventory.status != Inventory.Status.OUT_OF_STOCK,
    }


class MedicationSearchView(APIView):
    """
    GET /search/
    Matches against:
       Medication brand name (e.g. "Doliprane")
       Active ingredient name (e.g. "Paracetamol")
       Symptom category (e.g. "Analgesic")
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        lat = request.query_params.get("lat")
        lng = request.query_params.get("lng")
        sector = request.query_params.get("sector")
        radius_km = float(request.query_params.get("radius_km", 10))
        limit = min(int(request.query_params.get("limit", 10)), 30)

        if not query:
            return Response(
                {"error": {"code": "MISSING_QUERY", "message": "Search query 'q' is required.", "field": "q"}},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not ((lat and lng) or sector):
            return Response(
                {"error": {"code": "MISSING_LOCATION", "message": "Provide 'lat' and 'lng', or 'sector'.", "field": None}},
                status=status.HTTP_400_BAD_REQUEST
            )

        if lat and lng:
            try:
                lat, lng = float(lat), float(lng)
            except ValueError:
                return Response(
                    {"error": {"code": "INVALID_COORDINATES", "message": "lat and lng must be valid numbers.", "field": None}},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            lat, lng = -1.9441, 30.0619

        q = query.lower()

        matched_ingredient = None

        # Try ingredient name match
        ingredient_match = ActiveIngredient.objects.filter(name__icontains=q).first()
        if not ingredient_match:
            # Try symptom category match
            ingredient_match = ActiveIngredient.objects.filter(
                symptom_category__icontains=q
            ).first()

        if ingredient_match:
            matched_ingredient = ingredient_match
            medication_ids = list(
                ingredient_match.medications.values_list("medication_id", flat=True)
            )
        else:
            # Direct brand name match
            medications = Medication.objects.filter(brand_name__icontains=q)
            medication_ids = list(medications.values_list("medication_id", flat=True))
            if medications.exists():
                # Grab the ingredient from the first match for substitutes flag
                matched_ingredient = medications.first().ingredient

        if not medication_ids:
            return Response(
                {"error": {"code": "NO_RESULTS", "message": f"No medicines matching '{query}' found.", "field": None}},
                status=status.HTTP_404_NOT_FOUND
            )

        # fetch matching inventory within radius, only active clinics
        inventory_qs = (
            Inventory.objects
            .select_related("clinic", "medication", "medication__ingredient")
            .filter(
                medication_id__in=medication_ids,
                clinic__is_active=True,
            )
        )

        # build results, filter by radius, sort by distance
        results = []
        for inv in inventory_qs:
            clinic = inv.clinic
            distance = haversine_km(lat, lng, clinic.latitude, clinic.longitude)
            if distance <= radius_km:
                results.append(_build_result(inv, clinic, lat, lng))

        results.sort(key=lambda r: r["distance_km"])
        results = results[:limit]

        # substitutes_available = True when there ARE results but ALL are OUT_OF_STOCK
        all_out = results and all(
            r["traffic_light_status"] == Inventory.Status.OUT_OF_STOCK
            for r in results
        )

        return Response({
            "query": query,
            "matched_ingredient": (
                {"ingredient_id": matched_ingredient.ingredient_id, "name": matched_ingredient.name}
                if matched_ingredient else None
            ),
            "results": results,
            "substitutes_available": bool(all_out),
        })


class SmartSubstituteView(APIView):
    """
    GET /search/substitutes/
    Smart Substitute engine
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        ingredient_id = request.query_params.get("ingredient_id")
        lat = request.query_params.get("lat")
        lng = request.query_params.get("lng")
        exclude_medication_id = request.query_params.get("exclude_medication_id")
        radius_km = float(request.query_params.get("radius_km", 10))

        if not ingredient_id:
            return Response(
                {"error": {"code": "MISSING_PARAM", "message": "'ingredient_id' is required.", "field": "ingredient_id"}},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            lat, lng = float(lat), float(lng)
        except (TypeError, ValueError):
            lat, lng = -1.9441, 30.0619  # Kigali fallback

        try:
            ingredient = ActiveIngredient.objects.get(ingredient_id=ingredient_id)
        except (ActiveIngredient.DoesNotExist, ValidationError):  # Catch malformed UUIDs
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Ingredient not found.", "field": "ingredient_id"}},
                status=status.HTTP_404_NOT_FOUND
            )

        # All medications sharing this ingredient, excluding the originally searched one
        substitute_med_ids = ingredient.medications.values_list("medication_id", flat=True)
        if exclude_medication_id:
            substitute_med_ids = substitute_med_ids.exclude(
                medication_id=exclude_medication_id
            )

        # Only in-stock or low-stock inventory — never surface out-of-stock substitutes
        inventory_qs = (
            Inventory.objects
            .select_related("clinic", "medication")
            .filter(
                medication_id__in=substitute_med_ids,
                clinic__is_active=True,
            )
            .exclude(status=Inventory.Status.OUT_OF_STOCK)
        )

        substitutes = []
        for inv in inventory_qs:
            distance = haversine_km(lat, lng, inv.clinic.latitude, inv.clinic.longitude)
            if distance <= radius_km:
                result = _build_result(inv, inv.clinic, lat, lng)
                # Substitute results don't need operating_hours or lat/lng
                substitutes.append({
                    "clinic_id": result["clinic_id"],
                    "clinic_name": result["clinic_name"],
                    "address": result["address"],
                    "distance_km": result["distance_km"],
                    "medication": result["medication"],
                    "traffic_light_status": result["traffic_light_status"],
                    "hold_available": result["hold_available"],
                })

        substitutes.sort(key=lambda r: r["distance_km"])

        return Response({
            "ingredient_name": ingredient.name,
            "substitutes": substitutes,
        })


class MapPinsView(APIView):
    """
    GET /search/map-pins/
    Returns a minimal payload of clinic pins for Leaflet.js rendering.
    Runs the same search logic as MedicationSearchView but returns
    only the fields Leaflet needs — optimized for 3G (NFR 1).
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        lat = float(request.query_params.get("lat", -1.9441))
        lng = float(request.query_params.get("lng", 30.0619))
        radius_km = float(request.query_params.get("radius_km", 10))

        q = query.lower()
        ingredient = ActiveIngredient.objects.filter(name__icontains=q).first()
        if ingredient:
            medication_ids = ingredient.medications.values_list("medication_id", flat=True)
        else:
            medication_ids = Medication.objects.filter(
                brand_name__icontains=q
            ).values_list("medication_id", flat=True)

        inventory_qs = (
            Inventory.objects
            .select_related("clinic")
            .filter(medication_id__in=medication_ids, clinic__is_active=True)
        )

        pins = []
        seen_clinics = set()
        for inv in inventory_qs:
            clinic = inv.clinic
            if clinic.clinic_id in seen_clinics:
                continue
            distance = haversine_km(lat, lng, clinic.latitude, clinic.longitude)
            if distance <= radius_km:
                pins.append({
                    "clinic_id": clinic.clinic_id,
                    "clinic_name": clinic.name,
                    "latitude": clinic.latitude,
                    "longitude": clinic.longitude,
                    "traffic_light_status": inv.status,
                })
                seen_clinics.add(clinic.clinic_id)

        return Response({"pins": pins})


class TransitTimeView(APIView):
    """
    GET /routing/transit-time/
    Thin proxy to OSRM
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            from_lat = float(request.query_params["from_lat"])
            from_lng = float(request.query_params["from_lng"])
            to_lat = float(request.query_params["to_lat"])
            to_lng = float(request.query_params["to_lng"])
        except (KeyError, ValueError):
            return Response(
                {"error": {"code": "MISSING_PARAMS", "message": "from_lat, from_lng, to_lat, to_lng are all required.", "field": None}},
                status=status.HTTP_400_BAD_REQUEST
            )

        mode = request.query_params.get("mode", "driving")
        if mode not in ("driving", "walking"):
            mode = "driving"

        result = get_osrm_transit(from_lat, from_lng, to_lat, to_lng, mode)
        return Response(result)
