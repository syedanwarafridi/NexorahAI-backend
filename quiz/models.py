from django.db import models
from django.conf import settings


class Topic(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Question(models.Model):
    DIFFICULTY_CHOICES = [('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')]
    TYPE_CHOICES = [('quiz', 'Quiz'), ('mock', 'Mock Exam')]

    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True, related_name='questions')
    question_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='quiz')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    text = models.TextField()
    option_a = models.CharField(max_length=500)
    option_b = models.CharField(max_length=500)
    option_c = models.CharField(max_length=500)
    option_d = models.CharField(max_length=500)
    correct_option = models.CharField(max_length=1, choices=[('a','A'),('b','B'),('c','C'),('d','D')])
    explanation = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text[:80]

    def get_options(self):
        return {
            'a': self.option_a,
            'b': self.option_b,
            'c': self.option_c,
            'd': self.option_d,
        }


class QuizSession(models.Model):
    SESSION_TYPE_CHOICES = [('quiz', 'Quiz'), ('mock', 'Mock Exam')]
    STATUS_CHOICES = [('in_progress', 'In Progress'), ('completed', 'Completed')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_sessions')
    session_type = models.CharField(max_length=10, choices=SESSION_TYPE_CHOICES, default='quiz')
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True)
    questions = models.ManyToManyField(Question, through='QuizAttempt')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='in_progress')
    score = models.IntegerField(null=True, blank=True)
    total_questions = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.user.email} — {self.session_type} — {self.started_at.date()}"

    @property
    def score_percent(self):
        if self.total_questions == 0:
            return 0
        return round((self.score / self.total_questions) * 100)

    @property
    def passed(self):
        return self.score_percent >= 70

    @property
    def duration_minutes(self):
        if self.completed_at and self.started_at:
            delta = self.completed_at - self.started_at
            return round(delta.total_seconds() / 60)
        return None


class QuizAttempt(models.Model):
    session = models.ForeignKey(QuizSession, on_delete=models.CASCADE, related_name='attempts')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.CharField(max_length=1, choices=[('a','A'),('b','B'),('c','C'),('d','D')], null=True, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('session', 'question')

    def __str__(self):
        return f"Session {self.session.id} — Q{self.question.id}"
