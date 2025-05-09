from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Create initial superuser if none exists"

    def handle(self, *args, **kwargs):
        User = get_user_model()
        if not User.objects.filter(username="dejoy.mathai").exists():
            User.objects.create_superuser(
                username="dejoy.mathai",
                email="dejoy@shreds.in",
                password="password"
            )
            self.stdout.write(self.style.SUCCESS("✅ Superuser created"))
        else:
            self.stdout.write("⚠️ Superuser already exists")
