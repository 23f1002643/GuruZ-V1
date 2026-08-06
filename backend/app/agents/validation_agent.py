"""Agent 9: Validation — check for hallucination, schema validity, coverage."""
from __future__ import annotations
from typing import Callable, Optional
from app.agents.base_agent import BaseAgent
from app.rag.retriever import retrieve_all
from app.schemas.teacher_package import TeacherKnowledgePackage, ValidationReport, ValidationIssue
from app.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM = """You are a rigorous academic quality assurance specialist.
Evaluate whether the generated educational package accurately reflects the source material.
Write naturally, without referencing how the content was obtained.
Write ALL content in the language specified in LANGUAGE field. Do NOT mix languages.
Do NOT use phrases like 'according to the document', 'based on the provided material', 'the text says', 'source text', 'retrieved content', etc. Write as if the knowledge is yours.
Respond ONLY with valid JSON."""

PROMPT_TEMPLATE = """Validate this Teacher Knowledge Package against the source material.

REFERENCE MATERIAL (ground truth):
{context}

PACKAGE SUMMARY:
- Subject: {subject}
- Topic: {topic}
- Language: {language}
- Learning Objectives: {objectives_count}
- Concepts: {concepts_count}  
- Definitions: {definitions_count}
- Formulae: {formulae_count}
- Lessons: {lessons_count}
- MCQs: {mcqs_count}
- Misconceptions: {misconceptions_count}

SAMPLE CONTENT TO VALIDATE:
{sample}

Check for:
1. Hallucination: content not found in the document
2. Unsupported statements: claims not backed by document
3. Missing objectives: important topics not covered
4. Schema validity: all required fields present
5. Source chunk existence: references are grounded

Return a JSON object:
{{
  "hallucination_score": 0.95,
  "schema_valid": true,
  "all_objectives_covered": true,
  "source_chunks_verified": true,
  "issues": [
    {{
      "severity": "error | warning | info",
      "field": "field.path",
      "message": "Description of the issue"
    }}
  ],
  "validation_notes": "Overall assessment"
}}

hallucination_score: 0.0 = fully hallucinated, 1.0 = fully grounded in document."""


class ValidationAgent(BaseAgent):
    name = "validation_agent"
    temperature = 0.1
    max_tokens = 2000

    async def run(
        self, package: TeacherKnowledgePackage, language: str, job_id: str,
        progress_cb: Optional[Callable[[int, str], None]] = None,
    ) -> ValidationReport:
        logger.info("agent_start", agent=self.name, job_id=job_id)

        if progress_cb:
            progress_cb(20, "Retrieving ground truth from document...")

        # Get ground truth from document
        doc_chunks = retrieve_all(job_id, max_chunks=20)
        context = self.build_rag_context(doc_chunks)

        if progress_cb:
            progress_cb(40, "Building package sample...")

        # Build a sample of generated content to validate
        sample_parts = []
        if package.learning_objectives:
            sample_parts.append("OBJECTIVES: " + "; ".join(package.learning_objectives[:3]))
        if package.concepts:
            c = package.concepts[0]
            sample_parts.append(f"CONCEPT: {c.name} — {c.explanation[:200]}")
        if package.assessments and package.assessments.mcqs:
            q = package.assessments.mcqs[0]
            sample_parts.append(f"MCQ: {q.question}")
        if package.lessons:
            l = package.lessons[0]
            sample_parts.append(f"LESSON INTRO: {l.teacher_script[:300]}")
        sample = "\n\n".join(sample_parts)

        if progress_cb:
            progress_cb(60, "Validating package against source...")

        prompt = PROMPT_TEMPLATE.format(
            context=context,
            subject=package.metadata.subject,
            topic=package.metadata.topic,
            language=language,
            objectives_count=len(package.learning_objectives),
            concepts_count=len(package.concepts),
            definitions_count=len(package.definitions),
            formulae_count=len(package.formulae),
            lessons_count=len(package.lessons),
            mcqs_count=package.assessments.total_questions if package.assessments else 0,
            misconceptions_count=len(package.misconceptions),
            sample=sample,
        )

        data = await self.call_llm_json(prompt, SYSTEM)

        if progress_cb:
            progress_cb(80, "Scoring validation results...")

        hallucination_score = float(data.get("hallucination_score", 0.8))
        schema_valid = bool(data.get("schema_valid", True))
        all_objectives_covered = bool(data.get("all_objectives_covered", True))
        source_chunks_verified = bool(data.get("source_chunks_verified", True))
        completeness_score = data.get("completeness_score")
        if completeness_score is None:
            completeness_score = (
                (1.0 if all_objectives_covered else 0.0) * 0.55
                + (1.0 if source_chunks_verified else 0.0) * 0.35
                + (1.0 if schema_valid else 0.0) * 0.1
            )

        issues = [
            ValidationIssue(
                severity=i.get("severity", "info"),
                field=i.get("field", "unknown"),
                message=i.get("message", ""),
            )
            for i in data.get("issues", [])
        ]

        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")

        # Overall score: weighted average
        overall_score = (
            hallucination_score * 0.4
            + (1.0 if schema_valid else 0.0) * 0.2
            + (1.0 if all_objectives_covered else 0.0) * 0.2
            + (1.0 if source_chunks_verified else 0.0) * 0.1
            + max(0, 1.0 - error_count * 0.2 - warning_count * 0.05) * 0.1
        )

        is_valid = (
            error_count == 0
            and hallucination_score >= 0.6
            and schema_valid
        )

        report = ValidationReport(
            is_valid=is_valid,
            overall_score=round(overall_score, 3),
            hallucination_score=round(hallucination_score, 3),
            completeness_score=round(float(completeness_score), 3),
            schema_valid=schema_valid,
            all_objectives_covered=all_objectives_covered,
            source_chunks_verified=source_chunks_verified,
            issues=issues,
            regeneration_count=0,
        )

        if progress_cb:
            progress_cb(100, f"Score: {report.overall_score:.2f}, Valid: {report.is_valid}")

        logger.info(
            "agent_complete", agent=self.name, job_id=job_id,
            is_valid=is_valid, score=report.overall_score,
        )
        return report
