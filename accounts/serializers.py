from rest_framework import serializers
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from .models import User
import random


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'country', 'password')

    def create(self, validated_data):
        username = validated_data['email'].split('@')[0]
        verification_code = str(random.randint(100000, 999999))

        user = User.objects.create_user(
            email=validated_data['email'],
            username=username,
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            country=validated_data.get('country', ''),
            password=validated_data['password'],
        )
        user.verification_code = verification_code
        user.save()

        print(f"\n=== VERIFICATION CODE ===\nEmail: {user.email}\nCode: {verification_code}\n=========================\n")
        return user


class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=6, write_only=True)
    token = serializers.CharField()
    uidb64 = serializers.CharField()


class OnboardingSerializer(serializers.Serializer):
    weekly_study_hours = serializers.ChoiceField(choices=[
        '1-3 hours/week',
        '4-7 hours/week',
        '8-15 hours/week',
        '15+ hours/week',
    ])


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'country', 'email_verified',
            'weekly_study_hours', 'onboarding_completed',
        )
        read_only_fields = ('id', 'email', 'email_verified', 'onboarding_completed')


class ChangePasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(min_length=6, write_only=True)
    confirm_password = serializers.CharField(min_length=6, write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return data
