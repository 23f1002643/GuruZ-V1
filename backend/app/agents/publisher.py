"""Agent 10: Publisher — package and save the final TeacherKnowledgePackage."""
from __future__ import annotations
from typing import Callable, Optional
from app.agents.base_agent import BaseAgent
from app.schemas.teacher_package import TeacherKnowledgePackage
from app.services.pdf_export import export_package_pdfs
from app.services.storage import save_package
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PublisherAgent(BaseAgent):
    name = "publisher"

    async def run(
        self, package: TeacherKnowledgePackage, job_id: str,
        progress_cb: Optional[Callable[[int, str], None]] = None,
    ) -> TeacherKnowledgePackage:
        """Save the package to disk and return it."""
        logger.info("agent_start", agent=self.name, job_id=job_id,
                    package_id=package.package_id)

        if progress_cb:
            progress_cb(10, "Computing assessment totals...")

        # Ensure assessment totals are computed
        if package.assessments:
            package.assessments.compute_total()

        if progress_cb:
            progress_cb(30, "Persisting package to disk...")

        # Persist to disk before generating PDFs
        path = save_package(package)

        if progress_cb:
            progress_cb(50, "Generating PDF exports...")

        pdf_paths = export_package_pdfs(package)
        package.lesson_plan_pdf_path = str(pdf_paths["lesson_plan_pdf_path"])
        package.teacher_guide_pdf_path = str(pdf_paths["teacher_guide_pdf_path"])
        package.assessment_book_pdf_path = str(pdf_paths["assessment_book_pdf_path"])

        if progress_cb:
            progress_cb(80, "Saving final package with PDF links...")

        # Persist again with PDF paths included
        save_package(package)

        if progress_cb:
            progress_cb(100, f"Package {package.package_id} published")

        logger.info(
            "agent_complete",
            agent=self.name,
            job_id=job_id,
            package_id=package.package_id,
            path=str(path),
            lesson_plan_pdf=str(pdf_paths["lesson_plan_pdf_path"]),
            teacher_guide_pdf=str(pdf_paths["teacher_guide_pdf_path"]),
            assessment_book_pdf=str(pdf_paths["assessment_book_pdf_path"]),
        )
        return package
