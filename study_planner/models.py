from django.db import models
from django.conf import settings
from django.utils import timezone


class StudyPlan(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='study_plan')
    start_date = models.DateField()
    end_date = models.DateField()
    daily_goal_minutes = models.IntegerField(default=30)
    weekly_goal_hours = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    total_study_days = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} — {self.start_date} to {self.end_date}"

    def save(self, *args, **kwargs):
        if self.start_date and self.end_date:
            delta = self.end_date - self.start_date
            self.total_study_days = max(delta.days, 0)
        super().save(*args, **kwargs)


class StudySession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='study_sessions')
    date = models.DateField(default=timezone.now)
    duration_minutes = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.email} — {self.date} — {self.duration_minutes}min"


class CalendarEvent(models.Model):
    COLOR_CHOICES = [('green', 'Green'), ('red', 'Red'), ('blue', 'Blue'), ('orange', 'Orange')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='calendar_events')
    title = models.CharField(max_length=255)
    date = models.DateField()
    color = models.CharField(max_length=10, choices=COLOR_CHOICES, default='green')
    reminder_minutes_before = models.IntegerField(default=20)
    recurrence = models.CharField(max_length=50, blank=True)  # e.g. "weekly", "daily"
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f"{self.user.email} — {self.title} — {self.date}"
