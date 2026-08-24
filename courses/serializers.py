from rest_framework import serializers
from .models import Category, Course, Domain, Chapter, Document, UserCourseProgress, UserChapterProgress, ChatMessage


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
    is_locked = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = (
            'id', 'title', 'order', 'duration_minutes',
            'video_url', 'video_file', 'documents', 'is_completed', 'is_locked',
        )

    def get_is_locked(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return True
        # First chapter of first domain is always free
        if obj.domain and obj.domain.order == 1 and obj.order == 1:
            return False
        from payments.utils import has_active_subscription
        return not has_active_subscription(request.user)

    def get_is_completed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return UserChapterProgress.objects.filter(
                user=request.user, chapter=obj, completed=True
            ).exists()
        return False


class DomainSerializer(serializers.ModelSerializer):
    chapters = ChapterSerializer(many=True, read_only=True)
    total_chapters = serializers.IntegerField(read_only=True)
    total_duration_minutes = serializers.FloatField(read_only=True)
    completed_chapters = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = Domain
        fields = (
            'id', 'title', 'description', 'order',
            'total_chapters', 'total_duration_minutes',
            'completed_chapters', 'progress_percent',
            'chapters',
        )

    def get_completed_chapters(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return UserChapterProgress.objects.filter(
                user=request.user, chapter__domain=obj, completed=True
            ).count()
        return 0

    def get_progress_percent(self, obj):
        total = obj.total_chapters
        if total == 0:
            return 0
        return round((self.get_completed_chapters(obj) / total) * 100)


class CourseListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    total_domains = serializers.IntegerField(read_only=True)
    total_chapters = serializers.IntegerField(read_only=True)
    total_duration_minutes = serializers.FloatField(read_only=True)
    progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = (
            'id', 'title', 'slug', 'category', 'about', 'thumbnail',
            'total_domains', 'total_chapters', 'total_duration_minutes',
            'progress_percent',
        )

    def get_progress_percent(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            progress = UserCourseProgress.objects.filter(user=request.user, course=obj).first()
            if progress:
                return progress.progress_percent
        return 0


class CourseDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    domains = DomainSerializer(many=True, read_only=True)
    total_domains = serializers.IntegerField(read_only=True)
    total_chapters = serializers.IntegerField(read_only=True)
    total_duration_minutes = serializers.FloatField(read_only=True)
    progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = (
            'id', 'title', 'slug', 'category', 'about', 'description',
            'thumbnail', 'total_domains', 'total_chapters',
            'total_duration_minutes', 'progress_percent', 'domains',
        )

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
