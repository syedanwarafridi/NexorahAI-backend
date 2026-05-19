from rest_framework import serializers
from .models import Category, Course, Chapter, Document, UserCourseProgress, UserChapterProgress, ChatMessage


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'description')


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ('id', 'title', 'file')


class ChapterSerializer(serializers.ModelSerializer):
    documents = DocumentSerializer(many=True, read_only=True)
    is_completed = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = ('id', 'title', 'order', 'duration_minutes', 'video_url', 'video_file', 'documents', 'is_completed')

    def get_is_completed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return UserChapterProgress.objects.filter(
                user=request.user, chapter=obj, completed=True
            ).exists()
        return False


class CourseListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    total_chapters = serializers.IntegerField(read_only=True)
    total_duration_minutes = serializers.FloatField(read_only=True)
    progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ('id', 'title', 'slug', 'category', 'about', 'thumbnail',
                  'total_chapters', 'total_duration_minutes', 'progress_percent')

    def get_progress_percent(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            progress = UserCourseProgress.objects.filter(user=request.user, course=obj).first()
            if progress:
                return progress.progress_percent
        return 0


class CourseDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    chapters = ChapterSerializer(many=True, read_only=True)
    total_chapters = serializers.IntegerField(read_only=True)
    total_duration_minutes = serializers.FloatField(read_only=True)
    progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ('id', 'title', 'slug', 'category', 'about', 'description',
                  'thumbnail', 'total_chapters', 'total_duration_minutes',
                  'progress_percent', 'chapters')

    def get_progress_percent(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            progress = UserCourseProgress.objects.filter(user=request.user, course=obj).first()
            if progress:
                return progress.progress_percent
        return 0


class ChapterProgressSerializer(serializers.Serializer):
    completed = serializers.BooleanField()


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ('id', 'role', 'content', 'created_at')
        read_only_fields = ('id', 'role', 'created_at')


class ChatInputSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000)
