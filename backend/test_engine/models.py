from django.db import models
from django.utils import timezone


# ===================
# Shared Constants
# ===================
DIFFICULTY_LEVELS = [
    ('easy', 'Easy'),
    ('moderate', 'Moderate'),
    ('hard', 'Hard'),
]


# ===================
# Core Models
# ===================


class Test(models.Model):
    name = models.CharField(max_length=100)
    total_duration_minutes = models.IntegerField()
    enforce_section_time = models.BooleanField(default=False)
    show_section_time_guidance = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def total_section_time(self):
        return sum(section.section_duration_minutes for section in self.sections.all())

    def __str__(self):
        return self.name



class QuestionCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Question(models.Model):
    category = models.ForeignKey(QuestionCategory, on_delete=models.CASCADE)
    text = models.TextField()
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_LEVELS)
    question_type = models.CharField(max_length=50, default='MCQ')  # Optional for future
    options = models.TextField(help_text='Enter choices as JSON: ["A", "B", "C", "D"]')
    correct_answer = models.TextField()
    positive_marks = models.FloatField(default=1.0)
    negative_marks = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.category.name} | {self.difficulty} | {self.text[:50]}"


from django.core.exceptions import ValidationError

class TestSectionConfig(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='sections')
    category = models.ForeignKey(QuestionCategory, on_delete=models.CASCADE)
    easy_questions = models.PositiveIntegerField(default=0)
    moderate_questions = models.PositiveIntegerField(default=0)
    hard_questions = models.PositiveIntegerField(default=0)
    section_duration_minutes = models.PositiveIntegerField(default=10)

    def total_questions(self):
        return self.easy_questions + self.moderate_questions + self.hard_questions

    def save(self, *args, **kwargs):
        if not self.section_duration_minutes or self.section_duration_minutes == 0:
            total = self.easy_questions + self.moderate_questions + self.hard_questions
            self.section_duration_minutes = max(5, int(total * 1))  # Minimum 5 min
        super().save(*args, **kwargs)

    def clean(self):
        from .models import Question

        available_easy = Question.objects.filter(category=self.category, difficulty='easy').count()
        available_moderate = Question.objects.filter(category=self.category, difficulty='moderate').count()
        available_hard = Question.objects.filter(category=self.category, difficulty='hard').count()

        if self.easy_questions > available_easy:
            raise ValidationError(f"Only {available_easy} easy questions available in {self.category.name}")
        if self.moderate_questions > available_moderate:
            raise ValidationError(f"Only {available_moderate} moderate questions available in {self.category.name}")
        if self.hard_questions > available_hard:
            raise ValidationError(f"Only {available_hard} hard questions available in {self.category.name}")


class TestQuestionSet(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.IntegerField(default=0)  # to maintain consistent order

    def __str__(self):
        return f"{self.test.name} - Q{self.order + 1}"


class CandidateSectionQuestionOrder(models.Model):
    session = models.ForeignKey("CandidateTestSession", on_delete=models.CASCADE)
    section = models.ForeignKey('TestSectionConfig', on_delete=models.CASCADE)
    question = models.ForeignKey('Question', on_delete=models.CASCADE)
    display_order = models.PositiveIntegerField()

    class Meta:
        unique_together = ('session', 'section', 'question')
        ordering = ['display_order']



# ===================
# Candidate & Reports
# ===================
class Candidate(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    secret_code_1 = models.CharField(max_length=50)
    secret_code_2 = models.CharField(max_length=50)

    def __str__(self):
        return self.name


# ===================
# Candidate Response & Scoring
# ===================

class Response(models.Model):
    candidate = models.ForeignKey("Candidate", on_delete=models.CASCADE)
    test = models.ForeignKey("Test", on_delete=models.CASCADE)
    question = models.ForeignKey("Question", on_delete=models.CASCADE)
    answer = models.TextField(blank=True)
    time_spent = models.PositiveIntegerField(default=0)
    marked_for_review = models.BooleanField(default=False)
    revisit_count = models.PositiveIntegerField(default=0)
    answered_at = models.DateTimeField(auto_now=True)
    attempt_number = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.candidate} - Q{self.question.id}"

    class Meta:
        unique_together = ("candidate", "question", "test", "attempt_number")

class ArchivedResponse(models.Model):
    candidate = models.ForeignKey("Candidate", on_delete=models.CASCADE)
    test = models.ForeignKey("Test", on_delete=models.CASCADE)
    question = models.ForeignKey("Question", on_delete=models.CASCADE)
    answer = models.TextField(blank=True)
    time_spent = models.PositiveIntegerField(default=0)
    marked_for_review = models.BooleanField(default=False)
    revisit_count = models.PositiveIntegerField(default=0)
    answered_at = models.DateTimeField()
    attempt_number = models.PositiveIntegerField(default=1)
    archived_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Archived Q{self.question.id} | {self.candidate}"


class ScoreReport(models.Model):
    candidate = models.ForeignKey("Candidate", on_delete=models.CASCADE)
    test = models.ForeignKey("Test", on_delete=models.CASCADE)
    attempt_number = models.PositiveIntegerField(default=1)

    score = models.DecimalField(max_digits=6, decimal_places=2)
    max_score = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)  # ✅ Add
    total_positive = models.DecimalField(max_digits=6, decimal_places=2)
    total_negative = models.DecimalField(max_digits=6, decimal_places=2)
    total_correct = models.PositiveIntegerField()
    total_wrong = models.PositiveIntegerField()
    total_unattempted = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)  # ✅ Add

    class Meta:
        unique_together = ("candidate", "test", "attempt_number")


# --- Test Assignment & Session  ---

class TestAssignment(models.Model):
    candidate = models.ForeignKey("Candidate", on_delete=models.CASCADE)
    test = models.ForeignKey("Test", on_delete=models.CASCADE)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField(null=True, blank=True)
    max_attempts = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.candidate} → {self.test}"

    class Meta:
        unique_together = ("candidate", "test")

class CandidateTestSession(models.Model):
    assignment = models.ForeignKey(TestAssignment, on_delete=models.CASCADE)
    attempt_number = models.PositiveIntegerField(default=1)
    started_at = models.DateTimeField(default=timezone.now)
    completed = models.BooleanField(default=False)
    current_section = models.ForeignKey("TestSectionConfig", on_delete=models.SET_NULL, null=True, blank=True)
    section_started_at = models.DateTimeField(null=True, blank=True)
    screen_ok = models.BooleanField(default=True)  # Add this if missing
    test_completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Session {self.assignment} - Attempt {self.attempt_number}"

    class Meta:
        unique_together = ("assignment", "attempt_number")


class SectionStatus(models.Model):
    session = models.ForeignKey(CandidateTestSession, on_delete=models.CASCADE)
    section = models.ForeignKey("TestSectionConfig", on_delete=models.CASCADE)
    started_at = models.DateTimeField()
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    auto_submitted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.session.assignment} - {self.section.category.name}"

    class Meta:
        unique_together = ("session", "section")
