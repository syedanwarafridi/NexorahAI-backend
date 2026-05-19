from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('verify-email/', views.verify_email, name='verify-email'),
    path('resend-verification/', views.resend_verification, name='resend-verification'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('forgot-password/', views.forgot_password, name='forgot-password'),
    path('reset-password/', views.reset_password, name='reset-password'),
    path('reset-password/<uidb64>/<token>/', views.password_reset_redirect, name='password-reset-redirect'),
    path('onboarding/', views.onboarding, name='onboarding'),
    path('profile/', views.user_profile, name='user-profile'),
    path('change-password/', views.change_password, name='change-password'),
]
