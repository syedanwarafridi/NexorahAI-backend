from django.urls import path
from . import views

urlpatterns = [
    path('plans/', views.subscription_plans, name='subscription-plans'),
    path('checkout/', views.create_checkout_session, name='create-checkout'),
    path('status/', views.subscription_status, name='subscription-status'),
    path('verify/', views.verify_payment, name='verify-payment'),
    # path('webhook/', views.stripe_webhook, name='stripe-webhook'),  # Stripe (replaced by Lemon Squeezy)
    path('webhook/', views.lemonsqueezy_webhook, name='lemonsqueezy-webhook'),
]
