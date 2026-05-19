from django.contrib import admin
from .models import Flashcard, Keyword, CaseStudy, KnowledgeArticle


@admin.register(Flashcard)
class FlashcardAdmin(admin.ModelAdmin):
    list_display = ('topic', 'front_preview', 'is_active', 'order')
    list_filter = ('topic', 'is_active')
    list_editable = ('is_active', 'order')
    search_fields = ('topic', 'front', 'back')

    def front_preview(self, obj):
        return obj.front[:80]
    front_preview.short_description = 'Front'


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ('term', 'topic', 'is_active', 'order')
    list_filter = ('topic', 'is_active')
    list_editable = ('is_active', 'order')
    search_fields = ('term', 'definition', 'topic')


@admin.register(CaseStudy)
class CaseStudyAdmin(admin.ModelAdmin):
    list_display = ('title', 'topic', 'is_active', 'order', 'created_at')
    list_filter = ('topic', 'is_active')
    list_editable = ('is_active', 'order')
    search_fields = ('title', 'topic', 'content')


@admin.register(KnowledgeArticle)
class KnowledgeArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'topic', 'is_active', 'order', 'created_at')
    list_filter = ('topic', 'is_active')
    list_editable = ('is_active', 'order')
    search_fields = ('title', 'topic', 'content')
