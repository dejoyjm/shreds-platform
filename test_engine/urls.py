# test_engine/urls.py
from django.urls import path
from .views import (
    TestDetailAPIView, SubmitTestAPIView, ScoreReportByEmailAPIView,
    SavePerQuestionResponseAPIView, StartSessionAPIView, ResumeSectionAPIView, ResumeSessionAPIView, AutoSubmitAPIView,
    SaveBulkResponsesAPIView, VerifySecretsAPIView
)

urlpatterns = [
    path('test/<int:test_id>/', TestDetailAPIView.as_view(), name='test-detail'),
    path('submit/', SubmitTestAPIView.as_view(), name='submit-test'),
    path('report/', ScoreReportByEmailAPIView.as_view(), name='score-report'),
    path('save-response/', SavePerQuestionResponseAPIView.as_view(), name='save-response'),
    path('save-responses/', SaveBulkResponsesAPIView.as_view(), name='save-responses'),
    path('start-session/', StartSessionAPIView.as_view(), name='start-session'),
    path('resume-section/', ResumeSectionAPIView.as_view(), name='resume-section'),
    path('resume-session/', ResumeSessionAPIView.as_view(), name='resume-session'),
    path('auto-submit/', AutoSubmitAPIView.as_view(), name='auto-submit'),
    path('verify-secrets/', VerifySecretsAPIView.as_view(), name='verify-secrets'),

]
