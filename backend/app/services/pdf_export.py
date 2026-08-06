"""Professional PDF generation for Teacher Knowledge Packages.

Uses a Unicode TrueType font (Arial) so Greek symbols, subscripts, and
superscripts render correctly. Implements proper margins, headings,
page numbering, aligned tables, automatic page breaks, and section
separators to produce publication-quality documents.
"""
from __future__ import annotations
import html
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    Frame, PageTemplate, HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors

from app.utils.text_utils import normalize_scientific

if TYPE_CHECKING:
    from app.schemas.teacher_package import TeacherKnowledgePackage


# ─────────────────────────── Font registration ───────────────────────────

_FONT_REGISTERED = False
_FONT_NAME = "Helvetica"
_FONT_NAME_BOLD = "Helvetica-Bold"


def _find_font_candidates() -> list[str]:
    """Return a list of candidate TrueType font paths present on the system."""
    windir = os.environ.get("WINDIR", r"C:\Windows")
    candidates = [
        os.path.join(windir, "Fonts", "arial.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    return [p for p in candidates if p and os.path.exists(p)]


def _register_fonts() -> None:
    """Register a Unicode TrueType font family if available."""
    global _FONT_REGISTERED, _FONT_NAME, _FONT_NAME_BOLD
    if _FONT_REGISTERED:
        return

    font_path = _find_font_candidates()
    if font_path:
        try:
            pdfmetrics.registerFont(TTFont("AppUnicode", font_path[0]))
            # Try to register a bold variant
            windir = os.environ.get("WINDIR", r"C:\Windows")
            bold_candidates = [
                os.path.join(windir, "Fonts", "arialbd.ttf"),
                font_path[0].replace("Sans.ttf", "Sans-Bold.ttf").replace("Regular", "Bold"),
            ]
            for bold in bold_candidates:
                if os.path.exists(bold):
                    pdfmetrics.registerFont(TTFont("AppUnicode-Bold", bold))
                    break
            _FONT_NAME = "AppUnicode"
            _FONT_NAME_BOLD = "AppUnicode-Bold" if pdfmetrics.getRegisteredFontNames().__contains__("AppUnicode-Bold") else "AppUnicode"
        except Exception:
            # Fall back to built-in Helvetica
            _FONT_NAME = "Helvetica"
            _FONT_NAME_BOLD = "Helvetica-Bold"

    _FONT_REGISTERED = True


def _ensure_package_dir(package_id: str) -> Path:
    from app.config import get_settings

    settings = get_settings()
    packages_dir = Path(settings.packages_dir)
    package_dir = packages_dir / package_id
    package_dir.mkdir(parents=True, exist_ok=True)
    return package_dir


def _safe_filename(name: str) -> str:
    """Sanitize a string for use in a filename."""
    name = re.sub(r'[\\/:*?"<>|]+', "", name)
    name = re.sub(r"\s+", "_", name)
    return name.strip("._") or "Document"


def _build_filename(pkg: "TeacherKnowledgePackage", suffix: str) -> str:
    """Build a professional filename: <Subject>_<Topic>_<Suffix>.pdf"""
    subject = _safe_filename(pkg.metadata.subject or "Subject")
    topic = _safe_filename(pkg.metadata.topic or "Topic")
    return f"{subject}_{topic}_{suffix}.pdf"


def _stringify_blackboard(notes) -> str:
    """Convert BlackboardNotes (object or str) into a display string."""
    if isinstance(notes, str):
        return notes
    if notes is None:
        return ""
    parts = []
    if getattr(notes, "main_definition", None):
        parts.append(f"Main definition: {notes.main_definition}")
    if getattr(notes, "key_points", None):
        parts.append("Key points:\n" + "\n".join(f"• {p}" for p in notes.key_points))
    if getattr(notes, "formulas", None):
        parts.append("Formulas:\n" + "\n".join(f"• {f}" for f in notes.formulas))
    if getattr(notes, "examples", None):
        parts.append("Examples:\n" + "\n".join(f"• {e}" for e in notes.examples))
    if getattr(notes, "diagrams", None):
        parts.append("Diagrams:\n" + "\n".join(f"• {d}" for d in notes.diagrams))
    return "\n".join(parts)


# ─────────────────────────── Style helpers ───────────────────────────

def _build_styles() -> dict[str, ParagraphStyle]:
    _register_fonts()
    styles = getSampleStyleSheet()

    # getSampleStyleSheet returns a StyleSheet1; copy into a plain dict for type safety.
    style_dict: dict[str, ParagraphStyle] = {k: styles[k] for k in styles.byName}

    def _add(style: ParagraphStyle) -> None:
        style_dict[style.name] = style

    _add(ParagraphStyle(
        name="DocTitle",
        fontName=_FONT_NAME_BOLD,
        fontSize=22,
        leading=26,
        spaceAfter=6,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1a1a2e"),
    ))
    _add(ParagraphStyle(
        name="DocSubtitle",
        fontName=_FONT_NAME,
        fontSize=11,
        leading=15,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#555"),
    ))
    _add(ParagraphStyle(
        name="SectionTitle",
        fontName=_FONT_NAME_BOLD,
        fontSize=15,
        leading=19,
        spaceBefore=14,
        spaceAfter=8,
        textColor=colors.HexColor("#1a1a2e"),
    ))
    _add(ParagraphStyle(
        name="Subheading",
        fontName=_FONT_NAME_BOLD,
        fontSize=11,
        leading=15,
        spaceBefore=8,
        spaceAfter=4,
        textColor=colors.HexColor("#333"),
    ))
    _add(ParagraphStyle(
        name="BodyText",
        fontName=_FONT_NAME,
        fontSize=10,
        leading=15,
        spaceAfter=6,
        alignment=TA_LEFT,
    ))
    _add(ParagraphStyle(
        name="Bullet",
        parent=style_dict["BodyText"],
        leftIndent=18,
        bulletIndent=6,
        spaceAfter=3,
    ))
    _add(ParagraphStyle(
        name="QuestionText",
        fontName=_FONT_NAME_BOLD,
        fontSize=10.5,
        leading=15,
        spaceBefore=8,
        spaceAfter=4,
    ))
    _add(ParagraphStyle(
        name="SmallText",
        fontName=_FONT_NAME,
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#666"),
    ))
    _add(ParagraphStyle(
        name="HeaderFooter",
        fontName=_FONT_NAME,
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#888"),
    ))
    return style_dict


class _ReportDoc(SimpleDocTemplate):
    """Document template with header/footer and page numbers."""

    def __init__(self, filename: str, title: str, styles: dict[str, ParagraphStyle]):
        _register_fonts()
        super().__init__(
            filename,
            pagesize=letter,
            rightMargin=inch * 0.85,
            leftMargin=inch * 0.85,
            topMargin=inch * 1.0,
            bottomMargin=inch * 0.9,
            title=title,
            author="GuruZ AI Teacher Platform",
        )
        self._title = title
        self._styles = styles

        frame = Frame(
            self.leftMargin, self.bottomMargin, self.width, self.height, id="normal"
        )
        template = PageTemplate(
            id="main", frames=[frame], onPage=self._header_footer
        )
        self.addPageTemplates([template])

    def _header_footer(self, canvas, doc):
        canvas.saveState()
        # Header
        header = Paragraph(self._title, self._styles["HeaderFooter"])
        w, h = header.wrap(doc.width, doc.topMargin)
        header.drawOn(canvas, doc.leftMargin, doc.height + doc.topMargin - h - 6)
        # Header rule
        canvas.setStrokeColor(colors.HexColor("#cccccc"))
        canvas.setLineWidth(0.5)
        canvas.line(doc.leftMargin, doc.height + doc.topMargin - h - 12,
                    doc.leftMargin + doc.width, doc.height + doc.topMargin - h - 12)

        # Footer with page number
        footer = Paragraph(f"Page {doc.page}", self._styles["HeaderFooter"])
        w, h = footer.wrap(doc.width, doc.bottomMargin)
        footer.drawOn(canvas, doc.leftMargin, h - 4)
        canvas.restoreState()


# ─────────────────────────── Rendering helpers ───────────────────────────

def _clean(text: str) -> str:
    """Normalize scientific notation and escape for ReportLab."""
    if not text:
        return ""
    text = normalize_scientific(text)
    text = html.escape(text, quote=False)
    return text.replace("\n", "<br/>")


def _add_section(story, styles, title: str, content: str) -> None:
    if not content:
        return
    story.append(Paragraph(title, styles["SectionTitle"]))
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#cccccc"), spaceAfter=6))
    story.append(Paragraph(_clean(content), styles["BodyText"]))
    story.append(Spacer(1, 8))


def _add_list(story, styles, title: str, items: list) -> None:
    if not items:
        return
    story.append(Paragraph(title, styles["Subheading"]))
    for item in items:
        story.append(Paragraph(f"• {_clean(str(item))}", styles["Bullet"]))
    story.append(Spacer(1, 6))


def _add_table(story, styles, title: str, rows: list[list[str]], col_widths: Optional[list] = None) -> None:
    if not rows:
        return
    story.append(Paragraph(title, styles["Subheading"]))
    table = Table(rows, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#b0b0b0")),
        ("FONTNAME", (0, 0), (-1, 0), _FONT_NAME_BOLD),
        ("FONTNAME", (0, 1), (-1, -1), _FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
    ]))
    story.append(table)
    story.append(Spacer(1, 10))


def _add_cover(story, styles, pkg: "TeacherKnowledgePackage", subtitle: str) -> None:
    """Render a professional cover/title block."""
    story.append(Paragraph(_clean(pkg.metadata.subject or "Educational Package"), styles["DocTitle"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(_clean(pkg.metadata.topic or ""), styles["DocSubtitle"]))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="60%", thickness=1.2, color=colors.HexColor("#1a1a2e"), spaceAfter=14))
    meta_lines = []
    if pkg.metadata.grade:
        meta_lines.append(f"Grade: {_clean(pkg.metadata.grade)}")
    if pkg.metadata.difficulty:
        meta_lines.append(f"Difficulty: {_clean(pkg.metadata.difficulty.capitalize())}")
    if pkg.metadata.language:
        meta_lines.append(f"Language: {_clean(pkg.metadata.language)}")
    if pkg.metadata.total_pages:
        meta_lines.append(f"Source pages: {pkg.metadata.total_pages}")
    if meta_lines:
        story.append(Paragraph(" &nbsp;&nbsp;|&nbsp;&nbsp; ".join(meta_lines), styles["DocSubtitle"]))
    story.append(Spacer(1, 16))


# ─────────────────────────── Document exporters ───────────────────────────

def export_lesson_plan(pkg: "TeacherKnowledgePackage") -> Path:
    package_dir = _ensure_package_dir(pkg.package_id)
    target = package_dir / _build_filename(pkg, "LessonPlan")
    styles = _build_styles()
    doc = _ReportDoc(str(target), f"Lesson Plan — {pkg.metadata.subject}", styles)
    story: list = []

    _add_cover(story, styles, pkg, "Lesson Plan")

    # Teaching plan overview
    if pkg.teaching_plan and pkg.teaching_plan.overview:
        _add_section(story, styles, "Teaching Overview", pkg.teaching_plan.overview)

    _add_list(story, styles, "Learning Objectives", pkg.learning_objectives)

    for lesson in pkg.lessons:
        story.append(PageBreak())
        story.append(Paragraph(
            f"Period {lesson.period_number}: {_clean(lesson.title)}",
            styles["SectionTitle"],
        ))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1a1a2e"), spaceAfter=8))
        _add_list(story, styles, "Objectives", lesson.objectives)
        _add_section(story, styles, "Entry Ticket", lesson.entry_ticket)
        _add_section(story, styles, "Teacher Script", lesson.teacher_script)
        _add_section(story, styles, "Blackboard Notes", _stringify_blackboard(lesson.blackboard_notes))
        _add_list(story, styles, "Classroom Activities", lesson.classroom_activities)
        _add_list(story, styles, "Checkpoint Questions", lesson.checkpoint_questions)
        _add_section(story, styles, "Exit Ticket", lesson.exit_ticket)
        _add_section(story, styles, "Homework", lesson.homework)
        _add_section(story, styles, "Mentor Moment", lesson.mentor_moment)

    doc.build(story)
    return target


def export_teacher_guide(pkg: "TeacherKnowledgePackage") -> Path:
    package_dir = _ensure_package_dir(pkg.package_id)
    target = package_dir / _build_filename(pkg, "TeacherGuide")
    styles = _build_styles()
    doc = _ReportDoc(str(target), f"Teacher Guide — {pkg.metadata.subject}", styles)
    story: list = []

    _add_cover(story, styles, pkg, "Teacher Guide")
    _add_list(story, styles, "Learning Objectives", pkg.learning_objectives)
    _add_list(story, styles, "Prerequisites", pkg.prerequisites)

    def _render_objects(title: str, items: list, kind: str) -> None:
        if not items:
            return
        story.append(Paragraph(title, styles["SectionTitle"]))
        story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#cccccc"), spaceAfter=6))
        for item in items:
            if kind == "concept":
                story.append(Paragraph(f"<b>{_clean(item.name)}</b>", styles["Subheading"]))
                story.append(Paragraph(_clean(item.explanation), styles["BodyText"]))
            elif kind == "definition":
                story.append(Paragraph(f"<b>{_clean(item.term)}</b>", styles["Subheading"]))
                story.append(Paragraph(_clean(item.definition), styles["BodyText"]))
            elif kind == "formula":
                story.append(Paragraph(f"<b>{_clean(item.name)}</b>: {_clean(item.expression)}", styles["BodyText"]))
                if getattr(item, "description", None):
                    story.append(Paragraph(_clean(item.description), styles["BodyText"]))
            elif kind == "example":
                story.append(Paragraph(f"<b>{_clean(item.title)}</b>", styles["Subheading"]))
                story.append(Paragraph(_clean(item.description), styles["BodyText"]))
            elif kind == "application":
                story.append(Paragraph(f"<b>{_clean(item.domain)}</b>", styles["Subheading"]))
                story.append(Paragraph(_clean(item.description), styles["BodyText"]))
            story.append(Spacer(1, 6))
        story.append(Spacer(1, 8))

    _render_objects("Concepts", pkg.concepts, "concept")
    _render_objects("Definitions", pkg.definitions, "definition")
    _render_objects("Formulae", pkg.formulae, "formula")
    _render_objects("Examples", pkg.examples, "example")
    _render_objects("Applications", pkg.applications, "application")

    if pkg.misconceptions:
        story.append(PageBreak())
        story.append(Paragraph("Misconceptions and Remedial Actions", styles["SectionTitle"]))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1a1a2e"), spaceAfter=8))
        for item in pkg.misconceptions:
            story.append(Paragraph(f"<b>{_clean(item.misconception)}</b>", styles["Subheading"]))
            story.append(Paragraph(f"<b>Correct understanding:</b> {_clean(item.correct_understanding)}", styles["BodyText"]))
            story.append(Paragraph(f"<b>Remedial action:</b> {_clean(item.remedial_action)}", styles["BodyText"]))
            story.append(Spacer(1, 8))

    doc.build(story)
    return target


def _render_question_section(story, styles, title: str, questions: list, start_idx: int) -> int:
    """Render a group of questions, returning the next question index."""
    if not questions:
        return start_idx
    story.append(Paragraph(title, styles["SectionTitle"]))
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#cccccc"), spaceAfter=6))
    idx = start_idx
    for q in questions:
        question_text = getattr(q, "question", None) or getattr(q, "scenario", "")
        story.append(Paragraph(f"Q{idx}. {_clean(str(question_text))}", styles["QuestionText"]))
        if hasattr(q, "options") and q.options:
            for oi, opt in enumerate(q.options):
                story.append(Paragraph(f"{chr(65 + oi)}. {_clean(str(opt))}", styles["Bullet"]))
        if hasattr(q, "questions") and q.questions:
            for sq in q.questions:
                story.append(Paragraph(f"• {_clean(str(sq))}", styles["Bullet"]))
        if getattr(q, "diagram_prompt", None):
            story.append(Paragraph(f"<i>Diagram:</i> {_clean(q.diagram_prompt)}", styles["BodyText"]))
        story.append(Spacer(1, 6))
        idx += 1
    story.append(Spacer(1, 8))
    return idx


def export_assessment_book(pkg: "TeacherKnowledgePackage") -> Path:
    include_answer_key = True
    if pkg.assessments and hasattr(pkg.assessments, "config"):
        cfg = getattr(pkg.assessments, "config", None)
        if cfg and hasattr(cfg, "include_answer_key"):
            include_answer_key = cfg.include_answer_key

    package_dir = _ensure_package_dir(pkg.package_id)
    target = package_dir / _build_filename(pkg, "Assessment")
    styles = _build_styles()
    doc = _ReportDoc(str(target), f"Assessment — {pkg.metadata.subject}", styles)
    story: list = []

    _add_cover(story, styles, pkg, "Assessment Book")

    if not pkg.assessments:
        story.append(Paragraph("No assessments generated.", styles["BodyText"]))
        doc.build(story)
        return target

    idx = 1
    idx = _render_question_section(story, styles, "Multiple Choice Questions", pkg.assessments.mcqs, idx)

    # Short answer
    if pkg.assessments.short_answers:
        story.append(Paragraph("Short Answer Questions", styles["SectionTitle"]))
        story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#cccccc"), spaceAfter=6))
        for q in pkg.assessments.short_answers:
            story.append(Paragraph(f"Q{idx}. {_clean(q.question)}", styles["QuestionText"]))
            story.append(Spacer(1, 6))
            idx += 1
        story.append(Spacer(1, 8))

    # Long answer
    if pkg.assessments.long_answers:
        story.append(Paragraph("Long Answer Questions", styles["SectionTitle"]))
        story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#cccccc"), spaceAfter=6))
        for q in pkg.assessments.long_answers:
            story.append(Paragraph(f"Q{idx}. {_clean(q.question)}", styles["QuestionText"]))
            story.append(Spacer(1, 6))
            idx += 1
        story.append(Spacer(1, 8))

    # Numerical
    if pkg.assessments.numerical:
        story.append(Paragraph("Numerical Problems", styles["SectionTitle"]))
        story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#cccccc"), spaceAfter=6))
        for q in pkg.assessments.numerical:
            story.append(Paragraph(f"Q{idx}. {_clean(q.question)}", styles["QuestionText"]))
            story.append(Spacer(1, 6))
            idx += 1
        story.append(Spacer(1, 8))

    # Case studies
    if pkg.assessments.case_studies:
        story.append(Paragraph("Case Studies", styles["SectionTitle"]))
        story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#cccccc"), spaceAfter=6))
        for q in pkg.assessments.case_studies:
            story.append(Paragraph(f"Q{idx}. {_clean(q.scenario)}", styles["QuestionText"]))
            for sq in q.questions:
                story.append(Paragraph(f"• {_clean(sq)}", styles["Bullet"]))
            story.append(Spacer(1, 6))
            idx += 1
        story.append(Spacer(1, 8))

    # HOTS
    if pkg.assessments.hots:
        story.append(Paragraph("Higher Order Thinking Questions", styles["SectionTitle"]))
        story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#cccccc"), spaceAfter=6))
        for q in pkg.assessments.hots:
            story.append(Paragraph(f"Q{idx}. {_clean(q.question)}", styles["QuestionText"]))
            story.append(Spacer(1, 6))
            idx += 1
        story.append(Spacer(1, 8))

    # Diagram questions
    if pkg.assessments.diagram_questions:
        story.append(Paragraph("Diagram Questions", styles["SectionTitle"]))
        story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#cccccc"), spaceAfter=6))
        for q in pkg.assessments.diagram_questions:
            story.append(Paragraph(f"Q{idx}. {_clean(q.question)}", styles["QuestionText"]))
            if q.diagram_prompt:
                story.append(Paragraph(f"<i>Diagram:</i> {_clean(q.diagram_prompt)}", styles["BodyText"]))
            story.append(Spacer(1, 6))
            idx += 1
        story.append(Spacer(1, 8))

    # ── Answer Key (optional) ──
    if include_answer_key:
        story.append(PageBreak())
        story.append(Paragraph("Answer Key and Explanations", styles["SectionTitle"]))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1a1a2e"), spaceAfter=8))

        if pkg.assessments.mcqs:
            rows = [["Q", "Answer", "Explanation"]]
            for qi, mcq in enumerate(pkg.assessments.mcqs, start=1):
                rows.append([
                    str(qi),
                    chr(65 + mcq.correct_option),
                    _clean(mcq.explanation),
                ])
            # Use the same numbering as the question paper
            _render_answer_key_table(story, styles, "MCQ Answer Key", rows)

        if pkg.assessments.short_answers:
            story.append(Paragraph("Short Answer Key", styles["Subheading"]))
            for qi, q in enumerate(pkg.assessments.short_answers, start=1):
                story.append(Paragraph(f"<b>Q{qi}.</b> {_clean(q.model_answer)}", styles["BodyText"]))
            story.append(Spacer(1, 6))

        if pkg.assessments.long_answers:
            story.append(Paragraph("Long Answer Key", styles["Subheading"]))
            for qi, q in enumerate(pkg.assessments.long_answers, start=1):
                story.append(Paragraph(f"<b>Q{qi}.</b> {_clean(q.model_answer)}", styles["BodyText"]))
            story.append(Spacer(1, 6))

        if pkg.assessments.numerical:
            story.append(Paragraph("Numerical Solutions", styles["Subheading"]))
            for qi, q in enumerate(pkg.assessments.numerical, start=1):
                story.append(Paragraph(f"<b>Q{qi}.</b> {_clean(q.final_answer)}", styles["BodyText"]))
            story.append(Spacer(1, 6))

    doc.build(story)
    return target


def _render_answer_key_table(story, styles, title: str, rows: list[list[str]]) -> None:
    """Render a compact answer-key table."""
    if not rows:
        return
    story.append(Paragraph(title, styles["Subheading"]))
    table = Table(rows, colWidths=[0.5 * inch, 0.9 * inch, 5.0 * inch], repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#b0b0b0")),
        ("FONTNAME", (0, 0), (-1, 0), _FONT_NAME_BOLD),
        ("FONTNAME", (0, 1), (-1, -1), _FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
    ]))
    story.append(table)
    story.append(Spacer(1, 10))


def export_package_pdfs(pkg: "TeacherKnowledgePackage") -> dict[str, Path]:
    lesson_path = export_lesson_plan(pkg)
    teacher_path = export_teacher_guide(pkg)
    assessment_path = export_assessment_book(pkg)
    return {
        "lesson_plan_pdf_path": lesson_path,
        "teacher_guide_pdf_path": teacher_path,
        "assessment_book_pdf_path": assessment_path,
    }
