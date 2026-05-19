from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .models import Flashcard, Keyword, CaseStudy, KnowledgeArticle
from .serializers import (
    FlashcardSerializer, KeywordSerializer,
    CaseStudySerializer, KnowledgeArticleSerializer,
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def flashcard_list(request):
    topic = request.query_params.get('topic')
    qs = Flashcard.objects.filter(is_active=True)
    if topic:
        qs = qs.filter(topic__icontains=topic)
    return Response(FlashcardSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def keyword_list(request):
    topic = request.query_params.get('topic')
    qs = Keyword.objects.filter(is_active=True)
    if topic:
        qs = qs.filter(topic__icontains=topic)
    return Response(KeywordSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def case_study_list(request):
    topic = request.query_params.get('topic')
    qs = CaseStudy.objects.filter(is_active=True)
    if topic:
        qs = qs.filter(topic__icontains=topic)
    return Response(CaseStudySerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def case_study_detail(request, pk):
    from django.shortcuts import get_object_or_404
    item = get_object_or_404(CaseStudy, pk=pk, is_active=True)
    return Response(CaseStudySerializer(item).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def knowledge_article_list(request):
    topic = request.query_params.get('topic')
    qs = KnowledgeArticle.objects.filter(is_active=True)
    if topic:
        qs = qs.filter(topic__icontains=topic)
    return Response(KnowledgeArticleSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def knowledge_article_detail(request, pk):
    from django.shortcuts import get_object_or_404
    item = get_object_or_404(KnowledgeArticle, pk=pk, is_active=True)
    return Response(KnowledgeArticleSerializer(item).data)
