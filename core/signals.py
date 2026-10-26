
from django.db.models.signals import post_migrate
from django.dispatch import receiver


DEFAULT_CATEGORIES = [
    ("Road Damage", "infrastructure"),
    ("Broken Footpath", "infrastructure"),
    ("Streetlight Problem", "public_utilities"),
    ("Water Supply Problem", "public_utilities"),
    ("Drainage and Waterlogging", "public_utilities"),
    ("Garbage and Waste", "environment"),
    ("Air Pollution", "environment"),
    ("Safety Concern", "safety"),
]


@receiver(post_migrate, dispatch_uid="core_seed_default_categories")
def create_default_categories(sender, app_config, using, apps, **kwargs):
    if sender.label != "core":
        return

    Category = apps.get_model("core", "Category")

    for name, category_type in DEFAULT_CATEGORIES:
        Category.objects.using(using).get_or_create(
            name=name,
            type=category_type,
            defaults={
                "description": "",
                "requires_after_photo": True,
            },
        )
