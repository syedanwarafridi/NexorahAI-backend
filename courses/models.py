from django.db import models
from django.db.models import Sum
from django.conf import settings


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Course(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='courses')
    about = models.TextField(blank=True)
    description = models.TextField(blank=True)
    thumbnail = models.ImageField(upload_to='courses/thumbnails/', blank=True, null=True)
    is_published = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'title']

    def __str__(self):
        return self.title

    @property
    def total_chapters(self):
        return Chapter.objects.filter(domain__course=self, is_published=True).count()

    @property
    def total_duration_minutes(self):
        result = Chapter.objects.filter(domain__course=self, is_published=True).aggregate(
            total=Sum('duration_minutes')
        )['total']
        return float(result or 0)

    @property
    def total_domains(self):
        return self.domains.filter(is_published=True).count()


class Domain(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='domains')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} — {self.title}"

    @property
    def total_chapters(self):
        return self.chapters.filter(is_published=True).count()

    @property
    def total_duration_minutes(self):
        result = self.chapters.filter(is_published=True).aggregate(
            total=Sum('duration_minutes')
        )['total']
        return float(result or 0)


class Chapter(models.Model):
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='chapters', null=True, blank=True)
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    duration_minutes = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    video_url = models.URLField(blank=True)
    video_file = models.FileField(upload_to='courses/videos/', blank=True, null=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.domain.title} — {self.title}" if self.domain else self.title

    @property
    def course(self):
        return self.domain.course if self.domain else None


class Document(models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='courses/documents/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class UserCourseProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='course_progress')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='user_progress')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'course')

    def __str__(self):
        return f"{self.user.email} — {self.course.title}"

    @property
    def completed_chapters_count(self):
        return UserChapterProgress.objects.filter(
            user=self.user,
            chapter__domain__course=self.course,
            completed=True,
        ).count()

    @property
    def progress_percent(self):
        total = self.course.total_chapters
        if total == 0:
            return 0
        return round((self.completed_chapters_count / total) * 100)


class UserChapterProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chapter_progress')
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='user_progress')
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_accessed = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'chapter')

    def __str__(self):
        return f"{self.user.email} — {self.chapter.title}"


class ChapterQuizResult(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chapter_quiz_results')
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='quiz_results')
    score = models.PositiveIntegerField()
    total_questions = models.PositiveIntegerField()
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-completed_at']

    def __str__(self):
        return f"{self.user.email} — {self.chapter.title} — {self.score}/{self.total_questions}"

    @property
    def score_percent(self):
        if self.total_questions == 0:
            return 0
        return round((self.score / self.total_questions) * 100)

    @property
    def passed(self):
        return self.score_percent >= 80

    @property
    def status_label(self):
        return 'Passed' if self.passed else 'Needs Improvement'


class ModuleAssessmentResult(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='module_assessment_results')
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='assessment_results')
    score = models.PositiveIntegerField()
    total_questions = models.PositiveIntegerField()
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-completed_at']

    def __str__(self):
        return f"{self.user.email} — {self.domain.title} — {self.score}/{self.total_questions}"

    @property
    def score_percent(self):
        if self.total_questions == 0:
            return 0
        return round((self.score / self.total_questions) * 100)

    @property
    def passed(self):
        return self.score_percent >= 80

    @property
    def status_label(self):
        return 'Passed' if self.passed else 'Needs Improvement'


class ChatMessage(models.Model):
    ROLE_CHOICES = [('user', 'User'), ('assistant', 'Assistant')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_messages')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='chat_messages', null=True, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.email} [{self.role}]: {self.content[:60]}"
