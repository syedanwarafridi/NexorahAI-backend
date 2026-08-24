from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum
from django.conf import settings
from datetime import timedelta, date
import openai
import json

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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_plan(request):
    """
    AI-generated personalized CPHQ study plan.

    Request body:
        exam_date         (str, required)  — ISO date e.g. "2026-09-01"
        hours_per_week    (int, required)  — available study hours per week
        weak_topics       (list, optional) — list of topic names to focus on
        notes             (str, optional)  — any extra context for the AI
    """
    exam_date_str = request.data.get('exam_date')
    hours_per_week = request.data.get('hours_per_week')

    if not exam_date_str or not hours_per_week:
        return Response(
            {'error': 'exam_date and hours_per_week are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        exam_date = date.fromisoformat(exam_date_str)
    except ValueError:
        return Response({'error': 'Invalid exam_date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

    today = timezone.now().date()
    days_until_exam = (exam_date - today).days
    if days_until_exam <= 0:
        return Response({'error': 'exam_date must be in the future.'}, status=status.HTTP_400_BAD_REQUEST)

    weak_topics = request.data.get('weak_topics', [])
    extra_notes = request.data.get('notes', '')

    # Gather user's quiz performance for context
    from quiz.models import QuizSession
    from django.db.models import Avg
    completed = QuizSession.objects.filter(user=request.user, status='completed')
    quiz_summary = []
    topic_perf = (
        completed.exclude(topic=None)
        .values('topic__name')
        .annotate(avg=Avg('score') * 100.0 / Avg('total_questions'))
        .order_by('avg')
    )
    for tp in topic_perf:
        quiz_summary.append(f"- {tp['topic__name']}: {round(tp['avg'] or 0)}%")

    # All 7 CPHQ domains
    cphq_domains = [
        'Patient Safety',
        'Quality Review & Accountability',
        'Performance and Process Improvement',
        'Information Management',
        'Patient/Member Experience',
        'Regulatory and Accreditation',
        'Quality Leadership and Integration',
    ]

    prompt = f"""You are an expert CPHQ exam coach. Generate a personalized study plan in JSON format.

Student info:
- Exam date: {exam_date_str}
- Days until exam: {days_until_exam}
- Available study hours per week: {hours_per_week}
- Weak topics to focus on: {', '.join(weak_topics) if weak_topics else 'Not specified'}
- Quiz performance by topic:
{chr(10).join(quiz_summary) if quiz_summary else '  No quiz history yet'}
- Additional notes: {extra_notes or 'None'}

Course details:
- Total video content: 97 hours across 7 domains
- Recommended study approach: Watch videos + complete domain quizzes + full mock exams in final weeks
CPHQ domains to cover: {', '.join(cphq_domains)}

Return ONLY valid JSON with this exact structure:
{{
  "summary": "2-3 sentence overview of the plan",
  "daily_goal_minutes": <integer>,
  "weekly_goal_hours": <float>,
  "focus_areas": ["topic1", "topic2"],
  "calendar_events": [
    {{"title": "Study: Patient Safety", "date": "YYYY-MM-DD", "color": "blue"}},
    ...
  ],
  "tips": ["tip1", "tip2", "tip3"]
}}

Rules:
- calendar_events should span from today ({today.isoformat()}) to {exam_date_str}
- Generate between 15 and 40 calendar events — key study milestones, topic reviews, and mock exam days
- Distribute weak topics earlier and more frequently
- Schedule at least 2 full mock exam sessions in the final 2 weeks
- Use colors: blue=study session, orange=review, red=mock exam, green=milestone
- daily_goal_minutes and weekly_goal_hours must match hours_per_week ({hours_per_week})
- Return ONLY the JSON object, no markdown, no explanation"""

    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=2000,
            temperature=0.5,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        plan_data = json.loads(raw)
    except json.JSONDecodeError:
        return Response({'error': 'AI returned invalid data. Please try again.'}, status=status.HTTP_502_BAD_GATEWAY)
    except Exception as e:
        return Response({'error': f'AI service error: {str(e)[:200]}'}, status=status.HTTP_502_BAD_GATEWAY)

    # Save / update the StudyPlan
    plan, _ = StudyPlan.objects.update_or_create(
        user=request.user,
        defaults={
            'start_date': today,
            'end_date': exam_date,
            'daily_goal_minutes': plan_data.get('daily_goal_minutes', 30),
            'weekly_goal_hours': plan_data.get('weekly_goal_hours', hours_per_week),
        },
    )

    # Create calendar events (clear old AI-generated ones first)
    CalendarEvent.objects.filter(user=request.user).delete()
    created_events = []
    for ev in plan_data.get('calendar_events', []):
        try:
            ev_date = date.fromisoformat(ev['date'])
        except (ValueError, KeyError):
            continue
        event = CalendarEvent.objects.create(
            user=request.user,
            title=ev.get('title', 'Study Session'),
            date=ev_date,
            color=ev.get('color', 'blue'),
        )
        created_events.append(CalendarEventSerializer(event).data)

    return Response({
        'plan': StudyPlanSerializer(plan).data,
        'summary': plan_data.get('summary', ''),
        'focus_areas': plan_data.get('focus_areas', []),
        'tips': plan_data.get('tips', []),
        'calendar_events': created_events,
    }, status=status.HTTP_201_CREATED)
