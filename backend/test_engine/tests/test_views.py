from rest_framework.test import APITestCase
from django.urls import reverse
from test_engine.models import Candidate, Test, Question, Response, ScoreReport, QuestionCategory


class TestSubmitScoring(APITestCase):
    def setUp(self):
        # Create a question category
        self.category = QuestionCategory.objects.create(name="General")

        # Create the test (real fields only!)
        self.test = Test.objects.create(
            name="Mock Test",
            total_duration_minutes=30,
            enforce_section_time=False,
            show_section_time_guidance=False
        )

        # Create questions
        self.q1 = Question.objects.create(
            text="What is 2 + 2?",
            correct_answer="A",
            options='["A", "B", "C", "D"]',
            difficulty="easy",
            positive_marks=2.0,
            negative_marks=1.0,
            category=self.category
        )

        self.q2 = Question.objects.create(
            text="Capital of France?",
            correct_answer="B",
            options='["A", "B", "C", "D"]',
            difficulty="easy",
            positive_marks=2.0,
            negative_marks=1.0,
            category=self.category
        )

        # Candidate setup
        self.candidate_data = {
            "email": "acmathai@example.com",
            "name": "Dr. A C Mathai",
            "phone": "9876543210"
        }

        self.candidate = Candidate.objects.create(**self.candidate_data)

        # Responses (1 correct, 1 incorrect)
        Response.objects.create(candidate=self.candidate, question=self.q1, answer="A")  # ✅ correct
        Response.objects.create(candidate=self.candidate, question=self.q2, answer="C")  # ❌ wrong

    def test_submit_and_score(self):
        url = reverse('submit-test')
        payload = {
            "candidate": self.candidate_data,
            "test_id": self.test.id
        }

        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn("report", response.data)

        report = ScoreReport.objects.get(candidate=self.candidate, test=self.test)
        self.assertEqual(float(report.score), 1.0)  # 2.0 (correct) - 1.0 (wrong)
        self.assertEqual(report.total_correct, 1)
        self.assertEqual(report.total_wrong, 1)
        self.assertEqual(report.total_unattempted, 0)
