from django.db import models
from django.utils import timezone
from test_engine.models import Candidate, TestAssignment, Test

class IDDocumentType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class TestProctoringConfig(models.Model):
    test = models.OneToOneField(Test, on_delete=models.CASCADE)

    consent_required = models.BooleanField(default=True)
    consent_text = models.TextField()

    require_face_photo = models.BooleanField(default=True)
    require_id_photo = models.BooleanField(default=True)
    require_signature_photo = models.BooleanField(default=False)
    require_final_photo = models.BooleanField(default=True)

    allowed_id_documents = models.ManyToManyField(IDDocumentType)
    allow_file_upload_fallback = models.BooleanField(default=False)
    max_upload_size_mb = models.PositiveIntegerField(default=2)

    require_face_photo_periodic = models.BooleanField(default=False)
    require_screen_capture_periodic = models.BooleanField(default=False)
    periodic_face_capture_sec = models.PositiveIntegerField(default=60)
    periodic_screen_capture_sec = models.PositiveIntegerField(default=60)
    violation_boost_factor = models.FloatField(default=1.0)

    quality_profile = models.CharField(
        max_length=20,
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')],
        default='medium'
    )

    live_admin_override = models.BooleanField(default=False)

    def __str__(self):
        return f"Proctoring Config for {self.test.name}"

class ProctoringPhoto(models.Model):
    PHOTO_TYPE_CHOICES = [
        ('face', 'Face'),
        ('id', 'ID Document'),
        ('signature', 'Signature'),
        ('screen', 'Screen Snapshot'),
    ]

    PHOTO_CONTEXT_CHOICES = [
        ('initial', 'Initial Setup'),
        ('periodic', 'Periodic Monitoring'),
        ('violation', 'Violation Capture'),
        ('final', 'Final Submission'),
    ]

    photo_type = models.CharField(max_length=20, choices=PHOTO_TYPE_CHOICES)
    context = models.CharField(max_length=20, choices=PHOTO_CONTEXT_CHOICES, default='initial')
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    test_assignment = models.ForeignKey(TestAssignment, on_delete=models.CASCADE)
    id_document_type = models.ForeignKey(IDDocumentType, null=True, blank=True, on_delete=models.SET_NULL)
    image = models.ImageField(upload_to='proctoring_photos/')
    created_at = models.DateTimeField(auto_now_add=True)
    quality_self_declared = models.BooleanField(default=False)
    quality_flagged_by_admin = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.candidate.name} - {self.photo_type}"

class CandidateConsent(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    test_assignment = models.ForeignKey(TestAssignment, on_delete=models.CASCADE)
    consent_text = models.TextField()
    agreed = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.candidate.name} consent for {self.test_assignment.test.name}"
