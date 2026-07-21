from django.core.management.base import BaseCommand
from medications.models import ActiveIngredient, Medication


class Command(BaseCommand):
    help = "Seeds the database with MSF Essential Medicines linked to realistic East African commercial brands"

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding East African Commercial Medications...")

        ingredients_data = [
            # Antibacterials & Antifungals
            {"name": "Amoxicillin", "symptom_category": "Penicillin antibacterial"},
            {"name": "Azithromycin", "symptom_category": "Macrolide antibacterial"},
            {"name": "Ceftriaxone", "symptom_category": "Third-generation cephalosporin antibacterial"},
            {"name": "Ciprofloxacin", "symptom_category": "Fluoroquinolone antibacterial"},
            {"name": "Clarithromycin", "symptom_category": "Macrolide antibacterial"},
            {"name": "Metronidazole", "symptom_category": "Antiprotozoal, antibacterial (group of nitroimidazoles)"},
            {"name": "Fluconazole", "symptom_category": "Antifungal"},
            {"name": "Griseofulvin", "symptom_category": "Antifungal"},

            # Antimalarials & Anthelminthics
            {"name": "Albendazole", "symptom_category": "Anthelminthic"},
            {"name": "Artemether / Lumefantrine", "symptom_category": "Antimalarial"},
            {"name": "Mebendazole", "symptom_category": "Anthelminthic"},

            # Analgesics & Anti-inflammatories
            {"name": "Acetylsalicylic acid",
             "symptom_category": "Analgesic, antipyretic, non steroidal anti-inflammatory (NSAID)"},
            {"name": "Ibuprofen",
             "symptom_category": "Analgesic, antipyretic, non-steroidal anti-inflammatory (NSAID)"},
            {"name": "Paracetamol", "symptom_category": "Analgesic, antipyretic"},
            {"name": "Diclofenac", "symptom_category": "Non-steroidal anti-inflammatory drug (NSAID)"},

            # Cardiovascular & Antidiabetics
            {"name": "Amlodipine", "symptom_category": "Antihypertensive vasodilator (calcium channel blocker)"},
            {"name": "Enalapril", "symptom_category": "Angiotensin converting enzyme inhibitor (ACE)"},
            {"name": "Glibenclamide", "symptom_category": "Sulfonylurea antidiabetic"},
            {"name": "Metformin", "symptom_category": "Biguanide antidiabetic"},

            # Gastrointestinal & Respiratory
            {"name": "Omeprazole", "symptom_category": "Antiulcer and gastric antisecretory agent"},
            {"name": "Loperamide", "symptom_category": "Opioid antidiarrhoeal"},
            {"name": "Salbutamol", "symptom_category": "Short-acting beta-2 agonist bronchodilator"},

            # Vitamins & Supplements
            {"name": "Ferrous salts / Folic acid", "symptom_category": "Antianaemia drug"},
        ]

        ingredient_objects = {}
        for item in ingredients_data:
            ingredient, created = ActiveIngredient.objects.get_or_create(
                name=item["name"],
                defaults={
                    "symptom_category": item["symptom_category"],
                    "ems_reference_code": ""
                }
            )
            ingredient_objects[item["name"]] = ingredient
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created Ingredient: {ingredient.name}"))

        medications_data = [
            {"brand": "Panadol", "strength": "500 mg", "form": "TABLET", "ingredient": "Paracetamol"},
            {"brand": "Mara Pan", "strength": "500 mg", "form": "TABLET", "ingredient": "Paracetamol"},
            {"brand": "Action", "strength": "500 mg", "form": "TABLET", "ingredient": "Paracetamol"},
            {"brand": "Calpol", "strength": "120 mg/5 ml", "form": "SYRUP", "ingredient": "Paracetamol"},
            {"brand": "Panadol Baby", "strength": "120 mg/5 ml", "form": "SYRUP", "ingredient": "Paracetamol"},

            {"brand": "Coartem", "strength": "20 mg/120 mg", "form": "TABLET",
             "ingredient": "Artemether / Lumefantrine"},
            {"brand": "Lonart", "strength": "20 mg/120 mg", "form": "TABLET",
             "ingredient": "Artemether / Lumefantrine"},
            {"brand": "Lumartem", "strength": "20 mg/120 mg", "form": "TABLET",
             "ingredient": "Artemether / Lumefantrine"},

            {"brand": "Amoxil", "strength": "500 mg", "form": "CAPSULE", "ingredient": "Amoxicillin"},
            {"brand": "Ospamox", "strength": "250 mg/5 ml", "form": "SYRUP", "ingredient": "Amoxicillin"},
            {"brand": "Zithromax", "strength": "500 mg", "form": "TABLET", "ingredient": "Azithromycin"},
            {"brand": "Cipro", "strength": "500 mg", "form": "TABLET", "ingredient": "Ciprofloxacin"},
            {"brand": "Ciprobay", "strength": "500 mg", "form": "TABLET", "ingredient": "Ciprofloxacin"},
            {"brand": "Rocephin", "strength": "1 g", "form": "INJECTION", "ingredient": "Ceftriaxone"},
            {"brand": "Flagyl", "strength": "400 mg", "form": "TABLET", "ingredient": "Metronidazole"},
            {"brand": "Flagyl", "strength": "200 mg/5 ml", "form": "SYRUP", "ingredient": "Metronidazole"},
            {"brand": "Klacid", "strength": "500 mg", "form": "TABLET", "ingredient": "Clarithromycin"},

            {"brand": "Brufen", "strength": "400 mg", "form": "TABLET", "ingredient": "Ibuprofen"},
            {"brand": "Aspirin", "strength": "300 mg", "form": "TABLET", "ingredient": "Acetylsalicylic acid"},
            {"brand": "Voltaren", "strength": "50 mg", "form": "TABLET", "ingredient": "Diclofenac"},
            {"brand": "Diclofen", "strength": "50 mg", "form": "TABLET", "ingredient": "Diclofenac"},

            {"brand": "Zentel", "strength": "400 mg", "form": "TABLET", "ingredient": "Albendazole"},
            {"brand": "Vermox", "strength": "100 mg", "form": "TABLET", "ingredient": "Mebendazole"},

            {"brand": "Losec", "strength": "20 mg", "form": "CAPSULE", "ingredient": "Omeprazole"},
            {"brand": "Omez", "strength": "20 mg", "form": "CAPSULE", "ingredient": "Omeprazole"},
            {"brand": "Imodium", "strength": "2 mg", "form": "CAPSULE", "ingredient": "Loperamide"},

            {"brand": "Diflucan", "strength": "150 mg", "form": "CAPSULE", "ingredient": "Fluconazole"},
            {"brand": "Grisovin", "strength": "125 mg", "form": "TABLET", "ingredient": "Griseofulvin"},

            {"brand": "Norvasc", "strength": "5 mg", "form": "TABLET", "ingredient": "Amlodipine"},
            {"brand": "Renitec", "strength": "5 mg", "form": "TABLET", "ingredient": "Enalapril"},
            {"brand": "Glucophage", "strength": "500 mg", "form": "TABLET", "ingredient": "Metformin"},
            {"brand": "Daonil", "strength": "5 mg", "form": "TABLET", "ingredient": "Glibenclamide"},

            {"brand": "Ventolin", "strength": "100 mcg/puff", "form": "OTHER", "ingredient": "Salbutamol"},

            {"brand": "Fefol", "strength": "Standard", "form": "TABLET", "ingredient": "Ferrous salts / Folic acid"},
        ]

        for item in medications_data:
            med, created = Medication.objects.get_or_create(
                brand_name=item["brand"],
                ingredient=ingredient_objects[item["ingredient"]],
                dosage_form=item["form"],
                defaults={"strength": item["strength"]}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created Medication: {med.brand_name} {med.strength}"))

        self.stdout.write(self.style.SUCCESS("Database successfully seeded."))