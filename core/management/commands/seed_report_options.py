
from django.core.management.base import BaseCommand
from core.models import Area, Category


class Command(BaseCommand):
    help = "Populate initial report categories and areas"

    def handle(self, *args, **options):
        categories = [
            ("Road Damage", "infrastructure"),
            ("Broken Footpath", "infrastructure"),
            ("Streetlight Problem", "public_utilities"),
            ("Water Supply Problem", "public_utilities"),
            ("Drainage and Waterlogging", "public_utilities"),
            ("Garbage and Waste", "environment"),
            ("Air Pollution", "environment"),
            ("Safety Concern", "safety"),
        ]

        areas = [
            "Dhanmondi",
            "Mirpur",
            "Uttara",
            "Gulshan",
            "Banani",
            "Mohammadpur",
            "Farmgate",
            "Motijheel",
        ]

        for name, category_type in categories:
            Category.objects.get_or_create(
                name=name,
                type=category_type,
            )

        for name in areas:
            Area.objects.get_or_create(name=name)

        self.stdout.write(
            self.style.SUCCESS(
                "Initial categories and areas are ready."
            )
        )
