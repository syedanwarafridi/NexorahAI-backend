from rest_framework import serializers
from .models import Topic, Question, QuizSession, QuizAttempt


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ('id', 'name', 'description')


class QuestionSerializer(serializers.ModelSerializer):
    options = serializers.SerializerMethodField()
    topic_name = serializers.CharField(source='topic.name', read_only=True)

    class Meta:
        model = Question
        fields = ('id', 'text', 'options', 'difficulty', 'topic_name')

    def get_options(self, obj):
        return [
            {'key': 'a', 'text': obj.option_a},
            {'key': 'b', 'text': obj.option_b},
            {'key': 'c', 'text': obj.option_c},
            {'key': 'd', 'text': obj.option_d},
        ]


class QuestionResultSerializer(serializers.ModelSerializer):
    """Includes correct answer and explanation — used after answering."""
    options = serializers.SerializerMethodField()
    topic_name = serializers.CharField(source='topic.name', read_only=True)

    class Meta:
        model = Question
        fields = ('id', 'text', 'options', 'correct_option', 'explanation', 'difficulty', 'topic_name')

    def get_options(self, obj):
        return [
            {'key': 'a', 'text': obj.option_a},
            {'key': 'b', 'text': obj.option_b},
            {'key': 'c', 'text': obj.option_c},
            {'key': 'd', 'text': obj.option_d},
        ]


class StartSessionSerializer(serializers.Serializer):
    session_type = serializers.ChoiceField(choices=['quiz', 'mock'])
    topic_id = serializers.IntegerField(required=False, allow_null=True)
    num_questions = serializers.IntegerField(default=10, min_value=1, max_value=50)


class AnswerSerializer(serializers.Serializer):
    selected_option = serializers.ChoiceField(choices=['a', 'b', 'c', 'd'])


class QuizAttemptSerializer(serializers.ModelSerializer):
    question = QuestionResultSerializer(read_only=True)

    class Meta:
        model = QuizAttempt
        fields = ('id', 'question', 'selected_option', 'is_correct', 'answered_at')


class QuizSessionSerializer(serializers.ModelSerializer):
    score_percent = serializers.IntegerField(read_only=True)
    passed = serializers.BooleanField(read_only=True)
    duration_minutes = serializers.IntegerField(read_only=True)
    topic_name = serializers.CharField(source='topic.name', read_only=True, allow_null=True)

    class Meta:
        model = QuizSession
        fields = (
            'id', 'session_type', 'topic_name', 'status',
            'score', 'total_questions', 'score_percent', 'passed',
            'duration_minutes', 'started_at', 'completed_at',
        )


class QuizSessionDetailSerializer(QuizSessionSerializer):
    attempts = QuizAttemptSerializer(many=True, read_only=True)

    class Meta(QuizSessionSerializer.Meta):
        fields = QuizSessionSerializer.Meta.fields + ('attempts',)
