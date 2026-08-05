"""Agent 10: Publisher — package and save the final TeacherKnowledgePackage."""
from __future__ import annotations
from app.agents.base_agent import BaseAgent
from app.schemas.teacher_package import TeacherKnowledgePackage
from app.services.pdf_export import export_package_pdfs
from app.services.storage import save_package
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PublisherAgent(BaseAgent):
    name = "publisher"

    async def run(self, package: TeacherKnowledgePackage, job_id: str) -> TeacherKnowledgePackage:
        """Save the package to disk and return it."""
        logger.info("agent_start", agent=self.name, job_id=job_id,
                    package_id=package.package_id)

        # Ensure assessment totals are computed
        if package.assessments:
            package.assessments.compute_total()

        # Persist to disk before generating PDFs
        path = save_package(package)

        pdf_paths = export_package_pdfs(package)
        package.lesson_plan_pdf_path = str(pdf_paths["lesson_plan_pdf_path"])
        package.teacher_guide_pdf_path = str(pdf_paths["teacher_guide_pdf_path"])
        package.assessment_book_pdf_path = str(pdf_paths["assessment_book_pdf_path"])

        # Persist again with PDF paths included
        save_package(package)

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
