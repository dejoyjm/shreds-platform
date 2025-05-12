import os
import sys
import io
import django
from django.core.management import call_command

# Tell Django which settings to use
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assessments.settings')

# Setup Django
django.setup()

# Force UTF-8 stdout encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Run the dump
call_command("dumpdata", exclude=["contenttypes", "auth.Permission"], indent=2)
