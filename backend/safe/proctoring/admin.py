from django.contrib import admin
from .models import (
    IDDocumentType,
    TestProctoringConfig,
    ProctoringPhoto,
    CandidateConsent,
)

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
