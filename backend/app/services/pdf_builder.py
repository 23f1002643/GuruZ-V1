from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, Frame, PageTemplate
from reportlab.lib import colors

if TYPE_CHECKING:
    from app.schemas.teacher_package import TeacherKnowledgePackage


class PdfBuilder:
    def __init__(self, pkg: "TeacherKnowledgePackage", filename: str, title: str):
        self.pkg = pkg
        self.filename = filename
        self.title = title
        self.package_dir = self._ensure_package_dir(pkg.package_id)
        self.target_path = self.package_dir / self.filename
        self.styles = self._build_styles()
        self.story = []

        self.doc = SimpleDocTemplate(
            str(self.target_path),
            pagesize=letter,
            rightMargin=inch * 0.75,
            leftMargin=inch * 0.75,
            topMargin=inch * 1.25,
            bottomMargin=inch * 1.0,
        )

        frame = Frame(self.doc.leftMargin, self.doc.bottomMargin, self.doc.width, self.doc.height, id='normal')
        template = PageTemplate(id='main_template', frames=[frame], onPage=self._header_footer)
        self.doc.addPageTemplates([template])

    def _ensure_package_dir(self, package_id: str) -> Path:
        from app.config import get_settings
        settings = get_settings()
        packages_dir = Path(settings.packages_dir)
        package_dir = packages_dir / package_id
        package_dir.mkdir(parents=True, exist_ok=True)
        return package_dir

    def _build_styles(self) -> dict[str, ParagraphStyle]:
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="Title", parent=styles["h1"], fontName="Helvetica-Bold", fontSize=24, leading=28, spaceAfter=18, alignment=TA_CENTER))
        styles.add(ParagraphStyle(name="Header", parent=styles["Normal"], fontName="Helvetica", alignment=TA_CENTER))
        styles.add(ParagraphStyle(name="Footer", parent=styles["Normal"], fontName="Helvetica", alignment=TA_CENTER))
        styles.add(ParagraphStyle(name="SectionTitle", parent=styles["h2"], fontName="Helvetica-Bold", fontSize=16, leading=20, spaceAfter=12, spaceBefore=12))
        styles.add(ParagraphStyle(name="Subheading", parent=styles["h3"], fontName="Helvetica-Bold", fontSize=12, leading=16, spaceAfter=8, spaceBefore=8))
        styles.add(ParagraphStyle(name="CustomBodyText", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=14, spaceAfter=6))
        styles.add(ParagraphStyle(name="ListItem", parent=styles["CustomBodyText"], leftIndent=18, bulletIndent=6, spaceAfter=4))
        styles.add(ParagraphStyle(name="Code", parent=styles["Normal"], fontName="Courier", fontSize=9, leading=12, textColor=colors.darkgrey, backColor=colors.whitesmoke, padding=4))
        return styles

    def _header_footer(self, canvas, doc):
        canvas.saveState()
        # Header
        header = Paragraph(self.title, self.styles["Header"])
        w, h = header.wrap(doc.width, doc.topMargin)
        header.drawOn(canvas, doc.leftMargin, doc.height + doc.topMargin - h)

        # Footer
        footer = Paragraph(f"Page {doc.page}", self.styles["Footer"])
        w, h = footer.wrap(doc.width, doc.bottomMargin)
        footer.drawOn(canvas, doc.leftMargin, h)
        canvas.restoreState()

    def add_title(self):
        self.story.append(Paragraph(self.title, self.styles["Title"]))
        self.story.append(Spacer(1, 24))

    def add_section(self, title: str, content: str):
        if content:
            self.story.append(Paragraph(title, self.styles["SectionTitle"]))
            self.story.append(Paragraph(content.replace('\n', '<br/>'), self.styles["CustomBodyText"]))
            self.story.append(Spacer(1, 12))

    def add_list(self, title: str, items: list[str]):
        if items:
            self.story.append(Paragraph(title, self.styles["Subheading"]))
            for item in items:
                self.story.append(Paragraph(f"• {item}", self.styles["ListItem"]))
            self.story.append(Spacer(1, 12))

    def add_table(self, title: str, rows: list[list[str]], col_widths: list = None):
        if not rows:
            return
        self.story.append(Paragraph(title, self.styles["Subheading"]))
        table = Table(rows, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E0E0E0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#A0A0A0")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        self.story.append(table)
        self.story.append(Spacer(1, 12))

    def add_page_break(self):
        self.story.append(PageBreak())

    def build(self) -> Path:
        self.doc.build(self.story)
        return self.target_path
