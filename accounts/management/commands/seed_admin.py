import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create (or reset) the shared FixIt Local admin account for local development."

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get("SHARED_ADMIN_USERNAME", "admin")
        password = os.environ.get("SHARED_ADMIN_PASSWORD", "FixIt-Admin-2026")
        email = os.environ.get("SHARED_ADMIN_EMAIL", "admin@fixitlocal.test")

        user, created = User.objects.get_or_create(
            username=username, defaults={"email": email}
        )
        user.email = email
        user.role = User.Role.ADMIN      # FixIt Local role
        user.is_staff = True             # can enter /admin/
        user.is_superuser = True         # all permissions
        user.is_active = True
        user.set_password(password)
        user.save()

        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if created else 'Reset'} admin account '{username}'."
        ))