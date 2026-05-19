from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta

from .models import StudyPlan, StudySession, CalendarEvent
from .serializers import (
    StudyPlanSerializer, StudySessionSerializer,
    CalendarEventSerializer, PlannerStatsSerializer,
)


@api_view(['GET', 'POST', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def study_plan(request):
    user = request.user

    if request.method == 'GET':
        try:
            plan = StudyPlan.objects.get(user=user)
            return Response(StudyPlanSerializer(plan).data)
        except StudyPlan.DoesNotExist:
            return Response({'detail': 'No study plan found.'}, status=status.HTTP_404_NOT_FOUND)

    # Create or update
    try:
        plan = StudyPlan.objects.get(user=user)
        serializer = StudyPlanSerializer(plan, data=request.data, partial=(request.method == 'PATCH'))
    except StudyPlan.DoesNotExist:
        serializer = StudyPlanSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save(user=user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def study_sessions(request):
    if request.method == 'GET':
        sessions = StudySession.objects.filter(user=request.user)
        serializer = StudySessionSerializer(sessions, many=True)
        return Response(serializer.data)

    serializer = StudySessionSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def planner_stats(request):
    user = request.user
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())

    # Hours studied this week
    week_sessions = StudySession.objects.filter(user=user, date__gte=week_start)
    total_minutes_this_week = week_sessions.aggregate(t=Sum('duration_minutes'))['t'] or 0
    total_hours_this_week = round(total_minutes_this_week / 60, 1)

    # Weekly goal from plan
    try:
        plan = StudyPlan.objects.get(user=user)
        weekly_goal_hours = float(plan.weekly_goal_hours)
        plan_exists = True
    except StudyPlan.DoesNotExist:
        weekly_goal_hours = 0
        plan_exists = False

    # Streak calculation
    streak = 0
    check_date = today
    while True:
        has_session = StudySession.objects.filter(user=user, date=check_date, duration_minutes__gt=0).exists()
        if has_session:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    # Quiz tasks (sessions completed vs total started)
    from quiz.models import QuizSession
    total_tasks = QuizSession.objects.filter(user=user).count()
    tasks_completed = QuizSession.objects.filter(user=user, status='completed').count()

    # Avg session minutes
    all_sessions = StudySession.objects.filter(user=user)
    avg_minutes = 0
    if all_sessions.exists():
        total = all_sessions.aggregate(t=Sum('duration_minutes'))['t'] or 0
        avg_minutes = round(total / all_sessions.count())

    stats = {
        'total_hours_this_week': total_hours_this_week,
        'weekly_goal_hours': weekly_goal_hours,
        'tasks_completed': tasks_completed,
        'total_tasks': total_tasks,
        'streak_days': streak,
        'avg_session_minutes': avg_minutes,
        'plan_exists': plan_exists,
    }
    return Response(PlannerStatsSerializer(stats).data)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def calendar_events(request):
    if request.method == 'GET':
        events = CalendarEvent.objects.filter(user=request.user)
        serializer = CalendarEventSerializer(events, many=True)
        return Response(serializer.data)

    serializer = CalendarEventSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def calendar_event_detail(request, event_id):
    from django.shortcuts import get_object_or_404
    event = get_object_or_404(CalendarEvent, id=event_id, user=request.user)

    if request.method == 'DELETE':
        event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = CalendarEventSerializer(event, data=request.data, partial=(request.method == 'PATCH'))
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
