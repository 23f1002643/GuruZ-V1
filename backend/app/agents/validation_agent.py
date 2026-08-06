"""Agent 9: Validation — check for hallucination, schema validity, coverage."""
from __future__ import annotations
from typing import Callable, Optional
from app.agents.base_agent import BaseAgent
from app.rag.retriever import retrieve_all
from app.schemas.teacher_package import TeacherKnowledgePackage, ValidationIssue
from app.schemas.validation_report import ValidationReport
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
6. JSON validity: output is structured correctly and no fields are malformed
7. Educational quality: content is appropriate for the target grade and lesson objective
8. Consistency: package sections do not contradict each other

Return a JSON object:
{{
  "hallucination_score": 0.95,
  "schema_valid": true,
  "all_objectives_covered": true,
  "source_chunks_verified": true,
  "completeness_score": 0.95,
  "json_validity_score": 1.0,
  "educational_quality_score": 0.9,
  "consistency_score": 0.92,
  "issues": [
    {{
      "severity": "error | warning | info",
      "field": "field.path",
      "message": "Description of the issue"
    }}
  ],
  "validation_notes": "Overall assessment"
}}

hallucination_score: 0.0 = fully hallucinated, 1.0 = fully grounded in document.
completeness_score: 0.0 = many required parts missing, 1.0 = package is complete and covers objectives.
json_validity_score: 0.0 = invalid/malformed JSON, 1.0 = fully correct JSON structure.
educational_quality_score: 0.0 = poor instructional quality, 1.0 = excellent instructional quality.
consistency_score: 0.0 = contradictory or mismatched content, 1.0 = internally consistent."""


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
        json_validity_score = float(data.get("json_validity_score", 1.0))
        educational_quality_score = float(data.get("educational_quality_score", 0.8))
        consistency_score = float(data.get("consistency_score", 0.9))
        completeness_score = data.get("completeness_score")
        if completeness_score is None:
            completeness_score = (
                (1.0 if all_objectives_covered else 0.0) * 0.5
                + (1.0 if source_chunks_verified else 0.0) * 0.35
                + (1.0 if schema_valid else 0.0) * 0.15
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

        # Score weights chosen for transparency and production use.
        # Completeness and grounding are the strongest signals.
        overall_score = (
            completeness_score * 0.35
            + hallucination_score * 0.3
            + json_validity_score * 0.15
            + educational_quality_score * 0.1
            + consistency_score * 0.1
        )

        # Valid if no blocking errors, schema is valid, and grounding is reasonable.
        is_valid = (
            error_count == 0
            and schema_valid
            and hallucination_score >= 0.5
            and completeness_score >= 0.5
            and json_validity_score >= 0.75
        )

        report = ValidationReport(
            is_valid=is_valid,
            overall_score=round(min(max(overall_score, 0.0), 1.0), 3),
            hallucination_score=round(min(max(hallucination_score, 0.0), 1.0), 3),
            completeness_score=round(min(max(float(completeness_score), 0.0), 1.0), 3),
            json_validity_score=round(min(max(json_validity_score, 0.0), 1.0), 3),
            educational_quality_score=round(min(max(educational_quality_score, 0.0), 1.0), 3),
            consistency_score=round(min(max(consistency_score, 0.0), 1.0), 3),
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
