from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import Course, Chapter, Domain, UserCourseProgress, UserChapterProgress, ChatMessage
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

    # Placeholder response — OpenAI will be integrated tomorrow
    ai_reply = (
        "AI tutor is not yet connected. OpenAI integration coming soon. "
        "Your question has been recorded."
    )
    ChatMessage.objects.create(user=request.user, course=course, role='assistant', content=ai_reply)

    return Response({'reply': ai_reply})
