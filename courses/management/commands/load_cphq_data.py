"""
Management command: load_cphq_data

Reads JSON files from data/questions/ and seeds the database with:

  Category  : Healthcare Quality
  Course    : CPHQ Exam Preparation
  Chapters  : one per Domain (video attached if available in media/)
  Topics    : one per Domain
  Questions : loaded from JSON files

JSON file layout expected in <BASE_DIR>/data/questions/:
  patient_safety_quiz.json
  patient_safety_mock.json
  quality_review_quiz.json
  quality_review_mock.json
  cphq_global_mock.json

Each file has the schema:
  {
    "topic": "<topic name or null>",
    "type":  "quiz" | "mock",
    "questions": [
      {
        "text": "...",
        "options": {"a": "...", "b": "...", "c": "...", "d": "..."},
        "correct_option": "a" | "b" | "c" | "d",
        "explanation": "...",
        "difficulty": "easy" | "medium" | "hard"   // optional
      }
    ]
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

from courses.models import Category, Chapter, Course
from quiz.models import Question, Topic


# ---------------------------------------------------------------------------
# Question files: (filename, topic_name_or_None, question_type)
# ---------------------------------------------------------------------------
QUESTION_FILES = [
    ("patient_safety_quiz.json",     "Patient Safety",                  "quiz"),
    ("patient_safety_mock.json",     "Patient Safety",                  "mock"),
    ("quality_review_quiz.json",     "Quality Review & Accountability",  "quiz"),
    ("quality_review_mock.json",     "Quality Review & Accountability",  "mock"),
    ("cphq_global_mock.json",        None,                               "mock"),
]

DOMAIN_CHAPTERS = [
    {
        "order": 1,
        "title": "Domain 1: Patient Safety",
        "video_filename": "Patient Safety.mp4",
    },
    {
        "order": 2,
        "title": "Domain 2: Quality Review & Accountability",
        "video_filename": "Quality Review and Accountability.mp4",
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

        # ── Chapters ───────────────────────────────────────────────────────
        media_video_dir = Path(settings.MEDIA_ROOT) / "courses" / "videos"
        for domain in DOMAIN_CHAPTERS:
            chapter, created = Chapter.objects.get_or_create(
                course=course,
                order=domain["order"],
                defaults={
                    "title": domain["title"],
                    "is_published": True,
                    "duration_minutes": 0,
                },
            )
            if not created:
                chapter.title = domain["title"]
                chapter.save()
            self._log("created" if created else "exists", "Chapter", chapter.title)

            # Link video if it exists in media/
            video_path = media_video_dir / domain["video_filename"]
            if video_path.exists():
                rel = f"courses/videos/{domain['video_filename']}"
                if chapter.video_file.name != rel:
                    chapter.video_file.name = rel
                    chapter.save()
                    self.stdout.write(f"    Video linked: {domain['video_filename']}")
            else:
                self.stdout.write(
                    self.style.WARNING(f"    Video not found in media/: {domain['video_filename']}")
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
                        "description": f"Questions covering the {topic_name} domain of the CPHQ exam."
                    },
                )
                if t_created:
                    self._log("created", "Topic", topic.name)

            created_count, skipped_count = self._load_json(filepath, topic, q_type)
            total_created += created_count
            total_skipped += skipped_count

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"=== Done! {total_created} questions created, {total_skipped} skipped (duplicates). ==="
            )
        )

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

            # Deduplicate by question text
            if Question.objects.filter(text=text).exists():
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
        Course.objects.filter(slug="cphq-exam-preparation").delete()
        Category.objects.filter(slug="healthcare-quality").delete()
        Topic.objects.filter(name__in=["Patient Safety", "Quality Review & Accountability"]).delete()
        Question.objects.all().delete()
        self.stdout.write(self.style.WARNING("Done.\n"))

    def _log(self, action: str, model: str, name: str):
        colour = self.style.SUCCESS if action == "created" else self.style.HTTP_INFO
        self.stdout.write(colour(f"  [{action}] {model}: {name}"))
