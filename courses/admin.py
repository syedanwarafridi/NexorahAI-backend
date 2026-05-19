from django.contrib import admin
from .models import Category, Course, Chapter, Document, UserCourseProgress, UserChapterProgress, ChatMessage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 1
    fields = ('title', 'order', 'duration_minutes', 'video_url', 'video_file', 'is_published')


class DocumentInline(admin.TabularInline):
    model = Document
    extra = 1


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'total_chapters', 'is_published', 'order', 'created_at')
    list_filter = ('is_published', 'category')
    search_fields = ('title', 'about', 'description')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('is_published', 'order')
    inlines = [ChapterInline]


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'duration_minutes', 'is_published')
    list_filter = ('course', 'is_published')
    search_fields = ('title', 'course__title')
    list_editable = ('order', 'is_published')
    inlines = [DocumentInline]


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'chapter', 'created_at')
    search_fields = ('title',)


@admin.register(UserCourseProgress)
class UserCourseProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'progress_percent', 'enrolled_at', 'last_accessed')
    list_filter = ('course',)
    search_fields = ('user__email', 'course__title')
    readonly_fields = ('enrolled_at', 'last_accessed')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'role', 'created_at')
    list_filter = ('role', 'course')
    search_fields = ('user__email', 'content')
    readonly_fields = ('created_at',)
