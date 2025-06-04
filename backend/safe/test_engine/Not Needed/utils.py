from .models import Response, ScoreReport, Question


def score_candidate_test(candidate_id, test_id):
    responses = Response.objects.filter(candidate_id=candidate_id,
                                        question__category__testsectionconfig__test_id=test_id).select_related(
        'question')

    total_score = 0
    total_possible = 0

    for r in responses:
        q = r.question
        correct = q.correct_answer.strip().lower()
        user = r.answer.strip().lower()

        if user == correct:
            total_score += q.positive_marks
        else:
            total_score -= q.negative_marks

        total_possible += q.positive_marks

    # Round to 2 decimal places
    total_score = round(total_score, 2)
    total_possible = round(total_possible, 2)

    report, _ = ScoreReport.objects.update_or_create(
        candidate_id=candidate_id,
        test_id=test_id,
        defaults={
            'score': total_score,
            'total': total_possible
        }
    )
    return report
