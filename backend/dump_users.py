from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        User = get_user_model()
        users = User.objects.all()
        if not users.exists():
            print("❌ NO users found in database.")
        else:
            print(f"✅ {users.count()} user(s) found:")
            for u in users:
                print(f"- {u.username} | is_staff={u.is_staff} | is_superuser={u.is_superuser}")
