from rest_framework import serializers
from .models import StudyPlan, StudySession, CalendarEvent


class StudyPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyPlan
        fields = (
            'id', 'start_date', 'end_date',
            'daily_goal_minutes', 'weekly_goal_hours', 'total_study_days',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'total_study_days', 'created_at', 'updated_at')


class StudySessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudySession
        fields = ('id', 'date', 'duration_minutes', 'notes', 'created_at')
        read_only_fields = ('id', 'created_at')


class CalendarEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarEvent
        fields = ('id', 'title', 'date', 'color', 'reminder_minutes_before', 'recurrence', 'created_at')
        read_only_fields = ('id', 'created_at')


class PlannerStatsSerializer(serializers.Serializer):
    total_hours_this_week = serializers.FloatField()
    weekly_goal_hours = serializers.FloatField()
    tasks_completed = serializers.IntegerField()
    total_tasks = serializers.IntegerField()
    streak_days = serializers.IntegerField()
    avg_session_minutes = serializers.FloatField()
    plan_exists = serializers.BooleanField()
