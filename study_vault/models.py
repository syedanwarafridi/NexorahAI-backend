from django.db import models


class Flashcard(models.Model):
    topic = models.CharField(max_length=150)
    front = models.TextField()
    back = models.TextField()
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['topic', 'order']

    def __str__(self):
        return f"[{self.topic}] {self.front[:60]}"


class Keyword(models.Model):
    term = models.CharField(max_length=200)
    definition = models.TextField()
    topic = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['topic', 'term']

    def __str__(self):
        return self.term


class CaseStudy(models.Model):
    title = models.CharField(max_length=255)
    topic = models.CharField(max_length=150, blank=True)
    content = models.TextField()
    key_takeaways = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Case Studies'
        ordering = ['topic', 'order']

    def __str__(self):
        return self.title


class KnowledgeArticle(models.Model):
    title = models.CharField(max_length=255)
    topic = models.CharField(max_length=150, blank=True)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['topic', 'order']

    def __str__(self):
        return self.title
