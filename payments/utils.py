from django.utils import timezone


def has_active_subscription(user):
    try:
        sub = user.subscription
        return sub.status == 'active' and sub.end_date > timezone.now()
    except Exception:
        return False


def get_mock_questions_used(user):
    from quiz.models import QuizAttempt
    return QuizAttempt.objects.filter(
        session__user=user,
        session__session_type='mock',
    ).count()
