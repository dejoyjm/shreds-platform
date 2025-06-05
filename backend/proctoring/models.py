from django.db import models
from django.utils import timezone
from test_engine.models import Candidate, TestAssignment, Test
import uuid
from django.utils.html import format_html


class IDDocumentType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name



class ProctoringSession(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    test_assignment = models.ForeignKey(TestAssignment, on_delete=models.CASCADE)

    session_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    started_at = models.DateTimeField(auto_now_add=True)
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    screen_sharing_ok = models.BooleanField(default=False)
    camera_streaming_ok = models.BooleanField(default=False)
    fullscreen_mode = models.BooleanField(default=False)

    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("candidate", "test_assignment")

    def __str__(self):
        return f"ProctoringSession: {self.candidate.email} - {self.test_assignment.test.name}"


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


class ProctoringViolation(models.Model):
    VIOLATION_TYPES = [
        ('camera_lost', 'Camera Feed Lost'),
        ('camera_capture_failed', 'Camera Capture Failed'),
        ('screen_lost', 'Screen Share Lost'),
        ('screen_capture_failed', 'Screen Capture Failed'),
        ('fullscreen_exit', 'Fullscreen Exited'),
        ('face_mismatch', 'Face Mismatch'),
        ('multiple_faces', 'Multiple Faces'),
        ('no_face', 'No Face Detected'),
        ('keyboard_activity', 'Prohibited Keyboard Activity'),
        ('tab_switch', 'Tab Switch or Blur'),
        ('right_click', 'Right Click Detected'),
        ('other', 'Other'),
    ]

    assignment = models.ForeignKey(TestAssignment, on_delete=models.CASCADE)
    attempt_number = models.IntegerField(default=1)  # 🔁 NEW FIELD
    violation_type = models.CharField(max_length=64, choices=VIOLATION_TYPES)
    severity = models.IntegerField(default=1)  # 1 (minor) → 5 (major)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.assignment_id} - {self.violation_type} @ {self.timestamp.strftime('%H:%M:%S')}"


class ProctoringHeartbeat(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)  # 🔥 REQUIRED for `.latest("created_at")` to work
    assignment = models.ForeignKey('test_engine.TestAssignment', on_delete=models.CASCADE)
    attempt_number = models.IntegerField(default=1)  # 🔁 NEW FIELD
    last_seen = models.DateTimeField(auto_now=True)
    severity_score = models.IntegerField(default=0)

    last_face_photo_url = models.URLField(blank=True, null=True)
    last_face_timestamp = models.DateTimeField(blank=True, null=True)
    last_face_capture_ok = models.BooleanField(default=True)

    last_screen_photo_url = models.URLField(blank=True, null=True)
    last_screen_timestamp = models.DateTimeField(blank=True, null=True)
    last_screen_ok = models.BooleanField(default=True)

    fullscreen_ok = models.BooleanField(default=True)
    fullscreen_exit_time = models.DateTimeField(blank=True, null=True)

    candidate_status = models.CharField(
        max_length=20,
        choices=[
            ('not_started', 'Not Started'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed')
        ],
        default='not_started'
    )

    test_started_at = models.DateTimeField(blank=True, null=True)
    test_completed_at = models.DateTimeField(blank=True, null=True)


    def update_face_capture(self, url, ok=True):
        self.last_face_photo_url = url
        self.last_face_timestamp = timezone.now()
        self.last_face_capture_ok = ok
        self.save(update_fields=["last_face_photo_url", "last_face_timestamp", "last_face_capture_ok", "last_seen"])

    def update_screen_capture(self, url, ok=True):
        self.last_screen_photo_url = url
        self.last_screen_timestamp = timezone.now()
        self.last_screen_ok = ok
        self.save(update_fields=["last_screen_photo_url", "last_screen_timestamp", "last_screen_ok", "last_seen"])

    def mark_fullscreen_exit(self):
        self.fullscreen_ok = False
        self.fullscreen_exit_time = timezone.now()
        self.total_fullscreen_exits += 1
        self.save(update_fields=["fullscreen_ok", "fullscreen_exit_time", "total_fullscreen_exits", "last_seen"])

    def increment_severity(self, increment=1):
        self.severity_score += increment
        self.save(update_fields=["severity_score", "last_seen"])

    def mark_started(self):
        self.candidate_status = 'in_progress'
        self.test_started_at = timezone.now()
        self.save(update_fields=["candidate_status", "test_started_at", "last_seen"])

    def mark_completed(self):
        self.candidate_status = 'completed'
        self.test_completed_at = timezone.now()
        self.save(update_fields=["candidate_status", "test_completed_at", "last_seen"])


