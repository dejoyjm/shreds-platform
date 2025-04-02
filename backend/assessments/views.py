from rest_framework.views import APIView
from rest_framework.response import Response as DRFResponse
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import Test, Question, Candidate, Response as Answer, ScoreReport
from .serializers import (
    TestSerializer, QuestionSerializer, CandidateSerializer,
    ResponseSerializer, ScoreReportSerializer
)

# -----------------------------
# 1. Get Test & Questions
# -----------------------------
class TestDetailAPIView(APIView):
    def get(self, request, test_id):
        test = get_object_or_404(Test, id=test_id)
        questions = Question.objects.filter(test=test)

        return DRFResponse({
            'test': TestSerializer(test).data,
            'questions': QuestionSerializer(questions, many=True).data
        })


# -----------------------------
# 2. Submit Answers & Score
# -----------------------------
class SubmitTestAPIView(APIView):
    @transaction.atomic
    def post(self, request):
        """
        Expected payload:
        {
            "candidate": {
                "name": "Ethan",
                "email": "ethan@example.com"
            },
            "test_id": 1,
            "responses": [
                {"question_id": 10, "answer": "B"},
                {"question_id": 11, "answer": "D"},
                ...
            ]
        }
        """
        data = request.data
        candidate_data = data.get("candidate")
        test_id = data.get("test_id")
        responses = data.get("responses", [])

        # Get or create candidate
        candidate, _ = Candidate.objects.get_or_create(
            email=candidate_data["email"],
            defaults={
                "name": candidate_data.get("name", ""),
                "phone": candidate_data.get("phone", "")
            }
        )

        test = get_object_or_404(Test, id=test_id)
        score = 0
        total = 0

        for r in responses:
            q = get_object_or_404(Question, id=r["question_id"])
            Answer.objects.create(candidate=candidate, question=q, answer=r["answer"])

            if q.question_type == "MCQ":
                total += 1
                if str(r["answer"]).strip().lower() == str(q.correct_answer).strip().lower():
                    score += 1

        report = ScoreReport.objects.create(
            candidate=candidate,
            test=test,
            score=score,
            total=total
        )

        return DRFResponse({
            "message": "Submission successful",
            "report": ScoreReportSerializer(report).data
        }, status=status.HTTP_201_CREATED)


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
