import os
import re
import json
from io import BytesIO
from datetime import datetime
import pandas as pd
from django.conf import settings
from django.utils.text import slugify
from decimal import Decimal
from collections import defaultdict
from django.db import transaction

from ..models import (
    Response, ScoreReport, Test, Candidate,
    TestQuestionSet, TestSectionConfig, Question
)


@transaction.atomic
def calculate_score_for_candidate(test: Test, candidate: Candidate, attempt_number: int):
    print(f"\n🧠 Scoring for: {candidate.name} | Test: {test.name} | Attempt #{attempt_number}")

    # Fetch all questions used in this test
    test_questions_qs = TestQuestionSet.objects.filter(test=test).select_related('question')
    all_questions = [tq.question for tq in test_questions_qs]
    question_map = {q.id: q for q in all_questions}

    total_max_score = Decimal(sum(Decimal(q.positive_marks) for q in all_questions))

    # Organize questions by section (using category match)
    section_summary = {}
    section_map = {}
    for section in TestSectionConfig.objects.filter(test=test).select_related('category'):
        section_questions = [q for q in all_questions if q.category_id == section.category_id]
        section_id = section.id
        section_map[section_id] = section

        section_summary[section_id] = {
            "section_name": section.category.name,
            "score": Decimal("0.0"),
            "max_score": Decimal(sum(q.positive_marks for q in section_questions)),
            "correct": 0,
            "wrong": 0,
            "unattempted": 0,
        }

    # Load responses
    responses = Response.objects.filter(
        candidate=candidate,
        test=test,
        attempt_number=attempt_number
    ).select_related('question__category')

    print(f"✅ Found {responses.count()} responses")

    total_score = Decimal('0.0')
    total_positive = Decimal('0.0')
    total_negative = Decimal('0.0')
    total_correct = 0
    total_wrong = 0
    total_unattempted = 0

    for r in responses:
        q = question_map.get(r.question_id)
        if not q:
            continue  # Skip any question not in test

        submitted = (r.answer or "").strip().lower()
        correct = (q.correct_answer or "").strip().lower()
        section_id = next((sid for sid, sec in section_map.items() if sec.category_id == q.category_id), None)

        if not submitted:
            total_unattempted += 1
            if section_id:
                section_summary[section_id]["unattempted"] += 1
            continue

        if submitted == correct:
            marks = Decimal(str(q.positive_marks or 1.0))
            total_score += marks
            total_positive += marks
            total_correct += 1
            if section_id:
                section_summary[section_id]["score"] += marks
                section_summary[section_id]["correct"] += 1
            print(f"Q{q.id}: ✅ Correct (+{marks})")
        else:
            penalty = Decimal(str(q.negative_marks or 0.0))
            total_score -= penalty
            total_negative += penalty
            total_wrong += 1
            if section_id:
                section_summary[section_id]["score"] -= penalty
                section_summary[section_id]["wrong"] += 1
            print(f"Q{q.id}: ❌ Incorrect (-{penalty})")

    # Save to ScoreReport
    report, _ = ScoreReport.objects.update_or_create(
        test=test,
        candidate=candidate,
        attempt_number=attempt_number,
        defaults={
            'score': total_score,
            'max_score': total_max_score,
            'total_positive': total_positive,
            'total_negative': total_negative,
            'total_correct': total_correct,
            'total_wrong': total_wrong,
            'total_unattempted': total_unattempted,
        }
    )

    print(f"💾 Final Score: {total_score} / Max Possible: {total_max_score}")
    print(f"🟢 Correct: {total_correct}, 🔴 Wrong: {total_wrong}, ⚪ Unattempted: {total_unattempted}\n")

    # Add percentage to each section
    for sid, sec in section_summary.items():
        sec["percentage"] = round(
            float(sec["score"]) / float(sec["max_score"]) * 100 if sec["max_score"] else 0.0,
            2
        )

    return {
        "report": report,
        "section_summary": section_summary
    }


