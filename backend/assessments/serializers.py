from rest_framework import serializers
from .models import Candidate, Test, Question, Response, ScoreReport

class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = ['id', 'name', 'email', 'phone']

class TestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = ['id', 'title', 'description', 'duration_minutes']

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'question_text', 'question_type', 'options']

class ResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Response
        fields = ['id', 'candidate', 'question', 'answer']

class ScoreReportSerializer(serializers.ModelSerializer):
    candidate = CandidateSerializer(read_only=True)
    test = TestSerializer(read_only=True)

    class Meta:
        model = ScoreReport
        fields = ['id', 'candidate', 'test', 'score', 'total', 'generated_at']
