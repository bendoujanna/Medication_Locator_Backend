from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.core.exceptions import ValidationError
from authentication.firebase import FirebaseAuthentication
from authentication.permissions import IsClinicStaff, IsSuperuser
from medications.models import ActiveIngredient, Medication
from medications.serializers import (
    ActiveIngredientSerializer,
    ActiveIngredientDetailSerializer,
    MedicationSerializer,
)


class IngredientListCreateView(APIView):
    """
    GET  /ingredients/  — public, used by search dropdowns
    POST /ingredients/  — Superuser only (EML management)
    """
    authentication_classes = [FirebaseAuthentication]

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsSuperuser()]

    def get(self, request):
        qs = ActiveIngredient.objects.all()
        search = request.query_params.get("search")
        category = request.query_params.get("symptom_category")
        if search:
            qs = qs.filter(name__icontains=search)
        if category:
            qs = qs.filter(symptom_category__iexact=category)
        serializer = ActiveIngredientSerializer(qs, many=True)
        return Response({"count": qs.count(), "results": serializer.data})

    def post(self, request):
        serializer = ActiveIngredientSerializer(data=request.data)
        if serializer.is_valid():
            ingredient = serializer.save()
            return Response(
                ActiveIngredientSerializer(ingredient).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IngredientRetrieveUpdateView(APIView):
    authentication_classes = [FirebaseAuthentication]

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsSuperuser()]

    def get_object(self, ingredient_id):
        try:
            return ActiveIngredient.objects.get(ingredient_id=ingredient_id)
        except (ActiveIngredient.DoesNotExist, ValidationError):
            return None

    def get(self, request, ingredient_id):
        ingredient = self.get_object(ingredient_id)
        if not ingredient:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Ingredient not found.", "field": None}},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(ActiveIngredientDetailSerializer(ingredient).data)

    def patch(self, request, ingredient_id):
        ingredient = self.get_object(ingredient_id)
        if not ingredient:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Ingredient not found.", "field": None}},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ActiveIngredientSerializer(ingredient, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MedicationListCreateView(APIView):
    """
    GET  /medications/  — public
    POST /medications/  — authenticated clinic staff
    """
    authentication_classes = [FirebaseAuthentication]

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsClinicStaff()]

    def get(self, request):
        qs = Medication.objects.select_related("ingredient").all()
        search = request.query_params.get("search")
        ingredient_id = request.query_params.get("ingredient_id")
        dosage_form = request.query_params.get("dosage_form")
        if search:
            qs = qs.filter(brand_name__icontains=search)
        if ingredient_id:
            qs = qs.filter(ingredient_id=ingredient_id)
        if dosage_form:
            qs = qs.filter(dosage_form__iexact=dosage_form)
        serializer = MedicationSerializer(qs, many=True)
        return Response({"count": qs.count(), "results": serializer.data})

    def post(self, request):
        serializer = MedicationSerializer(data=request.data)
        if serializer.is_valid():
            medication = serializer.save()
            return Response(
                MedicationSerializer(medication).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MedicationRetrieveUpdateView(APIView):
    authentication_classes = [FirebaseAuthentication]

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsClinicStaff()]

    def get_object(self, medication_id):
        try:
            return Medication.objects.select_related("ingredient").get(
                medication_id=medication_id
            )
        except (Medication.DoesNotExist, ValidationError):
            return None

    def get(self, request, medication_id):
        medication = self.get_object(medication_id)
        if not medication:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Medication not found.", "field": None}},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(MedicationSerializer(medication).data)

    def patch(self, request, medication_id):
        medication = self.get_object(medication_id)
        if not medication:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Medication not found.", "field": None}},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = MedicationSerializer(medication, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)