from rest_framework import serializers


class DashboardStatsSerializer(serializers.Serializer):
    overall_progress_percent = serializers.IntegerField()
    readiness_score = serializers.IntegerField()
    study_streak_days = serializers.IntegerField()
    hours_this_week = serializers.FloatField()
    weekly_goal_hours = serializers.FloatField()
    weakest_topic = serializers.CharField(allow_null=True)
    weakest_topic_percent = serializers.IntegerField(allow_null=True)
    strongest_topic = serializers.CharField(allow_null=True)
