from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors

if TYPE_CHECKING:
    from app.schemas.teacher_package import TeacherKnowledgePackage


def _ensure_package_dir(package_id: str) -> Path:
    from app.config import get_settings

    settings = get_settings()
    packages_dir = Path(settings.packages_dir)
    package_dir = packages_dir / package_id
    package_dir.mkdir(parents=True, exist_ok=True)
    return package_dir


def _build_styles() -> dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="SectionTitle",
        parent=styles["Heading2"],
        spaceAfter=12,
        leading=18,
    ))
    styles.add(ParagraphStyle(
        name="Subheading",
        parent=styles["Heading4"],
        spaceAfter=8,
        leading=14,
    ))
    styles.add(ParagraphStyle(
        name="CustomBodyText",
        parent=styles["BodyText"],
        spaceAfter=8,
        leading=15,
    ))
    styles.add(ParagraphStyle(
        name="ListItem",
        parent=styles["CustomBodyText"],
        leftIndent=12,
        bulletIndent=0,
        spaceAfter=4,
        leading=14,
    ))
    return styles


def _render_table(story: list, title: str, rows: list[list[str]], styles: dict[str, ParagraphStyle]) -> None:
    if not rows:
        return
    story.append(Paragraph(title, styles["Subheading"]))
    table = Table(rows, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0d0d0")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(table)
    story.append(Spacer(1, 12))


def _build_list(story: list, title: str, items: list[str], styles: dict[str, ParagraphStyle]) -> None:
    if not items:
        return
    story.append(Paragraph(title, styles["Subheading"]))
    for item in items:
        story.append(Paragraph(f"• {item}", styles["ListItem"]))
    story.append(Spacer(1, 12))


def _build_section(story: list, heading: str, content: str, styles: dict[str, ParagraphStyle]) -> None:
    if content:
        story.append(Paragraph(heading, styles["Subheading"]))
        story.append(Paragraph(content.replace("\n", "<br/>"), styles["CustomBodyText"]))
        story.append(Spacer(1, 10))


def export_lesson_plan(pkg: "TeacherKnowledgePackage") -> Path:
    package_dir = _ensure_package_dir(pkg.package_id)
    target = package_dir / "lesson_plan.pdf"
    styles = _build_styles()
    doc = SimpleDocTemplate(
        str(target),
        pagesize=letter,
        rightMargin=inch * 0.5,
        leftMargin=inch * 0.5,
        topMargin=inch * 0.75,
        bottomMargin=inch * 0.75,
    )
    story: list = [Paragraph("Teacher Lesson Plan", styles["Heading1"])]
    story.append(Paragraph(f"Package ID: {pkg.package_id}", styles["CustomBodyText"]))
    story.append(Paragraph(f"Subject: {pkg.metadata.subject}", styles["CustomBodyText"]))
    story.append(Paragraph(f"Topic: {pkg.metadata.topic}", styles["CustomBodyText"]))
    story.append(Spacer(1, 16))

    for lesson in pkg.lessons:
        story.append(Paragraph(f"Period {lesson.period_number}: {lesson.title}", styles["SectionTitle"]))
        _build_section(story, "Entry Ticket", lesson.entry_ticket, styles)
        _build_section(story, "Teacher Script", lesson.teacher_script, styles)
        _build_section(story, "Blackboard Notes", lesson.blackboard_notes, styles)
        _build_list(story, "Classroom Activities", lesson.classroom_activities, styles)
        _build_list(story, "Checkpoint Questions", lesson.checkpoint_questions, styles)
        _build_section(story, "Exit Ticket", lesson.exit_ticket, styles)
        _build_section(story, "Homework", lesson.homework, styles)
        _build_section(story, "Mentor Moment", lesson.mentor_moment, styles)
        story.append(PageBreak())

    doc.build(story)
    return target


def export_teacher_guide(pkg: "TeacherKnowledgePackage") -> Path:
    package_dir = _ensure_package_dir(pkg.package_id)
    target = package_dir / "teacher_guide.pdf"
    styles = _build_styles()
    doc = SimpleDocTemplate(
        str(target),
        pagesize=letter,
        rightMargin=inch * 0.5,
        leftMargin=inch * 0.5,
        topMargin=inch * 0.75,
        bottomMargin=inch * 0.75,
    )
    story: list = [Paragraph("Teacher Guide", styles["Heading1"])]
    story.append(Paragraph(f"Subject: {pkg.metadata.subject}", styles["CustomBodyText"]))
    story.append(Paragraph(f"Topic: {pkg.metadata.topic}", styles["CustomBodyText"]))
    story.append(Paragraph(f"Grade: {pkg.metadata.grade}", styles["CustomBodyText"]))
    story.append(Spacer(1, 16))

    _build_list(story, "Learning Objectives", pkg.learning_objectives, styles)
    _build_list(story, "Prerequisites", pkg.prerequisites, styles)

    def _build_object_list(title: str, items: list[dict[str, any]]) -> None:
        if not items:
            return
        story.append(Paragraph(title, styles["SectionTitle"]))
        for item in items:
            if title == "Concepts":
                story.append(Paragraph(f"<strong>{item.name}</strong>: {item.explanation}", styles["CustomBodyText"]))
            elif title == "Definitions":
                story.append(Paragraph(f"<strong>{item.term}</strong>: {item.definition}", styles["CustomBodyText"]))
            elif title == "Formulae":
                story.append(Paragraph(f"<strong>{item.name}</strong>: {item.expression}", styles["CustomBodyText"]))
                if getattr(item, "description", None):
                    story.append(Paragraph(item.description, styles["CustomBodyText"]))
            elif title == "Examples":
                story.append(Paragraph(f"<strong>{item.title}</strong>: {item.description}", styles["CustomBodyText"]))
            elif title == "Applications":
                story.append(Paragraph(f"<strong>{item.domain}</strong>: {item.description}", styles["CustomBodyText"]))
            story.append(Spacer(1, 6))
        story.append(Spacer(1, 12))

    _build_object_list("Concepts", pkg.concepts)
    _build_object_list("Definitions", pkg.definitions)
    _build_object_list("Formulae", pkg.formulae)
    _build_object_list("Examples", pkg.examples)
    _build_object_list("Applications", pkg.applications)

    if pkg.misconceptions:
        story.append(Paragraph("Misconceptions and Remedial Actions", styles["SectionTitle"]))
        for item in pkg.misconceptions:
            story.append(Paragraph(f"<strong>{item.misconception}</strong>", styles["CustomBodyText"]))
            story.append(Paragraph(f"Correct understanding: {item.correct_understanding}", styles["CustomBodyText"]))
            story.append(Paragraph(f"Remedial action: {item.remedial_action}", styles["CustomBodyText"]))
            story.append(Spacer(1, 8))

    doc.build(story)
    return target


def export_assessment_book(pkg: "TeacherKnowledgePackage") -> Path:
    package_dir = _ensure_package_dir(pkg.package_id)
    target = package_dir / "assessment_book.pdf"
    styles = _build_styles()
    doc = SimpleDocTemplate(
        str(target),
        pagesize=letter,
        rightMargin=inch * 0.5,
        leftMargin=inch * 0.5,
        topMargin=inch * 0.75,
        bottomMargin=inch * 0.75,
    )
    story: list = [Paragraph("Assessment Book", styles["Heading1"])]
    story.append(Paragraph(f"Subject: {pkg.metadata.subject}", styles["CustomBodyText"]))
    story.append(Paragraph(f"Topic: {pkg.metadata.topic}", styles["CustomBodyText"]))
    story.append(Spacer(1, 16))

    if pkg.assessments:
        if pkg.assessments.mcqs:
            story.append(Paragraph("Multiple Choice Questions", styles["SectionTitle"]))
            for idx, mcq in enumerate(pkg.assessments.mcqs, start=1):
                story.append(Paragraph(f"Q{idx}. {mcq.question}", styles["CustomBodyText"]))
                for opt_idx, opt in enumerate(mcq.options):
                    option_label = chr(65 + opt_idx)
                    story.append(Paragraph(f"{option_label}. {opt}", styles["ListItem"]))
                story.append(Paragraph(f"Answer: {chr(65 + mcq.correct_option)}", styles["CustomBodyText"]))
                story.append(Paragraph(f"Explanation: {mcq.explanation}", styles["CustomBodyText"]))
                story.append(Spacer(1, 10))
            story.append(PageBreak())

        if pkg.assessments.short_answers:
            story.append(Paragraph("Short Answer Questions", styles["SectionTitle"]))
            for idx, item in enumerate(pkg.assessments.short_answers, start=1):
                story.append(Paragraph(f"Q{idx}. {item.question}", styles["CustomBodyText"]))
                story.append(Paragraph(f"Model answer: {item.model_answer}", styles["CustomBodyText"]))
                story.append(Paragraph(f"Rubric: {item.rubric}", styles["CustomBodyText"]))
                story.append(Spacer(1, 10))

        if pkg.assessments.long_answers:
            story.append(Paragraph("Long Answer Questions", styles["SectionTitle"]))
            for idx, item in enumerate(pkg.assessments.long_answers, start=1):
                story.append(Paragraph(f"Q{idx}. {item.question}", styles["CustomBodyText"]))
                story.append(Paragraph(f"Model answer: {item.model_answer}", styles["CustomBodyText"]))
                story.append(Paragraph(f"Rubric: {item.rubric}", styles["CustomBodyText"]))
                story.append(Spacer(1, 10))

        if pkg.assessments.numerical:
            story.append(Paragraph("Numerical Problems", styles["SectionTitle"]))
            for idx, item in enumerate(pkg.assessments.numerical, start=1):
                story.append(Paragraph(f"Q{idx}. {item.question}", styles["CustomBodyText"]))
                story.append(Paragraph(f"Solution steps:", styles["CustomBodyText"]))
                for step in item.solution_steps:
                    story.append(Paragraph(f"• {step}", styles["ListItem"]))
                story.append(Paragraph(f"Final answer: {item.final_answer}", styles["CustomBodyText"]))
                story.append(Spacer(1, 10))

    story.append(PageBreak())
    story.append(Paragraph("Answer Key and Explanations", styles["Heading1"]))
    if pkg.assessments:
        if pkg.assessments.mcqs:
            story.append(Paragraph("MCQ Answer Key", styles["SectionTitle"]))
            rows = [["Q", "Answer", "Explanation"]]
            for idx, mcq in enumerate(pkg.assessments.mcqs, start=1):
                rows.append([str(idx), chr(65 + mcq.correct_option), mcq.explanation])
            _render_table(story, "MCQ Answer Key", rows, styles)
        if pkg.assessments.short_answers:
            story.append(Paragraph("Short Answer Key", styles["SectionTitle"]))
            for idx, item in enumerate(pkg.assessments.short_answers, start=1):
                story.append(Paragraph(f"Q{idx}. {item.model_answer}", styles["CustomBodyText"]))
        if pkg.assessments.long_answers:
            story.append(Paragraph("Long Answer Key", styles["SectionTitle"]))
            for idx, item in enumerate(pkg.assessments.long_answers, start=1):
                story.append(Paragraph(f"Q{idx}. {item.model_answer}", styles["CustomBodyText"]))
        if pkg.assessments.numerical:
            story.append(Paragraph("Numerical Solutions", styles["SectionTitle"]))
            for idx, item in enumerate(pkg.assessments.numerical, start=1):
                story.append(Paragraph(f"Q{idx}. {item.final_answer}", styles["CustomBodyText"]))
    doc.build(story)
    return target


def export_package_pdfs(pkg: "TeacherKnowledgePackage") -> dict[str, Path]:
    lesson_path = export_lesson_plan(pkg)
    teacher_path = export_teacher_guide(pkg)
    assessment_path = export_assessment_book(pkg)
    return {
        "lesson_plan_pdf_path": lesson_path,
        "teacher_guide_pdf_path": teacher_path,
        "assessment_book_pdf_path": assessment_path,
    }
