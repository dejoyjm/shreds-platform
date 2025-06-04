from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from proctoring.models import (
    TestProctoringConfig,
    IDDocumentType,
    CandidateConsent,
    ProctoringPhoto
)
from test_engine.models import Candidate, TestAssignment



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
        "allow_file_upload": config.allow_file_upload,
        "require_screen_capture": config.require_screen_capture,
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

    # ✅ Validate photo_type from model choices
    from proctoring.models import ProctoringPhoto  # Optional if already at top
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

    ProctoringPhoto.objects.create(
        candidate=candidate,
        test_assignment=assignment,
        photo_type=photo_type,
        id_document_type=id_doc_type,
        image=image,
        context=context,
        quality_self_declared=True
    )

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

    return Response({
        "ready": len(missing) == 0,
        "enforce_proctoring": True,
        "missing": missing,
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