def serialize_score_report(report: ScoreReport, section_summary=None) -> dict:
    test = report.test
    candidate = report.candidate

    data = {
        "candidate_id": candidate.id,
        "name": candidate.name,
        "email": candidate.email,
        "phone": candidate.phone,
        "test_id": test.id,
        "test_name": test.name,
        "attempt_number": report.attempt_number,
        "score": float(report.score),
        "max_score": float(report.max_score),
        "percentage": round((report.score / report.max_score) * 100, 2) if report.max_score else 0.0,
        "total_correct": report.total_correct,
        "total_wrong": report.total_wrong,
        "total_unattempted": report.total_unattempted,
        "section_summary": {},
        "category_summary": {},
    }

    if section_summary:
        for sec_id, sec in section_summary.items():
            data["section_summary"][sec["section_name"]] = {
                "score": float(sec["score"]),
                "max_score": float(sec["max_score"]),
                "percentage": sec["percentage"],
                "correct": sec["correct"],
                "wrong": sec["wrong"],
                "unattempted": sec["unattempted"],
            }

    from collections import defaultdict
    from ..models import Response

    category_data = defaultdict(lambda: {
        "score": 0,
        "correct": 0,
        "wrong": 0,
        "unattempted": 0,
        "max_score": 0,
    })

    responses = Response.objects.filter(
        candidate=candidate,
        test=test,
        attempt_number=report.attempt_number
    ).select_related('question__category')

    for resp in responses:
        q = resp.question
        cat = q.category.name if q.category else "Uncategorized"
        category_data[cat]["max_score"] += q.positive_marks

        if resp.answer.strip() == "":
            category_data[cat]["unattempted"] += 1
        elif resp.answer.strip().lower() == q.correct_answer.strip().lower():
            category_data[cat]["correct"] += 1
            category_data[cat]["score"] += q.positive_marks
        else:
            category_data[cat]["wrong"] += 1
            category_data[cat]["score"] -= q.negative_marks

    for cat, stats in category_data.items():
        stats["percentage"] = round((stats["score"] / stats["max_score"] * 100), 2) if stats["max_score"] else 0.0
        data["category_summary"][cat] = stats

    return data


def generate_score_report_excel(candidate, test, attempt_number, report_data):
    # Paths
    base_path = os.path.join(settings.MEDIA_ROOT, "scores")
    os.makedirs(base_path, exist_ok=True)

    # Build base filename
    base_filename = f"score_{slugify(candidate.name)}_{slugify(test.name)}_attempt{attempt_number}"

    # Determine next available version
    existing_files = [f for f in os.listdir(base_path) if f.startswith(base_filename)]
    versions = [int(re.search(r"_v(\d+)\.xlsx", f).group(1)) for f in existing_files if re.search(r"_v(\d+)\.xlsx", f)]
    next_version = max(versions, default=0) + 1

    filename = f"{base_filename}_v{next_version}.xlsx"
    full_path = os.path.join(base_path, filename)

    # Sheet 1: Summary
    max_score = sum(s.get("max_score", 0) for s in report_data.get("section_summary", {}).values())

    summary_data = {
        "Candidate Name": candidate.name,
        "Email": candidate.email,
        "Test": test.name,
        "Attempt": attempt_number,
        "Total Score": report_data['score'],
        "Max Score": max_score,
        "% Score": round(report_data['score'] / max_score * 100, 2) if max_score else 0,
    }

    for section_name, section in report_data.get("section_summary", {}).items():
        key = f"Section: {section_name}"
        summary_data[f"{key} Score"] = section['score']
        summary_data[f"{key} Max"] = section['max_score']
        summary_data[f"{key} %"] = section['percentage']

    df_summary = pd.DataFrame([summary_data])

    # Sheet 2: Detailed Audit
    def get_choice_letter(raw, options):
        if not raw or not options:
            return ""
        try:
            values = [v.strip() for v in raw.split(",")]
            letters = []
            for val in values:
                if val in options:
                    letters.append(chr(ord("A") + options.index(val)))
            return ",".join(letters)
        except:
            return ""

    responses = Response.objects.filter(candidate=candidate, test=test, attempt_number=attempt_number)

    section_lookup = {
        s.category_id: f"Section {i + 1}: {s.category.name}"
        for i, s in enumerate(TestSectionConfig.objects.filter(test=test).select_related("category"))
    }

    audit_rows = []
    for r in responses.select_related('question'):
        q = r.question
        audit_rows.append({
            "Section": section_lookup.get(q.category_id, ""),
            "Category": q.category.name if q.category else "",
            "Question ID": q.id,
            "Question": str(q.text)[:100],
            "Your Answer (Raw)": r.answer,
            "Your Answer (Choice)": get_choice_letter(r.answer, json.loads(q.options)),
            "Correct Answer (Raw)": q.correct_answer,
            "Correct Answer (Choice)": get_choice_letter(q.correct_answer, json.loads(q.options)),
            "Evaluation": (
                    "Unattempted" if not r.answer else
                    "Correct" if r.answer.strip().lower() == (q.correct_answer or "").strip().lower()
                    else "Wrong"
                ),
            "Marks Awarded": (
                    q.positive_marks if r.answer and r.answer.strip().lower() == (q.correct_answer or "").strip().lower()
                    else -q.negative_marks if r.answer
                    else 0
                ),
            "Positive Marks": q.positive_marks,
            "Negative Marks": q.negative_marks,
        })

    df_audit = pd.DataFrame(audit_rows)

    with pd.ExcelWriter(full_path, engine='openpyxl') as writer:
        df_summary.to_excel(writer, index=False, sheet_name="Score Summary")
        df_audit.to_excel(writer, index=False, sheet_name="Detailed Audit")

    return full_path


