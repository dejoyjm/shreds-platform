from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response as DRFResponse

from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from random import shuffle
import json
from test_engine.utils.scoring import calculate_score_for_candidate, serialize_score_report, generate_score_report_excel



from .models import (
    Test, Question, Candidate, TestQuestionSet,
    Response as CandidateResponse, ScoreReport, CandidateTestSession,
    TestSectionConfig, TestAssignment, SectionStatus,
    CandidateSectionQuestionOrder, ArchivedResponse
)
from .serializers import (
    TestSerializer, QuestionSerializer, CandidateSerializer,
    ResponseSerializer, ScoreReportSerializer, TestDetailSerializer,
    PerQuestionResponseSerializer, QuestionPublicSerializer
)
from test_engine.utils.scoring import calculate_score_for_candidate, serialize_score_report


# -----------------------------
# 1. Get Test & Questions
# -----------------------------
class TestDetailAPIView(APIView):
    def get(self, request, test_id):
        try:
            test = Test.objects.get(pk=test_id)
        except Test.DoesNotExist:
            return Response({"error": "Test not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = TestDetailSerializer(test)
        return Response(serializer.data)


# -----------------------------
# 2. Submit Answers & Score
# -----------------------------




class SavePerQuestionResponseAPIView(APIView):
    def post(self, request):
        candidate_id = request.data.get("candidate")
        test_id = request.data.get("test")
        attempt_number = request.data.get("attempt_number")
        question_id = request.data.get("question")
        answer = request.data.get("answer")
        marked_for_review = request.data.get("marked_for_review", False)
        time_spent = request.data.get("time_spent", 0)

        if not all([candidate_id, test_id, attempt_number, question_id]):
            return Response({"error": "Missing required fields"}, status=400)

        question = get_object_or_404(Question, id=question_id)

        raw_answer = answer
        if question.question_type == "MCQ" and answer in ["A", "B", "C", "D"]:
            try:
                options_list = json.loads(question.options)
                raw_answer = options_list["ABCD".index(answer)]
            except Exception as e:
                raw_answer = answer  # fallback in case parsing fails

        old_response = CandidateResponse.objects.filter(
            candidate_id=candidate_id,
            question_id=question_id,
            test_id=test_id,
            attempt_number=attempt_number
        ).first()

        if old_response:
            ArchivedResponse.objects.create(
                candidate_id=candidate_id,
                question_id=question_id,
                test_id=test_id,
                answer=old_response.answer,
                time_spent=old_response.time_spent,
                marked_for_review=old_response.marked_for_review,
                revisit_count=old_response.revisit_count,
                answered_at=old_response.answered_at,
                attempt_number=attempt_number,
                archived_at=timezone.now()
            )

        CandidateResponse.objects.update_or_create(
            candidate_id=candidate_id,
            question_id=question_id,
            test_id=test_id,
            attempt_number=attempt_number,
            defaults={
                "answer": raw_answer,
                "marked_for_review": marked_for_review,
                "time_spent": time_spent,
                "answered_at": timezone.now(),
            },
        )

        return Response({"status": "saved"}, status=200)


class SaveBulkResponsesAPIView(APIView):
    def post(self, request):
        candidate_id = request.data.get("candidate")
        test_id = request.data.get("test")
        attempt_number = request.data.get("attempt_number")
        responses = request.data.get("responses", [])
        section_id = request.data.get("section_id")
        section_complete = request.data.get("section_complete", False)
        auto = request.data.get("auto", False)

        if not all([candidate_id, test_id, attempt_number]):
            return Response({"error": "Missing required fields"}, status=400)

        try:
            # ✅ First validate section state
            session = CandidateTestSession.objects.get(
                assignment__candidate_id=candidate_id,
                assignment__test_id=test_id,
                attempt_number=attempt_number,
                completed=False
            )

            if section_id:
                section = TestSectionConfig.objects.get(id=section_id)

                # 🔒 Prevent submission of out-of-order section
                if session.current_section and section.id != session.current_section.id:
                    return Response({
                        "error": "You are not allowed to submit this section now."
                    }, status=403)

                section_status, _ = SectionStatus.objects.get_or_create(
                    session=session,
                    section=section,
                    defaults={"started_at": timezone.now()}
                )

                # 🔒 Prevent double submission of already completed section
                if section_status.is_completed:
                    return Response({
                        "error": "Section already completed. No further submissions allowed."
                    }, status=400)

            # ✅ Save responses
            for r in responses:
                question_id = r.get("question")
                answer = r.get("answer")
                time_spent = r.get("time_spent", 0)
                marked_for_review = r.get("marked_for_review", False)

                question = get_object_or_404(Question, id=question_id)

                raw_answer = answer
                if question.question_type == "MCQ" and answer in ["A", "B", "C", "D"]:
                    try:
                        options_list = json.loads(question.options)
                        raw_answer = options_list["ABCD".index(answer)]
                    except Exception:
                        raw_answer = answer

                old_response = CandidateResponse.objects.filter(
                    candidate_id=candidate_id,
                    question_id=question_id,
                    test_id=test_id,
                    attempt_number=attempt_number
                ).first()

                if old_response:
                    ArchivedResponse.objects.create(
                        candidate_id=candidate_id,
                        question_id=question_id,
                        test_id=test_id,
                        answer=old_response.answer,
                        time_spent=old_response.time_spent,
                        marked_for_review=old_response.marked_for_review,
                        revisit_count=old_response.revisit_count,
                        answered_at=old_response.answered_at,
                        attempt_number=attempt_number,
                        archived_at=timezone.now()
                    )

                CandidateResponse.objects.update_or_create(
                    candidate_id=candidate_id,
                    question_id=question_id,
                    test_id=test_id,
                    attempt_number=attempt_number,
                    defaults={
                        "answer": raw_answer,
                        "marked_for_review": marked_for_review,
                        "time_spent": time_spent,
                        "answered_at": timezone.now(),
                    },
                )

            # ✅ Mark section complete if requested
            if section_complete and section_id:
                section_status.is_completed = True
                section_status.auto_submitted = auto
                section_status.submitted_at = timezone.now()
                section_status.save()
                print("✅ SectionStatus marked complete.")

                # ✅ Check if all sections complete → complete the test
                all_sections = list(
                    TestSectionConfig.objects.filter(test_id=test_id).values_list("id", flat=True)
                )
                completed_sections = list(
                    SectionStatus.objects.filter(session=session, is_completed=True).values_list("section_id", flat=True)
                )

                if set(all_sections) == set(completed_sections):
                    print("🎉 All sections completed. Test is now complete.")
                    session.completed = True
                    session.save()
                    test = Test.objects.get(id=test_id)
                    candidate = Candidate.objects.get(id=candidate_id)
                    try:
                        result = calculate_score_for_candidate(test, candidate, attempt_number)
                        report_data = serialize_score_report(result["report"],
                                                             section_summary=result["section_summary"])
                        generate_score_report_excel(candidate, test, attempt_number, report_data)
                    except Exception as e:
                        print("⚠️ Failed to generate score report:", e)

                    return Response({"status": "completed"})

                return Response({"status": "section_saved"})

        except CandidateTestSession.DoesNotExist:
            return Response({"error": "No active session found or test already completed."}, status=404)
        except Exception as e:
            print("❌ Exception in SaveBulkResponsesAPIView:", str(e))
            return Response({"error": f"Internal error: {str(e)}"}, status=500)

        return Response({"status": "saved"}, status=200)






class SubmitTestAPIView(APIView):
    def post(self, request):
        candidate_id = request.data.get("candidate")
        test_id = request.data.get("test")
        attempt_number = request.data.get("attempt_number")

        if not all([candidate_id, test_id, attempt_number]):
            return Response({"error": "Missing required fields"}, status=400)

        session = get_object_or_404(
            CandidateTestSession,
            assignment__candidate_id=candidate_id,
            assignment__test_id=test_id,
            attempt_number=attempt_number,
        )

        session.completed = True
        session.save()

        test = Test.objects.get(id=test_id)
        candidate = Candidate.objects.get(id=candidate_id)

        try:
            result = calculate_score_for_candidate(test, candidate, attempt_number)
            report_data = serialize_score_report(result["report"], section_summary=result["section_summary"])
            generate_score_report_excel(candidate, test, attempt_number, report_data)
        except Exception as e:
            print("⚠️ Failed to generate score report:", e)

        return Response({"status": "submitted"}, status=200)


class AutoSubmitAPIView(APIView):
    def post(self, request):
        candidate_id = request.data.get("candidate")
        test_id = request.data.get("test")
        attempt_number = request.data.get("attempt_number")

        if not all([candidate_id, test_id, attempt_number]):
            return Response({"error": "Missing required fields"}, status=400)

        session = get_object_or_404(
            CandidateTestSession,
            assignment__candidate_id=candidate_id,
            assignment__test_id=test_id,
            attempt_number=attempt_number,
        )

        session.completed = True
        session.save()

        SectionStatus.objects.filter(
            session=session,
            section=session.current_section
        ).update(auto_submitted=True, submitted_at=timezone.now())

        test = Test.objects.get(id=test_id)
        candidate = Candidate.objects.get(id=candidate_id)

        try:
            result = calculate_score_for_candidate(test, candidate, attempt_number)
            report_data = serialize_score_report(result["report"], section_summary=result["section_summary"])
            generate_score_report_excel(candidate, test, attempt_number, report_data)
        except Exception as e:
            print("⚠️ Failed to generate score report:", e)

        return Response({"status": "auto-submitted"}, status=200)




class StartSessionAPIView(APIView):
    def post(self, request):
        candidate_id = request.data.get("candidate")
        test_id = request.data.get("test")

        if not candidate_id or not test_id:
            return Response({"error": "Missing candidate or test ID"}, status=400)

        # Verify assignment
        assignment = get_object_or_404(
            TestAssignment,
            candidate_id=candidate_id,
            test_id=test_id
        )

        # Check validity window
        now = timezone.now()
        if assignment.valid_from and now < assignment.valid_from:
            return Response({
                "error": "Test not yet available",
                "status": "not_yet_open",
                "valid_from": assignment.valid_from
            }, status=403)

        if assignment.valid_to and now > assignment.valid_to:
            return Response({
                "error": "Test window has closed",
                "status": "window_expired",
                "valid_to": assignment.valid_to
            }, status=403)

        # Check attempts
        existing_attempts = CandidateTestSession.objects.filter(assignment=assignment).count()
        if existing_attempts >= assignment.max_attempts:
            return Response({
                "error": "Maximum attempts reached",
                "status": "max_attempts_exceeded",
                "attempts_used": existing_attempts,
                "max_attempts": assignment.max_attempts
            }, status=403)

        # Create session
        attempt_number = existing_attempts + 1
        session = CandidateTestSession.objects.create(
            assignment=assignment,
            attempt_number=attempt_number,
            started_at=now,
        )

        # Set first section
        first_section = TestSectionConfig.objects.filter(test=assignment.test).order_by("id").first()
        if first_section:
            session.current_section = first_section
            session.section_started_at = now
            session.save()

            SectionStatus.objects.get_or_create(
                session=session,
                section=first_section,
                defaults={"started_at": now}
            )

        return Response({
            "session_id": session.id,
            "candidate": candidate_id,
            "test": assignment.test.name,
            "attempt_number": attempt_number,
            "section_id": first_section.id if first_section else None,
            "section_name": first_section.category.name if first_section else None,
            "section_start_time": session.section_started_at,
        }, status=200)


class ResumeSectionAPIView(APIView):
    def post(self, request):
        candidate_id = request.data.get("candidate")
        test_id = request.data.get("test")
        attempt_number = request.data.get("attempt_number")

        if not candidate_id or not test_id or not attempt_number:
            return Response({"error": "Missing input"}, status=400)

        try:
            session = CandidateTestSession.objects.select_related(
                "assignment__candidate", "assignment__test", "current_section"
            ).get(
                assignment__candidate_id=candidate_id,
                assignment__test_id=test_id,
                attempt_number=attempt_number,
                completed=False
            )
        except CandidateTestSession.DoesNotExist:
            return Response({"error": "No active session found"}, status=404)

        # ✅ BLOCK resume if test is already completed
        if session.completed:
            print("🛑 Session already marked completed. Not resuming.")
            return Response({"status": "completed", "message": "Test already completed."}, status=200)

        current_section = session.current_section
        if not current_section:
            return Response({"error": "No current section"}, status=400)

        section_status, _ = SectionStatus.objects.get_or_create(
            session=session,
            section=current_section,
            defaults={"started_at": timezone.now()}
        )

        section_duration = current_section.section_duration_minutes or 30
        section_end_time = section_status.started_at + timedelta(minutes=section_duration)
        now = timezone.now()

        print("🛠️ --- Section Resume Diagnostics ---")
        print(f"🧑‍🎓 Candidate ID        : {candidate_id}")
        print(f"🧪 Test ID              : {test_id}")
        print(f"🔁 Attempt Number       : {attempt_number}")
        print(f"📘 Section ID           : {current_section.id}")
        print(f"📘 Section Name         : {current_section.category.name}")
        print(f"✅ is_completed         : {section_status.is_completed}")
        print(f"⏱️  Duration (minutes)  : {section_duration}")
        print(f"🕒 Now                  : {now}")
        print(f"🕓 Started At           : {section_status.started_at}")
        print(f"🕚 Section End Time     : {section_end_time}")
        print(f"⌛ Time Left (seconds)  : {(section_end_time - now).total_seconds()}")
        print("🛠️ -----------------------------------")

        # 🔁 Progress to next section if manually completed OR timed out
        if section_status.is_completed or now > section_end_time:
            print("🔄 Section considered complete. Proceeding to check next section.")

            if not section_status.is_completed:
                print("⏳ Auto-submitting section due to time expiry.")
                section_status.auto_submitted = True
                section_status.submitted_at = section_end_time
                section_status.save()

            next_section = (
                session.assignment.test.sections
                .filter(id__gt=current_section.id)
                .order_by("id")
                .first()
            )

            if next_section:
                print(f"➡️ Found next section: {next_section.id} - {next_section.category.name}")
                session.current_section = next_section
                session.section_started_at = now
                session.save()
                try:
                    test = session.assignment.test
                    candidate = session.assignment.candidate
                    result = calculate_score_for_candidate(test, candidate, session.attempt_number)
                    report_data = serialize_score_report(result["report"], section_summary=result["section_summary"])
                    generate_score_report_excel(candidate, test, session.attempt_number, report_data)
                except Exception as e:
                    print("⚠️ Failed to generate score report at test completion:", e)

                section_status, _ = SectionStatus.objects.get_or_create(
                    session=session,
                    section=next_section,
                    defaults={"started_at": now}
                )

                current_section = next_section
                section_end_time = section_status.started_at + timedelta(
                    minutes=current_section.section_duration_minutes or 1
                )

            else:
                print("✅ No more sections remaining. Marking session as completed.")
                session.completed = True
                session.save()
                try:
                    test = session.assignment.test
                    candidate = session.assignment.candidate
                    result = calculate_score_for_candidate(test, candidate, session.attempt_number)
                    report_data = serialize_score_report(result["report"], section_summary=result["section_summary"])
                    generate_score_report_excel(candidate, test, session.attempt_number, report_data)
                except Exception as e:
                    print("⚠️ Failed to generate score report at test completion:", e)

                return Response({"status": "completed"}, status=200)

        # 🗂️ Get questions for the current section
        existing_orders = CandidateSectionQuestionOrder.objects.filter(
            session=session,
            section=current_section
        ).order_by("display_order")

        if existing_orders.exists():
            questions = [entry.question for entry in existing_orders]
            print("📋 Found existing question order entries.")
        else:
            print("📋 No existing order. Generating fresh question list.")
            question_ids = (
                TestQuestionSet.objects
                .filter(test=session.assignment.test, question__category=current_section.category)
                .order_by("order")
                .values_list("question_id", flat=True)
            )

            questions = list(Question.objects.filter(id__in=question_ids))
            print(f"[DEBUG] Questions before shuffle: {[q.id for q in questions]}")

            shuffle(questions)  # can be removed if strict order needed

            for index, q in enumerate(questions):
                CandidateSectionQuestionOrder.objects.get_or_create(
                    session=session,
                    section=current_section,
                    question=q,
                    defaults={"display_order": index}
                )

        serialized_questions = QuestionSerializer(questions, many=True).data
        print(f"[DEBUG] Questions after shuffle (serialized): {[q['id'] for q in serialized_questions]}")

        return Response({
            "session_id": session.id,
            "candidate_id": candidate_id,
            "test_id": test_id,
            "attempt_number": session.attempt_number,
            "section_id": current_section.id,
            "section_name": current_section.category.name,
            "section_start_time": section_status.started_at,
            "section_duration_minutes": current_section.section_duration_minutes,
            "questions": serialized_questions,
            "time_left_seconds": max(0, int((section_end_time - now).total_seconds()))
        }, status=200)



class ResumeSessionAPIView(APIView):
    def post(self, request):
        candidate_id = request.data.get("candidate")
        test_id = request.data.get("test")

        if not candidate_id or not test_id:
            return Response({"error": "Missing candidate or test ID"}, status=400)

        session = CandidateTestSession.objects.select_related(
            "assignment__candidate", "assignment__test", "current_section"
        ).filter(
            assignment__candidate_id=candidate_id,
            assignment__test_id=test_id,
            completed=False
        ).order_by("-attempt_number").first()

        if not session:
            return Response({"error": "No active session found"}, status=404)

        return Response({
            "session_id": session.id,
            "candidate": str(session.assignment.candidate.id),
            "test": session.assignment.test.name,
            "attempt_number": session.attempt_number,
            "current_section": session.current_section.category.name if session.current_section else None,
            "section_id": session.current_section.id if session.current_section else None,
            "section_start_time": session.section_started_at,
        })







# -----------------------------
# 3. Get Report by Email & Test ID
# -----------------------------
class ScoreReportByEmailAPIView(APIView):
    def get(self, request):
        email = request.query_params.get("email")
        test_id = request.query_params.get("test_id")

        candidate = get_object_or_404(Candidate, email=email)
        report = get_object_or_404(ScoreReport, candidate=candidate, test_id=test_id)

        return DRFResponse({
            "report": ScoreReportSerializer(report).data
        })




# ----------To Validate Candidate Test Assignment
class VerifySecretsAPIView(APIView):
    def post(self, request):
        email = request.data.get("email")
        phone = request.data.get("mobile")
        secret1 = request.data.get("secret1")
        secret2 = request.data.get("secret2")

        if not all([email, phone, secret1, secret2]):
            return Response({"error": "Missing required fields"}, status=400)

        try:
            candidate = Candidate.objects.get(
                email=email,
                phone=phone,
                secret_code_1=secret1,
                secret_code_2=secret2
            )
        except Candidate.DoesNotExist:
            return Response({"error": "Invalid credentials"}, status=401)

        # 🔍 Fetch all assignments for the candidate
        now = timezone.now()
        assignments = TestAssignment.objects.select_related("test").filter(
            candidate=candidate,
            valid_to__gte=now
        ).order_by("valid_from")

        valid_assignments = []

        for assign in assignments:
            test = assign.test
            attempt_count = CandidateTestSession.objects.filter(assignment=assign).count()

            status_info = "ok"
            can_start = False

            if assign.valid_from and now < assign.valid_from:
                status_info = "not_yet_open"
            elif assign.valid_to and now > assign.valid_to:
                status_info = "window_expired"
            elif attempt_count >= assign.max_attempts:
                status_info = "max_attempts_exceeded"
            else:
                can_start = True

            total_questions = TestQuestionSet.objects.filter(test=test).count()
            sections = TestSectionConfig.objects.filter(test=test)

            valid_assignments.append({
                "assignment_id": assign.id,
                "test_id": test.id,
                "test_name": test.name,
                "valid_from": assign.valid_from,
                "valid_to": assign.valid_to,
                "attempts_used": attempt_count,
                "max_attempts": assign.max_attempts,
                "can_start": can_start,
                "status": status_info,
                "sections": [
                    {
                        "section_name": s.category.name,
                        "section_id": s.id,
                        "duration_minutes": s.section_duration_minutes or 30
                    } for s in sections.order_by("id")
                ],
                "total_questions": total_questions,
            })

        return Response({
            "candidate_id": candidate.id,
            "assignments": valid_assignments
        }, status=200)
