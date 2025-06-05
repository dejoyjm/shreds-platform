from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Sum, Max


from .models import (
    IDDocumentType,
    TestProctoringConfig,
    ProctoringPhoto,
    CandidateConsent,
    ProctoringViolation,
    ProctoringHeartbeat,
)
from test_engine.models import CandidateTestSession

@admin.register(IDDocumentType)
class IDDocumentTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description')
    search_fields = ('name',)

@admin.register(TestProctoringConfig)
class TestProctoringConfigAdmin(admin.ModelAdmin):
    list_display = ('test', 'require_face_photo', 'require_signature_photo')
    filter_horizontal = ('allowed_id_documents',)

@admin.register(ProctoringPhoto)
class ProctoringPhotoAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'test_assignment', 'photo_type', 'created_at', 'quality_self_declared', 'quality_flagged_by_admin')
    list_filter = ('photo_type', 'quality_flagged_by_admin')
    search_fields = ('candidate__name',)

@admin.register(CandidateConsent)
class CandidateConsentAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'test_assignment', 'agreed', 'timestamp')
    search_fields = ('candidate__name', 'test_assignment__test__name')

@admin.register(ProctoringViolation)
class ProctoringViolationAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'violation_type', 'severity', 'timestamp')
    list_filter = ('violation_type', 'severity')
    search_fields = ('assignment__candidate__name',)


@admin.register(ProctoringHeartbeat)
class ProctoringHeartbeatAdmin(admin.ModelAdmin):
    list_display = [
        'get_candidate_name',
        'get_test_name',
        'get_attempt_number',
        'candidate_status',
        'formatted_last_seen',
        'get_violation_count',
        'get_severity_score',
        'fullscreen_status',
        'face_photo_preview',
        'screen_photo_preview',
        'test_started_at',
        'test_completed_at',
    ]
    list_filter = ['candidate_status', 'severity_score']
    search_fields = ['assignment__candidate__name', 'assignment__candidate__email']

    def get_candidate_name(self, obj):
        return obj.assignment.candidate.name
    get_candidate_name.short_description = "Candidate"

    def get_test_name(self, obj):
        return obj.assignment.test.name
    get_test_name.short_description = "Test"

    def get_attempt_number(self, obj):
        session = CandidateTestSession.objects.filter(assignment=obj.assignment).order_by('-attempt_number').first()
        return session.attempt_number if session else "-"
    get_attempt_number.short_description = "Attempt #"

    def get_violation_count(self, obj):
        session = CandidateTestSession.objects.filter(assignment=obj.assignment).order_by('-attempt_number').first()
        if not session:
            return "-"

        end_time = session.sectionstatus_set.aggregate(max_end=Max("submitted_at"))['max_end'] or timezone.now()

        return ProctoringViolation.objects.filter(
            assignment=obj.assignment,
            attempt_number=session.attempt_number,
            timestamp__gte=session.started_at,
            timestamp__lte=end_time
        ).count()

    def formatted_last_seen(self, obj):
        return timezone.localtime(obj.last_seen).strftime('%b %d, %Y, %I:%M %p') if obj.last_seen else "-"
    formatted_last_seen.short_description = "Last Seen"

    def fullscreen_status(self, obj):
        session = CandidateTestSession.objects.filter(assignment=obj.assignment).order_by('-attempt_number').first()
        if not session:
            return "-"

        heartbeat = ProctoringHeartbeat.objects.filter(
            assignment=obj.assignment,
            attempt_number=session.attempt_number
        ).order_by('-last_seen').first()

        if not heartbeat:
            return "-"

        if not heartbeat.fullscreen_ok:
            if heartbeat.fullscreen_exit_time:
                return f"❌ Exited @ {timezone.localtime(heartbeat.fullscreen_exit_time).strftime('%H:%M:%S')}"
            return "❌"

        if heartbeat.fullscreen_exit_time:
            return f"✅ Resumed after {timezone.localtime(heartbeat.last_seen).strftime('%H:%M:%S')}"

        return "✅"
    fullscreen_status.short_description = "Fullscreen"

    def face_photo_preview(self, obj):
        if obj.last_face_photo_url:
            return format_html(
                '<a href="{0}" target="_blank"><img src="{0}" height="50" title="{1}" /></a>{2}',
                obj.last_face_photo_url,
                timezone.localtime(obj.last_face_timestamp).strftime('%H:%M:%S') if obj.last_face_timestamp else "",
                " ✅" if obj.last_face_capture_ok else " ❌"
            )
        return "-"
    face_photo_preview.short_description = "Face"

    def screen_photo_preview(self, obj):
        if obj.last_screen_photo_url:
            return format_html(
                '<a href="{0}" target="_blank"><img src="{0}" height="50" title="{1}" /></a>{2}',
                obj.last_screen_photo_url,
                timezone.localtime(obj.last_screen_timestamp).strftime('%H:%M:%S') if obj.last_screen_timestamp else "",
                " ✅" if obj.last_screen_ok else " ❌"
            )
        return "-"
    screen_photo_preview.short_description = "Screen"

    def get_severity_score(self, obj):
        session = CandidateTestSession.objects.filter(assignment=obj.assignment).order_by('-attempt_number').first()
        if not session:
            return obj.severity_score

        end_time = session.sectionstatus_set.filter(
            submitted_at__isnull=False
        ).aggregate(max_end=Max("submitted_at"))['max_end']

        return ProctoringViolation.objects.filter(
            assignment=obj.assignment,
            timestamp__gte=session.started_at,
            timestamp__lte=end_time or timezone.now()
        ).aggregate(score=Sum("severity"))['score'] or 0

