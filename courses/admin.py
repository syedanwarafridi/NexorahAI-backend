from django.contrib import admin
from .models import Category, Course, Domain, Chapter, Document, UserCourseProgress, UserChapterProgress, ChatMessage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


class DocumentInline(admin.TabularInline):
    model = Document
    extra = 1


class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 1
    fields = ('title', 'order', 'duration_minutes', 'video_url', 'video_file', 'is_published')


class DomainInline(admin.TabularInline):
    model = Domain
    extra = 1
    fields = ('title', 'order', 'description', 'is_published')
    show_change_link = True


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'total_domains', 'total_chapters', 'is_published', 'order', 'created_at')
    list_filter = ('is_published', 'category')
    search_fields = ('title', 'about', 'description')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('is_published', 'order')
    inlines = [DomainInline]


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'total_chapters', 'is_published')
    list_filter = ('course', 'is_published')
    search_fields = ('title', 'course__title')
    list_editable = ('order', 'is_published')
    inlines = [ChapterInline]


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('title', 'domain', 'get_course', 'order', 'duration_minutes', 'is_published')
    list_filter = ('domain__course', 'is_published')
    search_fields = ('title', 'domain__title', 'domain__course__title')
    list_editable = ('order', 'is_published')
    inlines = [DocumentInline]

    @admin.display(description='Course', ordering='domain__course__title')
    def get_course(self, obj):
        return obj.domain.course if obj.domain else '-'


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
