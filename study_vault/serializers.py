from rest_framework import serializers
from .models import Flashcard, Keyword, CaseStudy, KnowledgeArticle


class FlashcardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flashcard
        fields = ('id', 'topic', 'front', 'back', 'order')


class KeywordSerializer(serializers.ModelSerializer):
    class Meta:
        model = Keyword
        fields = ('id', 'term', 'definition', 'topic', 'order')


class CaseStudySerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseStudy
        fields = ('id', 'title', 'topic', 'content', 'key_takeaways', 'order')


class KnowledgeArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeArticle
        fields = ('id', 'title', 'topic', 'content', 'order')
