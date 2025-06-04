# ---- Export Evaluated Answers ---- #
@admin.action(description="Export evaluated answer sheets (Excel)")
def export_evaluated_answers(modeladmin, request, queryset):
    import io
    import zipfile
    import openpyxl
    from django.http import HttpResponse
    from openpyxl.styles import Font
    from django.utils.text import slugify
    from .models import Response, Question, TestQuestionSet

    files = []

    for report in queryset.select_related('candidate', 'test'):
        wb = openpyxl.Workbook()
        main_ws = wb.active
        main_ws.title = "Answer Sheet"
        summary_ws = wb.create_sheet(title="Category Summary")

        # === SHEET 1 HEADERS ===
        headers = [
            "#", "Category", "Difficulty", "Question",
            "Your Answer (Choice)", "Your Answer (Raw)",
            "Correct Answer (Choice)", "Correct Answer (Raw)",
            "Status", "+Marks", "-Marks", "Score Awarded", "Time Taken (s)"
        ]
        main_ws.append(headers)
        for cell in main_ws[1]:
            cell.font = Font(bold=True)

        tq_ids = TestQuestionSet.objects.filter(test=report.test).values_list('question_id', flat=True)
        questions = Question.objects.filter(id__in=tq_ids).select_related('category')

        responses = {
            r.question_id: r for r in Response.objects.filter(
                candidate=report.candidate,
                question_id__in=[q.id for q in questions]
            )
        }

        category_summary = {}

        def get_choice_letter(val, options):
            try:
                return chr(options.index(val) + ord('A'))
            except:
                return ""

        for i, q in enumerate(questions, start=1):
            r = responses.get(q.id)
            raw_submitted = (r.answer or "").strip() if r else ""
            raw_correct = (q.correct_answer or "").strip()

            try:
                opts = eval(q.options)
            except:
                opts = []

            submitted_choice = ",".join(
                get_choice_letter(val.strip(), opts) for val in raw_submitted.split(",") if val.strip()
            )
            correct_choice = ",".join(
                get_choice_letter(val.strip(), opts) for val in raw_correct.split(",") if val.strip()
            )

            status = "Unattempted"
            awarded = 0
            if raw_submitted:
                if sorted(raw_submitted.split(",")) == sorted(raw_correct.split(",")):
                    status = "Correct"
                    awarded = q.positive_marks
                else:
                    status = "Wrong"
                    awarded = -q.negative_marks

            cat = q.category.name
            if cat not in category_summary:
                category_summary[cat] = {
                    "total_qs": 0, "correct": 0, "wrong": 0,
                    "unattempted": 0, "positive": 0, "negative": 0,
                    "max_marks": 0
                }
            stats = category_summary[cat]
            stats["total_qs"] += 1
            stats["max_marks"] += q.positive_marks
            if status == "Correct":
                stats["correct"] += 1
                stats["positive"] += q.positive_marks
            elif status == "Wrong":
                stats["wrong"] += 1
                stats["negative"] += q.negative_marks
            else:
                stats["unattempted"] += 1

            main_ws.append([
                i,
                cat,
                q.difficulty,
                q.text[:200].replace("\n", " "),
                submitted_choice,
                raw_submitted,
                correct_choice,
                raw_correct,
                status,
                q.positive_marks,
                q.negative_marks,
                awarded,
                r.time_spent if r else ""
            ])

        summary_headers = [
            "Category", "Total", "Correct", "Wrong", "Unattempted",
            "Total +Marks", "Total -Marks", "Net Score", "Max Score", "Percentage"
        ]
        summary_ws.append(summary_headers)
        for cell in summary_ws[1]:
            cell.font = Font(bold=True)

        grand_total = {
            "total_qs": 0, "correct": 0, "wrong": 0, "unattempted": 0,
            "positive": 0, "negative": 0, "max_marks": 0
        }


        for cat, s in category_summary.items():
            net_score = s["positive"] - s["negative"]
            percent = (net_score / s["max_marks"] * 100) if s["max_marks"] else 0
            summary_ws.append([
                cat, s["total_qs"], s["correct"], s["wrong"], s["unattempted"],
                s["positive"], s["negative"], net_score, s["max_marks"], round(percent, 2)
            ])

            for key in grand_total:
                grand_total[key] += s.get(key, 0)

        g_net = grand_total["positive"] - grand_total["negative"]
        g_percent = (g_net / grand_total["max_marks"] * 100) if grand_total["max_marks"] else 0
        summary_ws.append([])
        summary_ws.append([
            "Grand Total", grand_total["total_qs"], grand_total["correct"], grand_total["wrong"],
            grand_total["unattempted"],
            grand_total["positive"], grand_total["negative"], g_net, grand_total["max_marks"], round(g_percent, 2)
        ])

        memfile = io.BytesIO()
        wb.save(memfile)
        memfile.seek(0)
        fname = f"{slugify(report.test.name)}_{slugify(report.candidate.name)}.xlsx"
        files.append((fname, memfile.read()))

    if len(files) == 1:
        name, content = files[0]
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f"attachment; filename={name}"
        return response
    else:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for name, content in files:
                zf.writestr(name, content)
        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.read(), content_type="application/zip")
        response["Content-Disposition"] = "attachment; filename=evaluated_answer_sheets.zip"
        return response