from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Print all users with basic info"

    def handle(self, *args, **kwargs):
        User = get_user_model()
        users = User.objects.all()

        if not users:
            self.stdout.write("❌ No users found.")
            return

        for user in users:
            self.stdout.write(
                f"👤 Username: {user.username} | Email: {user.email} | "
                f"Staff: {user.is_staff} | Superuser: {user.is_superuser} | Active: {user.is_active}"
            )
