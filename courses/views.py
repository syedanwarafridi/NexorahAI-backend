from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.conf import settings
import openai

from .models import Course, Chapter, Domain, UserCourseProgress, UserChapterProgress, ChatMessage, ChapterQuizResult, ModuleAssessmentResult
from .serializers import (
    CourseListSerializer, CourseDetailSerializer,
    ChapterProgressSerializer, ChatMessageSerializer, ChatInputSerializer,
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def course_list(request):
    courses = Course.objects.filter(is_published=True)
    serializer = CourseListSerializer(courses, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug, is_published=True)

    # Auto-enroll user when they open a course
    UserCourseProgress.objects.get_or_create(user=request.user, course=course)

    serializer = CourseDetailSerializer(course, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_chapter_progress(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id, is_published=True)

    # Lock check — only first chapter of first domain is free
    is_free_chapter = chapter.domain and chapter.domain.order == 1 and chapter.order == 1
    if not is_free_chapter:
        from payments.utils import has_active_subscription
        if not has_active_subscription(request.user):
            return Response(
                {'error': 'Subscription required.', 'code': 'subscription_required'},
                status=status.HTTP_403_FORBIDDEN,
            )

    serializer = ChapterProgressSerializer(data=request.data)

    if serializer.is_valid():
        progress, _ = UserChapterProgress.objects.get_or_create(
            user=request.user, chapter=chapter
        )
        progress.completed = serializer.validated_data['completed']
        if progress.completed and not progress.completed_at:
            progress.completed_at = timezone.now()
        elif not progress.completed:
            progress.completed_at = None
        progress.save()

        # Ensure course enrollment exists
        UserCourseProgress.objects.get_or_create(user=request.user, course=chapter.domain.course)

        return Response({'message': 'Progress updated.', 'completed': progress.completed})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_courses(request):
    progress_qs = UserCourseProgress.objects.filter(user=request.user).select_related('course')
    courses = [p.course for p in progress_qs]
    serializer = CourseListSerializer(courses, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chapter_quick_quiz(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id, is_published=True)
    from quiz.models import Question
    from quiz.serializers import QuestionResultSerializer
    questions = Question.objects.filter(chapter=chapter, question_type='chapter_quiz', is_active=True)
    return Response({
        'chapter_id': chapter.id,
        'chapter_title': chapter.title,
        'questions': QuestionResultSerializer(questions, many=True).data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_chapter_quiz(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id, is_published=True)
    from quiz.models import Question
    from quiz.serializers import QuestionResultSerializer

    answers = request.data.get('answers', [])
    if not answers:
        return Response({'error': 'answers is required.'}, status=status.HTTP_400_BAD_REQUEST)

    questions = {
        q.id: q for q in Question.objects.filter(chapter=chapter, question_type='chapter_quiz', is_active=True)
    }

    results = []
    correct_count = 0
    for answer in answers:
        question_id = answer.get('question_id')
        selected = str(answer.get('selected_option', '')).lower().strip()
        question = questions.get(question_id)
        if not question:
            continue
        is_correct = selected == question.correct_option
        if is_correct:
            correct_count += 1
        results.append({
            'question_id': question_id,
            'selected_option': selected,
            'correct_option': question.correct_option,
            'is_correct': is_correct,
            'explanation': question.explanation,
        })

    total = len(results)
    score_percent = round((correct_count / total) * 100) if total else 0
    passed = score_percent >= 80

    ChapterQuizResult.objects.create(
        user=request.user,
        chapter=chapter,
        score=correct_count,
        total_questions=total,
    )

    return Response({
        'chapter_id': chapter.id,
        'chapter_title': chapter.title,
        'score': correct_count,
        'total_questions': total,
        'score_percent': score_percent,
        'passed': passed,
        'status': 'Passed' if passed else 'Needs Improvement',
        'results': results,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def module_assessment(request, domain_id):
    """Full Module MCQ Assessment — covers the complete module, not just one chapter."""
    domain = get_object_or_404(Domain, id=domain_id, is_published=True)
    from quiz.models import Question
    from quiz.serializers import QuestionResultSerializer
    questions = Question.objects.filter(domain=domain, question_type='module_assessment', is_active=True)
    return Response({
        'domain_id': domain.id,
        'domain_title': domain.title,
        'questions': QuestionResultSerializer(questions, many=True).data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_module_assessment(request, domain_id):
    domain = get_object_or_404(Domain, id=domain_id, is_published=True)
    from quiz.models import Question

    answers = request.data.get('answers', [])
    if not answers:
        return Response({'error': 'answers is required.'}, status=status.HTTP_400_BAD_REQUEST)

    questions = {
        q.id: q for q in Question.objects.filter(domain=domain, question_type='module_assessment', is_active=True)
    }

    results = []
    correct_count = 0
    for answer in answers:
        question_id = answer.get('question_id')
        selected = str(answer.get('selected_option', '')).lower().strip()
        question = questions.get(question_id)
        if not question:
            continue
        is_correct = selected == question.correct_option
        if is_correct:
            correct_count += 1
        results.append({
            'question_id': question_id,
            'selected_option': selected,
            'correct_option': question.correct_option,
            'is_correct': is_correct,
            'explanation': question.explanation,
        })

    total = len(results)
    score_percent = round((correct_count / total) * 100) if total else 0
    passed = score_percent >= 80

    ModuleAssessmentResult.objects.create(
        user=request.user,
        domain=domain,
        score=correct_count,
        total_questions=total,
    )

    return Response({
        'domain_id': domain.id,
        'domain_title': domain.title,
        'score': correct_count,
        'total_questions': total,
        'score_percent': score_percent,
        'passed': passed,
        'status': 'Passed' if passed else 'Needs Improvement',
        'results': results,
    })


def _module_weak_strong(user):
    """Same weak/strong aggregation as weak_topics, but at the full-module level."""
    results = ModuleAssessmentResult.objects.filter(user=user).select_related('domain')

    module_scores = {}
    for r in results:
        did = r.domain.id
        if did not in module_scores:
            module_scores[did] = {
                'domain_id': r.domain.id,
                'domain_title': r.domain.title,
                'scores': [],
            }
        module_scores[did]['scores'].append(r.score_percent)

    weak, strong = [], []
    for did, data in module_scores.items():
        avg = round(sum(data['scores']) / len(data['scores']))
        entry = {
            'domain_id': data['domain_id'],
            'domain_title': data['domain_title'],
            'average_score_percent': avg,
            'attempts': len(data['scores']),
            'status': 'Passed' if avg >= 80 else 'Needs Improvement',
        }
        if avg < 80:
            entry['recommendation'] = f"Your score in {data['domain_title']} is {avg}%. Review the module content and retake the assessment to strengthen this area."
            weak.append(entry)
        else:
            strong.append(entry)

    weak.sort(key=lambda x: x['average_score_percent'])
    strong.sort(key=lambda x: x['average_score_percent'], reverse=True)
    return weak, strong


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def weak_topics(request):
    results = ChapterQuizResult.objects.filter(user=request.user).select_related(
        'chapter__domain'
    )
    weak_modules, strong_modules = _module_weak_strong(request.user)

    if not results.exists():
        return Response({
            'message': 'Complete some chapter quizzes to get topic recommendations.',
            'weak_topics': [],
            'strong_topics': [],
            'weak_modules': weak_modules,
            'strong_modules': strong_modules,
            'overall_score_percent': None,
        })

    # Aggregate latest result per chapter
    from django.db.models import Avg
    chapter_scores = {}
    for r in results:
        cid = r.chapter.id
        if cid not in chapter_scores:
            chapter_scores[cid] = {
                'chapter_id': r.chapter.id,
                'chapter_title': r.chapter.title,
                'domain_title': r.chapter.domain.title if r.chapter.domain else '',
                'scores': [],
            }
        chapter_scores[cid]['scores'].append(r.score_percent)

    weak = []
    strong = []
    all_scores = []

    for cid, data in chapter_scores.items():
        avg = round(sum(data['scores']) / len(data['scores']))
        all_scores.append(avg)
        entry = {
            'chapter_id': data['chapter_id'],
            'chapter_title': data['chapter_title'],
            'domain_title': data['domain_title'],
            'average_score_percent': avg,
            'attempts': len(data['scores']),
            'status': 'Passed' if avg >= 80 else 'Needs Improvement',
        }
        if avg < 80:
            entry['recommendation'] = f"Your score in {data['chapter_title']} is {avg}%. Review the chapter content and retry the quiz to strengthen this area."
            weak.append(entry)
        else:
            strong.append(entry)

    weak.sort(key=lambda x: x['average_score_percent'])
    strong.sort(key=lambda x: x['average_score_percent'], reverse=True)
    overall = round(sum(all_scores) / len(all_scores)) if all_scores else 0

    return Response({
        'overall_score_percent': overall,
        'weak_topics': weak,
        'strong_topics': strong,
        'weak_modules': weak_modules,
        'strong_modules': strong_modules,
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def chat(request, course_id):
    course = get_object_or_404(Course, id=course_id, is_published=True)

    if request.method == 'GET':
        messages = ChatMessage.objects.filter(user=request.user, course=course)
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)

    serializer = ChatInputSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user_message = serializer.validated_data['message']

    # Save user message
    ChatMessage.objects.create(user=request.user, course=course, role='user', content=user_message)

    # Build context: course domains and chapters
    domains = course.domains.filter(is_published=True).prefetch_related('chapters')
    course_outline = '\n'.join(
        f"- {d.title}: " + ', '.join(ch.title for ch in d.chapters.filter(is_published=True))
        for d in domains
    )

    # Build message history (last 10 exchanges = 20 messages)
    history = ChatMessage.objects.filter(
        user=request.user, course=course
    ).order_by('-created_at')[:20]
    history_messages = [
        {'role': m.role, 'content': m.content}
        for m in reversed(history)
    ]

    system_prompt = f"""You are an expert AI tutor helping a student prepare for the CPHQ (Certified Professional in Healthcare Quality) exam.

Course: {course.title}

Course outline:
{course_outline}

Your role:
- Answer questions clearly and accurately about healthcare quality, patient safety, and CPHQ exam topics
- Explain concepts with real-world healthcare examples when helpful
- When asked about quiz or exam questions, guide the student to think through the answer rather than just giving it
- Keep responses concise and focused — suitable for a student studying for a professional certification
- If asked something unrelated to CPHQ or healthcare quality, politely redirect the conversation

Student name: {request.user.first_name or 'Student'}"""

    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {'role': 'system', 'content': system_prompt},
                *history_messages,
            ],
            max_tokens=600,
            temperature=0.7,
        )
        ai_reply = response.choices[0].message.content.strip()
    except Exception as e:
        ai_reply = f"I'm temporarily unavailable. Please try again in a moment. (Error: {str(e)[:100]})"

    ChatMessage.objects.create(user=request.user, course=course, role='assistant', content=ai_reply)
    return Response({'reply': ai_reply})
