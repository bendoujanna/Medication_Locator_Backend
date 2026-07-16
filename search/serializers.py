from rest_framework import serializers


class MedicationResultSerializer(serializers.Serializer):
    """
    The medication sub-object inside a search result card.
    inventory_id is included so the client can POST /hold-requests/
    without needing to know any other internal ID.
    """
    inventory_id = serializers.UUIDField()
    brand_name = serializers.CharField()
    dosage_form = serializers.CharField()
    strength = serializers.CharField()


class SearchResultSerializer(serializers.Serializer):
    """
    A single clinic result card returned by GET /search/.
    """
    clinic_id = serializers.UUIDField()
    clinic_name = serializers.CharField()
    address = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    distance_km = serializers.FloatField()
    operating_hours = serializers.CharField()
    medication = MedicationResultSerializer()
    traffic_light_status = serializers.CharField()
    hold_available = serializers.BooleanField()


class SubstituteResultSerializer(serializers.Serializer):
    """Result shape for GET /search/substitutes/"""
    clinic_id = serializers.UUIDField()
    clinic_name = serializers.CharField()
    address = serializers.CharField()
    distance_km = serializers.FloatField()
    medication = MedicationResultSerializer()
    traffic_light_status = serializers.CharField()
    hold_available = serializers.BooleanField()


class MapPinSerializer(serializers.Serializer):
    """
    Minimal payload for GET /search/map-pins/.
    """
    clinic_id = serializers.UUIDField()
    clinic_name = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    traffic_light_status = serializers.CharField()


class TransitTimeSerializer(serializers.Serializer):
    """Response shape for GET /routing/transit-time/"""
    mode = serializers.CharField()
    duration_seconds = serializers.IntegerField()
    duration_label = serializers.CharField()
    distance_km = serializers.FloatField()
