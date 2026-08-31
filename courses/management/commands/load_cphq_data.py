"""
Management command: load_cphq_data

Reads JSON files from data/questions/ and seeds the database with:

  Category  : Healthcare Quality
  Course    : CPHQ Exam Preparation
  Chapters  : one or more per Domain (video attached if available in media/)
  Topics    : one per Domain
  Questions : loaded from JSON files (quiz, mock, chapter_quiz, module_assessment)

JSON file layout expected in <BASE_DIR>/data/questions/:
  patient_safety_quiz.json          — domain-level quiz questions
  patient_safety_mock.json          — domain-level mock questions
  domain1_chapter1_quick_quiz.json  — chapter quick quiz questions
  domain1_module_assessment.json    — full module MCQ assessment questions

Chapter quick quiz schema:
  {
    "topic": "<topic name>",
    "questions": [{ "text": "...", "options": {...}, "correct_option": "a-d", "explanation": "...", "difficulty": "easy|medium|hard" }]
  }

Module assessment schema:
  {
    "domain_order": 1,
    "questions": [{ "text": "...", "options": {...}, "correct_option": "a-d", "explanation": "...", "difficulty": "easy|medium|hard" }]
  }

Usage:
    python manage.py load_cphq_data
    python manage.py load_cphq_data --flush      # wipe existing data first
    python manage.py load_cphq_data --data-dir path/to/questions/
"""

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from courses.models import Category, Chapter, Course, Domain
from quiz.models import Question, Topic


# ---------------------------------------------------------------------------
# Question files: (filename, topic_name_or_None, question_type)
# ---------------------------------------------------------------------------
QUESTION_FILES = [
    ("patient_safety_quiz.json",              "Patient Safety",                    "quiz"),
    ("patient_safety_mock.json",              "Patient Safety",                    "mock"),
    ("quality_review_quiz.json",              "Quality Review & Accountability",   "quiz"),
    ("quality_review_mock.json",              "Quality Review & Accountability",   "mock"),
    ("performance_improvement_quiz.json",     "Performance and Process Improvement", "quiz"),
    ("performance_improvement_mock.json",     "Performance and Process Improvement", "mock"),
    ("information_management_quiz.json",      "Health Data Analytics",             "quiz"),
    ("information_management_mock.json",      "Health Data Analytics",             "mock"),
    ("patient_experience_quiz.json",          "Population Health and Care Transitions", "quiz"),
    ("patient_experience_mock.json",          "Population Health and Care Transitions", "mock"),
    ("regulatory_accreditation_quiz.json",    "Regulatory and Accreditation",      "quiz"),
    ("regulatory_accreditation_mock.json",    "Regulatory and Accreditation",      "mock"),
    ("quality_leadership_quiz.json",          "Quality Leadership and Integration", "quiz"),
    ("quality_leadership_mock.json",          "Quality Leadership and Integration", "mock"),
    ("cphq_global_mock.json",                 None,                                "mock"),
    ("pre_assessment_bank.json",               None,                                "pre_assessment"),
    ("practice_test_bank.json",                None,                                "practice_test"),
    ("mock_exam_bank.json",                    None,                                "mock"),
    ("final_exam_bank.json",                   None,                                "final_exam"),
]

