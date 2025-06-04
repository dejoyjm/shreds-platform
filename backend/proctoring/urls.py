

from django.urls import path
from .views import (
    get_consent, submit_consent, upload_photo, check_ready,
    start_proctoring_session,
    update_proctoring_status,
    check_proctoring_status
)


urlpatterns = [
    path("get-consent/", get_consent, name="get-consent"),
    path("submit-consent/", submit_consent, name="submit-consent"),
    path("upload-photo/", upload_photo, name="upload-photo"),
    path("check-ready/", check_ready),
    path("start-session/", start_proctoring_session),
    path("update-session-status/", update_proctoring_status),
    path("check-session-status/", check_proctoring_status),

]
