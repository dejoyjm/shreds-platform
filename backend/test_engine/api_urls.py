from django.urls import path
from .views import TestDetailAPIView, SubmitTestAPIView, ScoreReportByEmailAPIView

urlpatterns = [
    path('test/<int:test_id>/', TestDetailAPIView.as_view(), name='test-detail'),
    path('submit/', SubmitTestAPIView.as_view(), name='submit-test'),
    path('report/', ScoreReportByEmailAPIView.as_view(), name='score-report'),
]
