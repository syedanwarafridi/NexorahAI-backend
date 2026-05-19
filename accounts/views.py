from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import redirect
import random

from .serializers import (
    RegisterSerializer, VerifyEmailSerializer, ResendVerificationSerializer,
    LoginSerializer, ForgotPasswordSerializer, ResetPasswordSerializer,
    OnboardingSerializer, UserSerializer, ChangePasswordSerializer,
)
from .models import User
from .utils import send_verification_email


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    email = request.data.get('email')

    # Allow re-registration if previous attempt was not verified
    try:
        existing = User.objects.get(email=email)
        if not existing.email_verified:
            existing.delete()
    except User.DoesNotExist:
        pass

    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        send_verification_email(user.email, user.verification_code)
        return Response({
            'message': 'Registration successful. Check your email for the verification code.',
            'email': user.email,
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email(request):
    serializer = VerifyEmailSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        code = serializer.validated_data['code']
        try:
            user = User.objects.get(email=email, verification_code=code)
            user.email_verified = True
            user.verification_code = None
            user.save()
            return Response({'message': 'Email verified successfully.'})
        except User.DoesNotExist:
            return Response({'error': 'Invalid email or verification code.'}, status=status.HTTP_400_BAD_REQUEST)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def resend_verification(request):
    serializer = ResendVerificationSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email)
            if not user.email_verified:
                new_code = str(random.randint(100000, 999999))
                user.verification_code = new_code
                user.save()
                sent = send_verification_email(user.email, new_code)
                if sent:
                    return Response({'message': 'New verification code sent to your email.'})
                return Response({'error': 'Failed to send email. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response({'message': 'Email already verified.'})
        except User.DoesNotExist:
            pass
    return Response({'message': 'If that email exists, a verification code was sent.'})


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        try:
            user = User.objects.get(email=email)
            if user.check_password(password):
                if not user.email_verified:
                    return Response({
                        'error': 'Please verify your email before logging in.',
                        'email': user.email,
                    }, status=status.HTTP_403_FORBIDDEN)
                refresh = RefreshToken.for_user(user)
                return Response({
                    'message': 'Login successful.',
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': UserSerializer(user).data,
                })
        except User.DoesNotExist:
            pass
    return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    serializer = ForgotPasswordSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email)
            token_generator = PasswordResetTokenGenerator()
            token = token_generator.make_token(user)
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            reset_link = f"{settings.FRONTEND_URL}/reset-password?uid={uidb64}&token={token}"

            send_mail(
                subject='Reset Your Nexorah AI Password',
                message=(
                    f"Hi {user.first_name},\n\n"
                    f"Click the link below to reset your password:\n\n"
                    f"{reset_link}\n\n"
                    f"If you did not request this, please ignore this email.\n\n"
                    f"— The Nexorah AI Team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
            )
            return Response({'message': 'Password reset email sent.'})
        except User.DoesNotExist:
            pass
    return Response({'message': 'If that email exists, a reset link was sent.'})


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    serializer = ResetPasswordSerializer(data=request.data)
    if serializer.is_valid():
        try:
            uid = force_str(urlsafe_base64_decode(serializer.validated_data['uidb64']))
            user = User.objects.get(pk=uid)
            token_generator = PasswordResetTokenGenerator()
            if token_generator.check_token(user, serializer.validated_data['token']):
                user.set_password(serializer.validated_data['password'])
                user.save()
                Token.objects.filter(user=user).delete()
                return Response({'message': 'Password reset successful.'})
        except (User.DoesNotExist, ValueError):
            pass
    return Response({'error': 'Invalid or expired reset link.'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def password_reset_redirect(request, uidb64, token):
    return redirect(f"{settings.FRONTEND_URL}/reset-password/{uidb64}/{token}/")


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    user = request.user
    if request.method == 'GET':
        return Response(UserSerializer(user).data)
    serializer = UserSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({'message': 'Profile updated successfully.', 'user': serializer.data})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    serializer = ChangePasswordSerializer(data=request.data)
    if serializer.is_valid():
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return Response({'message': 'Password changed successfully.'})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def onboarding(request):
    serializer = OnboardingSerializer(data=request.data)
    if serializer.is_valid():
        user = request.user
        user.weekly_study_hours = serializer.validated_data['weekly_study_hours']
        user.onboarding_completed = True
        user.save()
        return Response({'message': 'Onboarding preferences saved.', 'user': UserSerializer(user).data})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    try:
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'error': 'Refresh token is required.'}, status=status.HTTP_400_BAD_REQUEST)
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({'message': 'Logout successful.'}, status=status.HTTP_205_RESET_CONTENT)
    except Exception:
        return Response({'error': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)
