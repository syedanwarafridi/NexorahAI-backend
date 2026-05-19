from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum, Avg, Count
from datetime import timedelta

from .serializers import DashboardStatsSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    user = request.user
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())

    # ── Overall course progress ─────────────────────────────────────────────
    from courses.models import UserCourseProgress, Course
    enrolled = UserCourseProgress.objects.filter(user=user)
    total_courses = enrolled.count()

    if total_courses > 0:
        avg_progress = sum(p.progress_percent for p in enrolled) / total_courses
        overall_progress = round(avg_progress)
    else:
        overall_progress = 0

    # ── Readiness score — based on quiz performance ─────────────────────────
    from quiz.models import QuizSession
    completed_sessions = QuizSession.objects.filter(user=user, status='completed')
    if completed_sessions.exists():
        avg_score = sum(s.score_percent for s in completed_sessions) / completed_sessions.count()
        readiness_score = round(avg_score)
    else:
        readiness_score = 0

    # ── Study streak ────────────────────────────────────────────────────────
    from study_planner.models import StudySession, StudyPlan
    streak = 0
    check_date = today
    while True:
        has_session = StudySession.objects.filter(user=user, date=check_date, duration_minutes__gt=0).exists()
        if has_session:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    # ── Hours this week ─────────────────────────────────────────────────────
    week_minutes = StudySession.objects.filter(
        user=user, date__gte=week_start
    ).aggregate(t=Sum('duration_minutes'))['t'] or 0
    hours_this_week = round(week_minutes / 60, 1)

    # ── Weekly goal ─────────────────────────────────────────────────────────
    try:
        plan = StudyPlan.objects.get(user=user)
        weekly_goal_hours = float(plan.weekly_goal_hours)
    except StudyPlan.DoesNotExist:
        weekly_goal_hours = 0

    # ── Weakest / strongest topic (by quiz performance) ─────────────────────
    weakest_topic = None
    weakest_topic_percent = None
    strongest_topic = None

    topic_stats = (
        completed_sessions
        .exclude(topic=None)
        .values('topic__name')
        .annotate(avg_score=Avg('score') * 100 / Avg('total_questions'))
        .order_by('avg_score')
    )

    if topic_stats.exists():
        weakest = topic_stats.first()
        strongest = topic_stats.last()
        weakest_topic = weakest['topic__name']
        weakest_topic_percent = round(weakest['avg_score'] or 0)
        strongest_topic = strongest['topic__name']

    stats = {
        'overall_progress_percent': overall_progress,
        'readiness_score': readiness_score,
        'study_streak_days': streak,
        'hours_this_week': hours_this_week,
        'weekly_goal_hours': weekly_goal_hours,
        'weakest_topic': weakest_topic,
        'weakest_topic_percent': weakest_topic_percent,
        'strongest_topic': strongest_topic,
    }

    return Response(DashboardStatsSerializer(stats).data)