# Chapter quick quiz files: (filename, domain_order, chapter_order)
CHAPTER_QUIZ_FILES = [
    ("domain1_chapter1_quick_quiz.json", 1, 1),
    ("domain1_chapter2_quick_quiz.json", 1, 2),
    ("domain1_chapter3_quick_quiz.json", 1, 3),
    ("domain1_chapter4_quick_quiz.json", 1, 4),
    ("domain1_chapter5_quick_quiz.json", 1, 5),
    ("domain2_chapter1_quick_quiz.json", 2, 1),
    ("domain2_chapter2_quick_quiz.json", 2, 2),
    ("domain2_chapter3_quick_quiz.json", 2, 3),
    ("domain2_chapter4_quick_quiz.json", 2, 4),
    ("domain3_chapter1_quick_quiz.json", 3, 1),
    ("domain3_chapter2_quick_quiz.json", 3, 2),
    ("domain3_chapter3_quick_quiz.json", 3, 3),
    ("domain3_chapter4_quick_quiz.json", 3, 4),
    ("domain3_chapter5_quick_quiz.json", 3, 5),
    ("domain4_chapter1_quick_quiz.json", 4, 1),
    ("domain4_chapter2_quick_quiz.json", 4, 2),
    ("domain4_chapter3_quick_quiz.json", 4, 3),
    ("domain4_chapter4_quick_quiz.json", 4, 4),
    ("domain4_chapter5_quick_quiz.json", 4, 5),
    ("domain5_chapter1_quick_quiz.json", 5, 1),
    ("domain5_chapter2_quick_quiz.json", 5, 2),
    ("domain5_chapter3_quick_quiz.json", 5, 3),
    ("domain5_chapter4_quick_quiz.json", 5, 4),
    ("domain5_chapter5_quick_quiz.json", 5, 5),
    ("domain6_chapter1_quick_quiz.json", 6, 1),
    ("domain6_chapter2_quick_quiz.json", 6, 2),
    ("domain6_chapter3_quick_quiz.json", 6, 3),
    ("domain6_chapter4_quick_quiz.json", 6, 4),
    ("domain6_chapter5_quick_quiz.json", 6, 5),
    ("domain6_chapter6_quick_quiz.json", 6, 6),
    ("domain7_chapter1_quick_quiz.json", 7, 1),
    ("domain7_chapter2_quick_quiz.json", 7, 2),
    ("domain7_chapter3_quick_quiz.json", 7, 3),
    ("domain7_chapter4_quick_quiz.json", 7, 4),
]

# Full Module MCQ Assessment files: (filename, domain_order)
MODULE_ASSESSMENT_FILES = [
    ("domain1_module_assessment.json", 1),
    ("domain2_module_assessment.json", 2),
    ("domain3_module_assessment.json", 3),
    ("domain4_module_assessment.json", 4),
    ("domain5_module_assessment.json", 5),
    ("domain6_module_assessment.json", 6),
    ("domain7_module_assessment.json", 7),
]

