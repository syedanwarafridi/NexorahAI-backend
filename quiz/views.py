from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
import random

from .models import Topic, Question, QuizSession, QuizAttempt
from .serializers import (
    TopicSerializer, QuestionSerializer, QuestionResultSerializer,
    StartSessionSerializer, AnswerSerializer,
    QuizSessionSerializer, QuizSessionDetailSerializer,
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def topic_list(request):
    topics = Topic.objects.all()
    serializer = TopicSerializer(topics, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_session(request):
    """Start a new quiz or mock exam session."""
    serializer = StartSessionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    session_type = data['session_type']
    topic_id = data.get('topic_id')
    num_questions = data['num_questions']

    # Free tier: mock exams limited to 5 questions total across all sessions
    from payments.utils import has_active_subscription, get_mock_questions_used
    from django.conf import settings
    if session_type == 'mock' and not has_active_subscription(request.user):
        used = get_mock_questions_used(request.user)
        limit = getattr(settings, 'FREE_MOCK_QUESTIONS_LIMIT', 5)
        remaining = limit - used
        if remaining <= 0:
            return Response(
                {
                    'error': 'You have used your free mock exam questions.',
                    'code': 'subscription_required',
                    'message': f'Free users can attempt {limit} mock exam questions. Upgrade to continue.',
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        num_questions = min(num_questions, remaining)

    questions_qs = Question.objects.filter(is_active=True, question_type=session_type)
    if topic_id:
        questions_qs = questions_qs.filter(topic_id=topic_id)

    questions = list(questions_qs)
    if not questions:
        return Response({'error': 'No questions available for the selected criteria.'}, status=status.HTTP_404_NOT_FOUND)

    selected = random.sample(questions, min(num_questions, len(questions)))

    topic = None
    if topic_id:
        topic = Topic.objects.filter(id=topic_id).first()

    MOCK_TIME_LIMIT_MINUTES = 180

    session = QuizSession.objects.create(
        user=request.user,
        session_type=session_type,
        topic=topic,
        total_questions=len(selected),
        time_limit_minutes=MOCK_TIME_LIMIT_MINUTES if session_type == 'mock' else None,
    )

    for q in selected:
        QuizAttempt.objects.create(session=session, question=q)

    first_question = selected[0]
    response_data = {
        'session_id': session.id,
        'total_questions': session.total_questions,
        'time_limit_minutes': session.time_limit_minutes,
        'time_remaining_seconds': session.time_remaining_seconds,
        'first_question': QuestionSerializer(first_question).data,
    }
    return Response(response_data, status=status.HTTP_201_CREATED)


def _check_time_expired(session):
    """Auto-expire session if time limit exceeded. Returns True if expired."""
    if session.status != 'in_progress' or not session.is_time_expired:
        return False
    correct_count = session.attempts.filter(is_correct=True).count()
    session.score = correct_count
    session.status = 'timed_out'
    session.completed_at = timezone.now()
    session.save()
    return True


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_question(request, session_id, question_number):
    """Get a specific question in a session (1-indexed)."""
    session = get_object_or_404(QuizSession, id=session_id, user=request.user)
    if _check_time_expired(session):
        return Response({
            'error': 'Time is up! Your exam has been submitted automatically.',
            'code': 'time_expired',
            'score': session.score,
            'total_questions': session.total_questions,
            'score_percent': session.score_percent,
        }, status=status.HTTP_400_BAD_REQUEST)
    if session.status in ('completed', 'timed_out'):
        return Response({'error': 'Session already completed.'}, status=status.HTTP_400_BAD_REQUEST)

    attempts = session.attempts.all().order_by('id')
    if question_number < 1 or question_number > attempts.count():
        return Response({'error': 'Invalid question number.'}, status=status.HTTP_404_NOT_FOUND)

    attempt = attempts[question_number - 1]
    response_data = {
        'question_number': question_number,
        'total_questions': session.total_questions,
        'question': QuestionSerializer(attempt.question).data,
        'already_answered': attempt.selected_option is not None,
    }
    if session.time_limit_minutes:
        response_data['time_remaining_seconds'] = session.time_remaining_seconds
    return Response(response_data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_answer(request, session_id, question_number):
    """Submit an answer for a question."""
    session = get_object_or_404(QuizSession, id=session_id, user=request.user)
    if _check_time_expired(session):
        return Response({
            'error': 'Time is up! Your exam has been submitted automatically.',
            'code': 'time_expired',
            'score': session.score,
            'total_questions': session.total_questions,
            'score_percent': session.score_percent,
        }, status=status.HTTP_400_BAD_REQUEST)
    if session.status in ('completed', 'timed_out'):
        return Response({'error': 'Session already completed.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = AnswerSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    attempts = session.attempts.all().order_by('id')
    if question_number < 1 or question_number > attempts.count():
        return Response({'error': 'Invalid question number.'}, status=status.HTTP_404_NOT_FOUND)

    attempt = attempts[question_number - 1]
    if attempt.selected_option is not None:
        return Response({'error': 'Question already answered.'}, status=status.HTTP_400_BAD_REQUEST)

    selected = serializer.validated_data['selected_option']
    attempt.selected_option = selected
    attempt.is_correct = (selected == attempt.question.correct_option)
    attempt.answered_at = timezone.now()
    attempt.save()

    is_last = question_number == session.total_questions
    response_data = {
        'is_correct': attempt.is_correct,
        'correct_option': attempt.question.correct_option,
        'explanation': attempt.question.explanation,
        'is_last_question': is_last,
    }

    if is_last:
        # Auto-complete session
        correct_count = session.attempts.filter(is_correct=True).count()
        session.score = correct_count
        session.status = 'completed'
        session.completed_at = timezone.now()
        session.save()
        response_data['score'] = correct_count
        response_data['total_questions'] = session.total_questions
        response_data['score_percent'] = session.score_percent
        response_data['passed'] = session.passed
        response_data['status_label'] = session.status_label
    else:
        next_attempt = attempts[question_number]
        response_data['next_question'] = QuestionSerializer(next_attempt.question).data

    return Response(response_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def session_result(request, session_id):
    """Get full result of a completed session."""
    session = get_object_or_404(QuizSession, id=session_id, user=request.user)
    serializer = QuizSessionDetailSerializer(session)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def session_history(request):
    """List all completed quiz/mock sessions for the user."""
    sessions = QuizSession.objects.filter(user=request.user, status='completed')
    serializer = QuizSessionSerializer(sessions, many=True)
    return Response(serializer.data)
