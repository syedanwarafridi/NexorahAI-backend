from django.contrib import admin
from .models import StudyPlan, StudySession, CalendarEvent


@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    list_display = ('user', 'start_date', 'end_date', 'weekly_goal_hours', 'total_study_days')
    search_fields = ('user__email',)
    readonly_fields = ('total_study_days', 'created_at', 'updated_at')


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'duration_minutes', 'created_at')
    list_filter = ('date',)
    search_fields = ('user__email',)


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'date', 'color', 'recurrence')
    list_filter = ('color', 'date')
    search_fields = ('user__email', 'title')
