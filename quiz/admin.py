from django.contrib import admin
from .models import Topic, Question, QuizSession, QuizAttempt


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text_preview', 'topic', 'question_type', 'difficulty', 'is_active', 'created_at')
    list_filter = ('question_type', 'difficulty', 'is_active', 'topic')
    search_fields = ('text',)
    list_editable = ('is_active',)

    fieldsets = (
        ('Question', {'fields': ('topic', 'question_type', 'difficulty', 'text', 'is_active')}),
        ('Options', {'fields': ('option_a', 'option_b', 'option_c', 'option_d', 'correct_option')}),
        ('Explanation', {'fields': ('explanation',)}),
    )

    def text_preview(self, obj):
        return obj.text[:80]
    text_preview.short_description = 'Question'


class QuizAttemptInline(admin.TabularInline):
    model = QuizAttempt
    extra = 0
    readonly_fields = ('question', 'selected_option', 'is_correct', 'answered_at')
    can_delete = False


@admin.register(QuizSession)
class QuizSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'session_type', 'status', 'score', 'total_questions', 'score_percent', 'started_at')
    list_filter = ('session_type', 'status')
    search_fields = ('user__email',)
    readonly_fields = ('started_at', 'completed_at')
    inlines = [QuizAttemptInline]

    def score_percent(self, obj):
        return f"{obj.score_percent}%"
    score_percent.short_description = 'Score %'