# Course structure: Course → Domains → Chapters
# Each domain can have one or more chapters.
COURSE_STRUCTURE = [
    {
        "order": 1,
        "title": "Module 1: Quality Leadership and Integration",
        "description": "Covers quality leadership principles, change management, organizational culture, and strategic integration of quality.",
        "topic_name": "Quality Leadership and Integration",
        "chapters": [
            {
                "order": 1,
                "title": "Chapter 1: Leadership vs. Management",
                "video_filename": "Quality Leadership and Integration - Chapter 1.mp4",
            },
            {
                "order": 2,
                "title": "Chapter 2: Leadership and Organizational Culture",
                "video_filename": "Quality Leadership and Integration - Chapter 2.mp4",
            },
            {
                "order": 3,
                "title": "Chapter 3: Strategic Planning and Performance Excellence",
                "video_filename": "Quality Leadership and Integration - Chapter 3.mp4",
            },
            {
                "order": 4,
                "title": "Chapter 4: Organizational Infrastructure for Quality and Safety",
                "video_filename": "Quality Leadership and Integration - Chapter 4.mp4",
            },
            {
                "order": 5,
                "title": "Chapter 5: Quality Leadership and Integration",
                "video_filename": "Quality Leadership and Integration - Chapter 5.mp4",
            },
        ],
    },
    {
        "order": 2,
        "title": "Module 2: Performance and Process Improvement",
        "description": "Covers quality improvement methodologies including PDSA, Lean, Six Sigma, and data-driven improvement tools.",
        "topic_name": "Performance and Process Improvement",
        "chapters": [
            {
                "order": 1,
                "title": "Chapter 1: Evolution of Performance Improvement in Healthcare",
                "video_filename": "Performance and Process Improvement - Chapter 1.mp4",
            },
            {
                "order": 2,
                "title": "Chapter 2: Performance Improvement Approaches",
                "video_filename": "Performance and Process Improvement - Chapter 2.mp4",
            },
            {
                "order": 3,
                "title": "Chapter 3: Systems Thinking",
                "video_filename": "Performance and Process Improvement - Chapter 3.mp4",
            },
            {
                "order": 4,
                "title": "Chapter 4: Quality Indicators & Value in Healthcare",
                "video_filename": "Performance and Process Improvement - Chapter 4.mp4",
            },
        ],
    },
    {
        "order": 3,
        "title": "Module 3: Population Health and Care Transitions",
        "description": "Covers population health strategy, care transitions, health equity, social determinants of health, and value-based care.",
        "topic_name": "Population Health and Care Transitions",
        "chapters": [
            {
                "order": 1,
                "title": "Chapter 1: Strategic Frameworks for Population Health",
                "video_filename": "Population Health and Care Transitions - Chapter 1.mp4",
            },
            {
                "order": 2,
                "title": "Chapter 2: Core Components of Population Health Management",
                "video_filename": "Population Health and Care Transitions - Chapter 2.mp4",
            },
            {
                "order": 3,
                "title": "Chapter 3: Data, Analytics & Multi-Sector Collaboration",
                "video_filename": "Population Health and Care Transitions - Chapter 3.mp4",
            },
            {
                "order": 4,
                "title": "Chapter 4: Health Equity & Social Determinants of Health",
                "video_filename": "Population Health and Care Transitions - Chapter 4.mp4",
            },
            {
                "order": 5,
                "title": "Chapter 5: Value-Based Care & Population Health",
                "video_filename": "Population Health and Care Transitions - Chapter 5.mp4",
            },
        ],
    },
    {
        "order": 4,
        "title": "Module 4: Health Data Analytics",
        "description": "Covers healthcare data management, analytics, sampling, and the Donabedian structure-process-outcome framework.",
        "topic_name": "Health Data Analytics",
        "chapters": [
            {
                "order": 1,
                "title": "Chapter 1: Data & Decision Support System",
                "video_filename": "Health Data Analytics - Chapter 1.mp4",
            },
            {
                "order": 2,
                "title": "Chapter 2: From Data to Decision",
                "video_filename": "Health Data Analytics - Chapter 2.mp4",
            },
            {
                "order": 3,
                "title": "Chapter 3: Sampling in Healthcare Quality Measurement",
                "video_filename": "Health Data Analytics - Chapter 3.mp4",
            },
            {
                "order": 4,
                "title": "Chapter 4: The Chain of Quality — Donabedian & Finding the Right Data",
                "video_filename": "Health Data Analytics - Chapter 4.mp4",
            },
            {
                "order": 5,
                "title": "Chapter 5: Health Data Analytics",
                "video_filename": "Health Data Analytics - Chapter 5.mp4",
            },
        ],
    },
    {
        "order": 5,
        "title": "Module 5: Patient Safety",
        "description": "Covers patient safety principles, risk reduction, and safety culture in healthcare.",
        "topic_name": "Patient Safety",
        "chapters": [
            {
                "order": 1,
                "title": "Chapter 1: Concepts, Principles and Practices",
                "video_filename": "Patient Safety - Chapter 1.mp4",
            },
            {
                "order": 2,
                "title": "Chapter 2: Leadership",
                "video_filename": "Patient Safety - Chapter 2.mp4",
            },
            {
                "order": 3,
                "title": "Chapter 3: Tools and Techniques",
                "video_filename": "Patient Safety - Chapter 3.mp4",
            },
            {
                "order": 4,
                "title": "Chapter 4: Evaluating and Improving Patient Safety",
                "video_filename": "Patient Safety - Chapter 4.mp4",
            },
            {
                "order": 5,
                "title": "Chapter 5: Patient Safety and Learning Organizations",
                "video_filename": "Patient Safety - Chapter 5.mp4",
            },
        ],
    },
    {
        "order": 6,
        "title": "Module 6: Quality Review and Accountability",
        "description": "Covers quality review processes, accountability structures, payment models, and performance measurement infrastructure.",
        "topic_name": "Quality Review & Accountability",
        "chapters": [
            {
                "order": 1,
                "title": "Chapter 1: Current & Emerging Payment Models",
                "video_filename": "Quality Review and Accountability - Chapter 1.mp4",
            },
            {
                "order": 2,
                "title": "Chapter 2: External Quality Organizations & Compliance",
                "video_filename": "Quality Review and Accountability - Chapter 2.mp4",
            },
            {
                "order": 3,
                "title": "Chapter 3: Transparency & Performance Measurement",
                "video_filename": "Quality Review and Accountability - Chapter 3.mp4",
            },
            {
                "order": 4,
                "title": "Chapter 4: Physician & Clinician Performance",
                "video_filename": "Quality Review and Accountability - Chapter 4.mp4",
            },
            {
                "order": 5,
                "title": "Chapter 5: Quality Review and Accountability",
                "video_filename": "Quality Review and Accountability - Chapter 5.mp4",
            },
            {
                "order": 6,
                "title": "Chapter 6: Performance Measurement & Improvement Infrastructure",
                "video_filename": "Quality Review and Accountability - Chapter 6.mp4",
            },
        ],
    },
    {
        "order": 7,
        "title": "Module 7: Regulatory and Accreditation",
        "description": "Covers healthcare laws, federal agencies, accreditation, certification, and accrediting bodies.",
        "topic_name": "Regulatory and Accreditation",
        "chapters": [
            {
                "order": 1,
                "title": "Chapter 1: Healthcare Laws & Regulations",
                "video_filename": "Regulatory and Accreditation - Chapter 1.mp4",
            },
            {
                "order": 2,
                "title": "Chapter 2: Federal Agencies",
                "video_filename": "Regulatory and Accreditation - Chapter 2.mp4",
            },
            {
                "order": 3,
                "title": "Chapter 3: Accreditation, Certification & Recognition",
                "video_filename": "Regulatory and Accreditation - Chapter 3.mp4",
            },
            {
                "order": 4,
                "title": "Chapter 4: Accrediting Bodies",
                "video_filename": "Regulatory and Accreditation - Chapter 4.mp4",
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Seed the database with the CPHQ course, chapters, topics, and questions from JSON files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing CPHQ course data before loading.",
        )
        parser.add_argument(
            "--data-dir",
            default=None,
            help="Path to the questions JSON folder (default: <BASE_DIR>/data/questions).",
        )

    def handle(self, *args, **options):
        data_dir = Path(options["data_dir"]) if options["data_dir"] else Path(settings.BASE_DIR) / "data" / "questions"

        if not data_dir.exists():
            raise CommandError(f"Data directory not found: {data_dir}")

        if options["flush"]:
            self._flush()

        self.stdout.write(self.style.MIGRATE_HEADING("=== Loading CPHQ data from JSON ===\n"))

        # ── Category & Course ──────────────────────────────────────────────
        category, created = Category.objects.get_or_create(
            slug="healthcare-quality",
            defaults={
                "name": "Healthcare Quality",
                "description": "CPHQ exam preparation materials.",
            },
        )
        self._log("created" if created else "exists", "Category", category.name)

        course, created = Course.objects.get_or_create(
            slug="cphq-exam-preparation",
            defaults={
                "title": "CPHQ Exam Preparation",
                "category": category,
                "about": (
                    "Comprehensive preparation for the Certified Professional in Healthcare Quality (CPHQ) exam. "
                    "Covers all exam domains with video lectures, quizzes, and mock examinations."
                ),
                "description": (
                    "This course prepares healthcare professionals for the CPHQ certification exam. "
                    "It includes in-depth video instruction, domain-specific quizzes, and full-length mock exams "
                    "aligned with the NAHQ exam blueprint."
                ),
                "is_published": True,
                "order": 1,
            },
        )
        self._log("created" if created else "exists", "Course", course.title)

        # ── Domains & Chapters ─────────────────────────────────────────────
        media_video_dir = Path(settings.MEDIA_ROOT) / "courses" / "videos"
        topic_name_to_domain = {}
        for domain_cfg in COURSE_STRUCTURE:
            domain, created = Domain.objects.get_or_create(
                course=course,
                order=domain_cfg["order"],
                defaults={
                    "title": domain_cfg["title"],
                    "description": domain_cfg.get("description", ""),
                    "is_published": True,
                },
            )
            if not created:
                domain.title = domain_cfg["title"]
                domain.description = domain_cfg.get("description", "")
                domain.save()
            self._log("created" if created else "exists", "Domain", domain.title)
            topic_name_to_domain[domain_cfg["topic_name"]] = domain

            for ch_cfg in domain_cfg["chapters"]:
                chapter, created = Chapter.objects.get_or_create(
                    domain=domain,
                    order=ch_cfg["order"],
                    defaults={
                        "title": ch_cfg["title"],
                        "is_published": True,
                        "duration_minutes": 0,
                    },
                )
                if not created:
                    chapter.title = ch_cfg["title"]
                    chapter.save()
                self._log("created" if created else "exists", "Chapter", chapter.title)

                # Link video if it exists in media/
                video_filename = ch_cfg.get("video_filename", "")
                if video_filename:
                    video_path = media_video_dir / video_filename
                    if video_path.exists():
                        rel = f"courses/videos/{video_filename}"
                        if chapter.video_file.name != rel:
                            chapter.video_file.name = rel
                            chapter.save()
                            self.stdout.write(f"      Video linked: {video_filename}")
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"      Video not found in media/: {video_filename}")
                        )

        # ── Topics & Questions ─────────────────────────────────────────────
        self.stdout.write("")
        total_created = 0
        total_skipped = 0

        for filename, topic_name, q_type in QUESTION_FILES:
            filepath = data_dir / filename
            if not filepath.exists():
                self.stdout.write(self.style.WARNING(f"  Skipping (not found): {filename}"))
                continue

            topic = None
            if topic_name:
                topic, t_created = Topic.objects.get_or_create(
                    name=topic_name,
                    defaults={
                        "description": f"Questions covering the {topic_name} domain of the CPHQ exam.",
                        "domain": topic_name_to_domain.get(topic_name),
                    },
                )
                if t_created:
                    self._log("created", "Topic", topic.name)
                elif topic.domain_id != getattr(topic_name_to_domain.get(topic_name), "id", None):
                    topic.domain = topic_name_to_domain.get(topic_name)
                    topic.save(update_fields=["domain"])

            created_count, skipped_count = self._load_json(filepath, topic, q_type)
            total_created += created_count
            total_skipped += skipped_count

        # ── Chapter Quick Quiz Questions ───────────────────────────────────
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("=== Loading chapter quick quiz questions ===\n"))
        chapter_q_created = 0
        chapter_q_skipped = 0

        for filename, domain_order, chapter_order in CHAPTER_QUIZ_FILES:
            filepath = data_dir / filename
            if not filepath.exists():
                self.stdout.write(self.style.WARNING(f"  Skipping (not found): {filename}"))
                continue

            try:
                chapter = Chapter.objects.get(domain__course=course, domain__order=domain_order, order=chapter_order)
            except Chapter.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  Chapter not found for domain {domain_order} chapter {chapter_order}, skipping {filename}"))
                continue

            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)

            topic_name = data.get("topic")
            topic = None
            if topic_name:
                topic, _ = Topic.objects.get_or_create(
                    name=topic_name,
                    defaults={"description": f"Questions covering the {topic_name} domain of the CPHQ exam."},
                )

            created, skipped = self._load_chapter_quiz(filepath, data, chapter, topic)
            chapter_q_created += created
            chapter_q_skipped += skipped

        # ── Full Module MCQ Assessment Questions ────────────────────────────
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("=== Loading full module MCQ assessment questions ===\n"))
        module_q_created = 0
        module_q_skipped = 0

        for filename, domain_order in MODULE_ASSESSMENT_FILES:
            filepath = data_dir / filename
            if not filepath.exists():
                self.stdout.write(self.style.WARNING(f"  Skipping (not found): {filename}"))
                continue

            try:
                domain = Domain.objects.get(course=course, order=domain_order)
            except Domain.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  Domain {domain_order} not found, skipping {filename}"))
                continue

            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)

            created, skipped = self._load_module_assessment(filepath, data, domain)
            module_q_created += created
            module_q_skipped += skipped

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"=== Done! {total_created} domain questions + {chapter_q_created} chapter quiz questions + "
                f"{module_q_created} module assessment questions created. "
                f"({total_skipped + chapter_q_skipped + module_q_skipped} total skipped) ==="
            )
        )

    # ── Chapter quiz loader ────────────────────────────────────────────────

    def _load_chapter_quiz(self, filepath: Path, data: dict, chapter, topic) -> tuple[int, int]:
        questions = data.get("questions", [])
        self.stdout.write(f"  Loading {filepath.name}  ({len(questions)} questions, chapter={chapter.title})")
        created = 0
        skipped = 0
        for q in questions:
            text = q.get("text", "").strip()
            options = q.get("options", {})
            correct = q.get("correct_option", "").lower().strip()
            explanation = q.get("explanation", "").strip()
            difficulty = q.get("difficulty", "medium")
            if not text or not options or correct not in "abcd" or len(options) < 4:
                skipped += 1
                continue
            if Question.objects.filter(text=text, question_type="chapter_quiz").exists():
                skipped += 1
                continue
            Question.objects.create(
                topic=topic,
                chapter=chapter,
                question_type="chapter_quiz",
                difficulty=difficulty,
                text=text,
                option_a=options.get("a", ""),
                option_b=options.get("b", ""),
                option_c=options.get("c", ""),
                option_d=options.get("d", ""),
                correct_option=correct,
                explanation=explanation,
                is_active=True,
            )
            created += 1
        label = self.style.SUCCESS(f"    Created: {created}") if created else f"    Created: {created}"
        self.stdout.write(label + (f"  Skipped: {skipped}" if skipped else ""))
        return created, skipped

    # ── Module assessment loader ─────────────────────────────────────────────

    def _load_module_assessment(self, filepath: Path, data: dict, domain) -> tuple[int, int]:
        questions = data.get("questions", [])
        self.stdout.write(f"  Loading {filepath.name}  ({len(questions)} questions, module={domain.title})")
        created = 0
        skipped = 0
        for q in questions:
            text = q.get("text", "").strip()
            options = q.get("options", {})
            correct = q.get("correct_option", "").lower().strip()
            explanation = q.get("explanation", "").strip()
            difficulty = q.get("difficulty", "medium")
            if not text or not options or correct not in "abcd" or len(options) < 4:
                skipped += 1
                continue
            if Question.objects.filter(text=text, question_type="module_assessment").exists():
                skipped += 1
                continue
            Question.objects.create(
                domain=domain,
                question_type="module_assessment",
                difficulty=difficulty,
                text=text,
                option_a=options.get("a", ""),
                option_b=options.get("b", ""),
                option_c=options.get("c", ""),
                option_d=options.get("d", ""),
                correct_option=correct,
                explanation=explanation,
                is_active=True,
            )
            created += 1
        label = self.style.SUCCESS(f"    Created: {created}") if created else f"    Created: {created}"
        self.stdout.write(label + (f"  Skipped: {skipped}" if skipped else ""))
        return created, skipped

    # ── JSON loader ────────────────────────────────────────────────────────

    def _load_json(self, filepath: Path, topic, q_type: str) -> tuple[int, int]:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        questions = data.get("questions", [])
        self.stdout.write(f"  Loading {filepath.name}  ({len(questions)} questions, type={q_type})")

        created = 0
        skipped = 0

        for q in questions:
            text = q.get("text", "").strip()
            options = q.get("options", {})
            correct = q.get("correct_option", "").lower().strip()
            explanation = q.get("explanation", "").strip()
            difficulty = q.get("difficulty", "medium")

            # Basic validation
            if not text or not options or correct not in "abcd" or len(options) < 4:
                skipped += 1
                continue

            # Deduplicate by question text within the same question type - the
            # same CPHQ question can legitimately appear in multiple assessment
            # pools (e.g. both a mock exam and the final exam) without being a
            # true duplicate of that specific pool's content.
            if Question.objects.filter(text=text, question_type=q_type).exists():
                skipped += 1
                continue

            Question.objects.create(
                topic=topic,
                question_type=q_type,
                difficulty=difficulty,
                text=text,
                option_a=options.get("a", ""),
                option_b=options.get("b", ""),
                option_c=options.get("c", ""),
                option_d=options.get("d", ""),
                correct_option=correct,
                explanation=explanation,
                is_active=True,
            )
            created += 1

        label = self.style.SUCCESS(f"    Created: {created}") if created else f"    Created: {created}"
        self.stdout.write(label + (f"  Skipped: {skipped}" if skipped else ""))
        return created, skipped

    # ── Flush ──────────────────────────────────────────────────────────────

    def _flush(self):
        self.stdout.write(self.style.WARNING("Flushing existing CPHQ data..."))
        Course.objects.filter(slug="cphq-exam-preparation").delete()  # cascades → Domain → Chapter
        Category.objects.filter(slug="healthcare-quality").delete()
        Topic.objects.filter(name__in=["Patient Safety", "Quality Review & Accountability"]).delete()
        Question.objects.all().delete()
        self.stdout.write(self.style.WARNING("Done.\n"))

    def _log(self, action: str, model: str, name: str):
        colour = self.style.SUCCESS if action == "created" else self.style.HTTP_INFO
        self.stdout.write(colour(f"  [{action}] {model}: {name}"))
