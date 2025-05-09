from rest_framework import serializers
from .models import Candidate, Test, Question, Response, ScoreReport, TestQuestionSet

class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = ['id', 'name', 'email', 'phone']


class TestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = ['id', 'name'] #, 'description']


class QuestionSerializer(serializers.ModelSerializer):
    options = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ['id', 'text', 'question_type', 'options']

    def get_options(self, obj):
        try:
            # stored as JSON string in DB like '["89", "102", "97", "91"]'
            import json
            parsed = json.loads(obj.options)
            if isinstance(parsed, list):
                return parsed
            return [str(parsed)]
        except Exception:
            return []





class ResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Response
        fields = [
            'id', 'candidate', 'question', 'answer',
            'time_spent_seconds', 'marked_for_review', 'revisit_count'
        ]

class PerQuestionResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Response
        fields = ['candidate', 'question', 'answer', 'time_spent', 'marked_for_review', 'revisit_count']

class ScoreReportSerializer(serializers.ModelSerializer):
    max_possible = serializers.SerializerMethodField()
    percentage = serializers.SerializerMethodField()
    category_breakdown = serializers.SerializerMethodField()

    class Meta:
        model = ScoreReport
        fields = [
            'candidate',
            'test',
            'score',
            'total_positive',
            'total_negative',
            'total_correct',
            'total_wrong',
            'total_unattempted',
            'max_possible',
            'percentage',
            'category_breakdown',
            'created_at',
        ]

    def get_max_possible(self, obj):
        return float(obj.total_positive + obj.total_negative)

    def get_percentage(self, obj):
        max_marks = obj.total_positive + obj.total_negative
        if max_marks == 0:
            return 0.0
        return round((obj.score / max_marks) * 100, 2)

    def get_category_breakdown(self, obj):
        responses = Response.objects.filter(candidate=obj.candidate).select_related('question__category')

        breakdown = {}

        for r in responses:
            cat_name = r.question.category.name
            correct_answer = (r.question.correct_answer or "").strip().lower()
            submitted = (r.answer or "").strip().lower()

            if cat_name not in breakdown:
                breakdown[cat_name] = {
                    "correct": 0,
                    "wrong": 0,
                    "unattempted": 0,
                    "positive": 0.0,
                    "negative": 0.0
                }

            if not submitted:
                breakdown[cat_name]["unattempted"] += 1
            elif submitted == correct_answer:
                breakdown[cat_name]["correct"] += 1
                breakdown[cat_name]["positive"] += float(r.question.positive_marks or 0)
            else:
                breakdown[cat_name]["wrong"] += 1
                breakdown[cat_name]["negative"] += float(r.question.negative_marks or 0)

        return breakdown

class QuestionPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'text', 'question_type', 'options']

class SectionSerializer(serializers.Serializer):
    category = serializers.CharField()
    duration_minutes = serializers.IntegerField()
    questions = QuestionPublicSerializer(many=True)

class TestDetailSerializer(serializers.ModelSerializer):
    sections = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = [
            'id',
            'name',
            'total_duration_minutes',
            'enforce_section_time',
            'show_section_time_guidance',
            'sections',
        ]

    def get_sections(self, test):
        section_configs = test.sections.all().select_related('category')
        question_set = TestQuestionSet.objects.filter(test=test).select_related('question')

        categorized_questions = {}
        for qs in question_set:
            key = qs.question.category.id
            if key not in categorized_questions:
                categorized_questions[key] = []
            categorized_questions[key].append(qs.question)

        result = []
        for section in section_configs:
            section_questions = categorized_questions.get(section.category.id, [])
            result.append({
                "category": section.category.name,
                "duration_minutes": section.section_duration_minutes,
                "questions": QuestionPublicSerializer(section_questions, many=True).data
            })

        return result
