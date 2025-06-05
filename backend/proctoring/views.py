from rest_framework.decorators import api_view

from rest_framework.response import Response
from rest_framework import status
from proctoring.models import (
    TestProctoringConfig,
    IDDocumentType,
    CandidateConsent,
    ProctoringPhoto, ProctoringViolation, ProctoringSession, ProctoringHeartbeat
)
from test_engine.models import Candidate, TestAssignment, CandidateTestSession, TestAssignment, SectionStatus

from django.utils import timezone


@api_view(["GET"])
def get_consent(request):
    assignment_id = request.query_params.get("assignment_id")
    if not assignment_id:
        return Response({"error": "assignment_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        assignment = TestAssignment.objects.select_related("test").get(id=assignment_id)
    except TestAssignment.DoesNotExist:
        return Response({"error": "Invalid assignment_id"}, status=status.HTTP_404_NOT_FOUND)

    try:
        config = TestProctoringConfig.objects.get(test=assignment.test)
    except TestProctoringConfig.DoesNotExist:
        return Response({"error": "No proctoring config found for this test"}, status=status.HTTP_404_NOT_FOUND)

    allowed_ids = config.allowed_id_documents.all()
    id_docs = [{"id": doc.id, "name": doc.name} for doc in allowed_ids]

    return Response({
        "consent_text": config.consent_text,
        "require_face_photo": config.require_face_photo,
        "require_signature_photo": config.require_signature_photo,
        "allowed_id_documents": id_docs,
        "allow_file_upload": config.allow_file_upload_fallback,
        "require_screen_capture_periodic": config.require_screen_capture_periodic,
        "periodic_screen_capture_sec": config.periodic_screen_capture_sec,

    })


@api_view(["POST"])
def submit_consent(request):

    assignment_id = request.data.get("assignment_id")
    candidate_id = request.data.get("candidate_id")
    agreed = request.data.get("agreed")

    if not all([assignment_id, candidate_id, agreed is not None]):
        return Response({"error": "assignment_id, candidate_id, and agreed are required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        assignment = TestAssignment.objects.get(id=assignment_id)
    except TestAssignment.DoesNotExist:
        return Response({"error": "Invalid assignment_id"}, status=status.HTTP_404_NOT_FOUND)

    try:
        candidate = Candidate.objects.get(id=candidate_id)
    except Candidate.DoesNotExist:
        return Response({"error": "Invalid candidate_id"}, status=status.HTTP_404_NOT_FOUND)

    if CandidateConsent.objects.filter(candidate=candidate, test_assignment=assignment).exists():
        return Response({"error": "Consent already submitted for this assignment"}, status=status.HTTP_409_CONFLICT)

    try:
        config = TestProctoringConfig.objects.get(test=assignment.test)
    except TestProctoringConfig.DoesNotExist:
        return Response({"error": "Proctoring config not found for this test"}, status=status.HTTP_404_NOT_FOUND)

    CandidateConsent.objects.create(
        candidate=candidate,
        test_assignment=assignment,
        consent_text=config.consent_text,
        agreed=agreed,
    )

    return Response({"status": "consent_saved"})

@api_view(["POST"])
def upload_photo(request):
    candidate_id = request.POST.get("candidate_id")
    assignment_id = request.POST.get("assignment_id")
    photo_type = request.POST.get("photo_type")
    id_document_type_id = request.POST.get("id_document_type")
    image = request.FILES.get("image")
    context = request.POST.get("context", "initial")

    if not all([candidate_id, assignment_id, photo_type, image]):
        return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

    VALID_PHOTO_TYPES = [choice[0] for choice in ProctoringPhoto._meta.get_field("photo_type").choices]
    if photo_type not in VALID_PHOTO_TYPES:
        return Response({"error": f"Invalid photo_type. Must be one of: {', '.join(VALID_PHOTO_TYPES)}"},
                        status=status.HTTP_400_BAD_REQUEST)

    try:
        candidate = Candidate.objects.get(id=candidate_id)
        assignment = TestAssignment.objects.get(id=assignment_id)
    except (Candidate.DoesNotExist, TestAssignment.DoesNotExist):
        return Response({"error": "Invalid candidate or assignment ID"}, status=status.HTTP_404_NOT_FOUND)

    id_doc_type = None
    if photo_type == "id":
        if not id_document_type_id:
            return Response({"error": "id_document_type is required for ID photos"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            id_doc_type = IDDocumentType.objects.get(id=id_document_type_id)
        except IDDocumentType.DoesNotExist:
            return Response({"error": "Invalid ID document type"}, status=status.HTTP_404_NOT_FOUND)

    photo_obj = ProctoringPhoto.objects.create(
        candidate=candidate,
        test_assignment=assignment,
        photo_type=photo_type,
        id_document_type=id_doc_type,
        image=image,
        context=context,
        quality_self_declared=True
    )

    # 🟢 Update heartbeat
    heartbeat, _ = ProctoringHeartbeat.objects.get_or_create(assignment=assignment)
    photo_url = photo_obj.image.url

    if photo_type == "face":
        heartbeat.update_face_capture(photo_url, ok=True)
    elif photo_type == "screen":
        heartbeat.update_screen_capture(photo_url, ok=True)

    return Response({"status": "photo_uploaded"})


@api_view(["GET"])
def check_ready(request):
    assignment_id = request.query_params.get("assignment_id")
    candidate_id = request.query_params.get("candidate_id")

    if not assignment_id or not candidate_id:
        return Response({"error": "assignment_id and candidate_id are required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        assignment = TestAssignment.objects.select_related("test").get(id=assignment_id)
        candidate = Candidate.objects.get(id=candidate_id)
    except (TestAssignment.DoesNotExist, Candidate.DoesNotExist):
        return Response({"error": "Invalid assignment_id or candidate_id"}, status=status.HTTP_404_NOT_FOUND)

    try:
        config = TestProctoringConfig.objects.get(test=assignment.test)
    except TestProctoringConfig.DoesNotExist:
        # Proctoring not required
        return Response({
            "ready": True,
            "enforce_proctoring": False,
            "requirements": {}
        })

    missing = []
    photos = ProctoringPhoto.objects.filter(candidate=candidate, test_assignment=assignment)

    # Consent check
    if config.consent_required and not CandidateConsent.objects.filter(candidate=candidate, test_assignment=assignment, agreed=True).exists():
        missing.append("consent")

    # Required photos check
    if config.require_face_photo and not photos.filter(photo_type="face", context="initial").exists():
        missing.append("face")

    if config.require_signature_photo and not photos.filter(photo_type="signature", context="initial").exists():
        missing.append("signature")

    if config.require_id_photo and config.allowed_id_documents.exists() and not photos.filter(photo_type="id", context="initial").exists():
        missing.append("id")

    reason = "initial_proctoring_not_completed" if missing else "proctoring_ready"
    return Response({
        "ready": len(missing) == 0,
        "enforce_proctoring": True,
        "missing": missing,
        "reason": reason,
        "requirements": {
            "consent_required": config.consent_required,
            "consent_text": config.consent_text if config.consent_required else "",
            "require_face_photo_initial": config.require_face_photo,
            "require_id_photo_initial": config.require_id_photo,
            "require_signature_photo_initial": config.require_signature_photo,
            "allow_file_upload": config.allow_file_upload_fallback,
            "require_final_photo": config.require_final_photo,
            "require_face_photo_periodic": config.require_face_photo_periodic,
            "require_screen_capture_periodic": config.require_screen_capture_periodic,
            "periodic_face_capture_sec": config.periodic_face_capture_sec,
            "periodic_screen_capture_sec": config.periodic_screen_capture_sec,
            "violation_boost_factor": config.violation_boost_factor,
            "max_upload_size_mb": config.max_upload_size_mb,
            "quality_profile": config.quality_profile,
            "allow_file_upload_fallback": config.allow_file_upload_fallback,
            "live_admin_override": config.live_admin_override,
            "allowed_id_documents": list(config.allowed_id_documents.values("id", "name")),
        }
    })


@api_view(["POST"])
def start_proctoring_session(request):
    candidate_id = request.data.get("candidate_id")
    assignment_id = request.data.get("assignment_id")

    if not candidate_id or not assignment_id:
        return Response({"error": "Missing candidate_id or assignment_id"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        candidate = Candidate.objects.get(id=candidate_id)
        assignment = TestAssignment.objects.get(id=assignment_id)
    except (Candidate.DoesNotExist, TestAssignment.DoesNotExist):
        return Response({"error": "Invalid candidate or assignment_id"}, status=status.HTTP_404_NOT_FOUND)

    session, created = ProctoringSession.objects.get_or_create(
        candidate=candidate,
        test_assignment=assignment,
        defaults={"started_at": timezone.now()}
    )

    if not created:
        session.is_active = True
        session.ended_at = None
        session.save()

    return Response({
        "status": "started" if created else "resumed",
        "session_token": str(session.session_token),
        "started_at": session.started_at,
    })


@api_view(["POST"])
def update_proctoring_status(request):
    session_token = request.data.get("session_token")
    camera_ok = request.data.get("camera_streaming_ok")
    screen_ok = request.data.get("screen_sharing_ok")
    fullscreen = request.data.get("fullscreen_mode")

    if not session_token:
        return Response({"error": "Missing session_token"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        session = ProctoringSession.objects.get(session_token=session_token)
    except ProctoringSession.DoesNotExist:
        return Response({"error": "Invalid session_token"}, status=status.HTTP_404_NOT_FOUND)

    session.camera_streaming_ok = camera_ok if camera_ok is not None else session.camera_streaming_ok
    session.screen_sharing_ok = screen_ok if screen_ok is not None else session.screen_sharing_ok
    session.fullscreen_mode = fullscreen if fullscreen is not None else session.fullscreen_mode
    session.last_heartbeat = timezone.now()
    session.save()

    return Response({"status": "updated", "last_heartbeat": session.last_heartbeat})



@api_view(["GET"])
def check_proctoring_status(request):
    session_token = request.query_params.get("session_token")

    if not session_token:
        return Response({"error": "Missing session_token"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        session = ProctoringSession.objects.get(session_token=session_token)
    except ProctoringSession.DoesNotExist:
        return Response({"error": "Invalid session_token"}, status=status.HTTP_404_NOT_FOUND)

    return Response({
        "candidate": session.candidate.name,
        "test": session.test_assignment.test.name,
        "is_active": session.is_active,
        "camera_streaming_ok": session.camera_streaming_ok,
        "screen_sharing_ok": session.screen_sharing_ok,
        "fullscreen_mode": session.fullscreen_mode,
        "last_heartbeat": session.last_heartbeat,
        "started_at": session.started_at,
        "ended_at": session.ended_at
    })

@api_view(["POST"])
def log_violation(request):
    try:
        assignment_id = request.data.get("assignment_id")
        violation_type = request.data.get("type")
        metadata = request.data.get("metadata", {})
        severity = int(request.data.get("severity", 1))

        if not all([assignment_id, violation_type]):
            return Response({"error": "Missing assignment_id or violation type"}, status=status.HTTP_400_BAD_REQUEST)

        # Create violation record
        violation = ProctoringViolation.objects.create(
            assignment_id=assignment_id,
            violation_type=violation_type,
            severity=severity,
            metadata=metadata
        )

        # Update heartbeat
        heartbeat, _ = ProctoringHeartbeat.objects.get_or_create(assignment_id=assignment_id)
        heartbeat.last_seen = violation.timestamp  # Optional: or use timezone.now()

        # Handle specific violation effects
        if violation_type == "fullscreen_exit":
            heartbeat.mark_fullscreen_exit()
        else:
            heartbeat.increment_severity(severity)

        return Response({"status": "logged"}, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["POST"])
def update_heartbeat(request):
    """
    Accepts JSON: {
        "assignment_id": int,
        "session_token": str,
        "screen_ok": bool,
        "fullscreen_ok": bool (optional),
        "reason": str (optional)
    }
    """
    assignment_id = request.data.get("assignment_id")
    session_token = request.data.get("session_token")
    screen_ok = request.data.get("screen_ok")
    fullscreen_ok = request.data.get("fullscreen_ok")
    reason = request.data.get("reason", "heartbeat update")

    if not assignment_id or screen_ok is None:
        return Response({"error": "Missing required fields"}, status=400)

    try:
        session = CandidateTestSession.objects.get(
            assignment_id=assignment_id,
            session_token=session_token,
            completed=False,
        )
    except CandidateTestSession.DoesNotExist:
        return Response({"error": "Active session not found"}, status=404)

    # Save heartbeat update on session
    session.last_seen = timezone.now()
    session.screen_ok = bool(screen_ok)
    session.save(update_fields=["last_seen", "screen_ok"])

    # Update fullscreen status on latest heartbeat or create new one
    try:
        heartbeat = ProctoringHeartbeat.objects.filter(
            assignment=session.assignment,
            attempt_number=session.attempt_number
        ).latest("created_at")
    except ProctoringHeartbeat.DoesNotExist:
        heartbeat = ProctoringHeartbeat.objects.create(
            assignment=session.assignment,
            attempt_number=session.attempt_number
        )


    return Response({"status": "heartbeat updated", "screen_ok": screen_ok, "fullscreen_ok": fullscreen_ok})
