# --- Stripe (replaced by Lemon Squeezy) ---
# import stripe
# from django.conf import settings
# from django.utils import timezone
# from django.views.decorators.csrf import csrf_exempt
# from rest_framework import status
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import IsAuthenticated, AllowAny
# from rest_framework.response import Response
# from datetime import timedelta
#
# from .models import SubscriptionPlan, UserSubscription
# from .serializers import SubscriptionPlanSerializer, UserSubscriptionSerializer
#
# stripe.api_key = settings.STRIPE_SECRET_KEY
#
#
# @api_view(['GET'])
# @permission_classes([AllowAny])
# def subscription_plans(request):
#     plans = SubscriptionPlan.objects.filter(is_active=True)
#     return Response(SubscriptionPlanSerializer(plans, many=True).data)
#
#
# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def create_checkout_session(request):
#     plan_id = request.data.get('plan_id')
#     if not plan_id:
#         return Response({'error': 'plan_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
#
#     try:
#         plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
#     except SubscriptionPlan.DoesNotExist:
#         return Response({'error': 'Plan not found.'}, status=status.HTTP_404_NOT_FOUND)
#
#     if not plan.stripe_price_id:
#         return Response({'error': 'Plan not configured in Stripe yet.'}, status=status.HTTP_400_BAD_REQUEST)
#
#     success_url = request.data.get(
#         'success_url',
#         settings.FRONTEND_URL + '/payment/success?session_id={CHECKOUT_SESSION_ID}'
#     )
#     cancel_url = request.data.get('cancel_url', settings.FRONTEND_URL + '/payment/cancel')
#
#     try:
#         session = stripe.checkout.Session.create(
#             payment_method_types=['card'],
#             line_items=[{'price': plan.stripe_price_id, 'quantity': 1}],
#             mode='payment',
#             success_url=success_url,
#             cancel_url=cancel_url,
#             customer_email=request.user.email,
#             metadata={
#                 'user_id': str(request.user.id),
#                 'plan_id': str(plan.id),
#             },
#         )
#     except stripe.StripeError as e:
#         return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
#
#     return Response({'checkout_url': session.url, 'session_id': session.id})
#
#
# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def subscription_status(request):
#     try:
#         sub = UserSubscription.objects.get(user=request.user)
#         if sub.end_date <= timezone.now() and sub.status == 'active':
#             sub.status = 'expired'
#             sub.save()
#         return Response(UserSubscriptionSerializer(sub).data)
#     except UserSubscription.DoesNotExist:
#         return Response({
#             'is_active': False,
#             'plan': None,
#             'status': 'none',
#             'end_date': None,
#             'days_remaining': 0,
#         })
#
#
# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def verify_payment(request):
#     """Frontend calls this after Stripe redirect to confirm the payment went through."""
#     session_id = request.query_params.get('session_id')
#     if not session_id:
#         return Response({'error': 'session_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
#
#     try:
#         session = stripe.checkout.Session.retrieve(session_id)
#     except stripe.StripeError as e:
#         return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
#
#     if session.payment_status == 'paid':
#         if not UserSubscription.objects.filter(
#             user=request.user, stripe_session_id=session_id
#         ).exists():
#             _activate_subscription(session)
#         return Response({'success': True, 'message': 'Subscription activated.'})
#
#     return Response({'success': False, 'message': 'Payment not completed.'})
#
#
# @csrf_exempt
# @api_view(['POST'])
# @permission_classes([AllowAny])
# def stripe_webhook(request):
#     payload = request.body
#     sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
#
#     if not settings.STRIPE_WEBHOOK_SECRET:
#         return Response({'error': 'Webhook secret not configured.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#
#     try:
#         event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
#     except (ValueError, stripe.error.SignatureVerificationError):
#         return Response({'error': 'Invalid signature.'}, status=status.HTTP_400_BAD_REQUEST)
#
#     if event['type'] == 'checkout.session.completed':
#         _activate_subscription(event['data']['object'])
#
#     return Response({'status': 'ok'})
#
#
# def _activate_subscription(session):
#     from django.contrib.auth import get_user_model
#     User = get_user_model()
#
#     try:
#         user_id = session.metadata['user_id']
#         plan_id = session.metadata['plan_id']
#     except (KeyError, AttributeError, TypeError):
#         return
#
#     try:
#         user = User.objects.get(id=user_id)
#         plan = SubscriptionPlan.objects.get(id=plan_id)
#     except (User.DoesNotExist, SubscriptionPlan.DoesNotExist):
#         return
#
#     now = timezone.now()
#     UserSubscription.objects.update_or_create(
#         user=user,
#         defaults={
#             'plan': plan,
#             'stripe_customer_id': session.customer or '',
#             'stripe_session_id': session.id or '',
#             'status': 'active',
#             'start_date': now,
#             'end_date': now + timedelta(days=plan.duration_days),
#         },
#     )


# --- Lemon Squeezy ---
import requests
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from datetime import timedelta

from . import lemonsqueezy
from .models import SubscriptionPlan, UserSubscription
from .serializers import SubscriptionPlanSerializer, UserSubscriptionSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def subscription_plans(request):
    plans = SubscriptionPlan.objects.filter(is_active=True)
    return Response(SubscriptionPlanSerializer(plans, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_checkout_session(request):
    plan_id = request.data.get('plan_id')
    if not plan_id:
        return Response({'error': 'plan_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
    except SubscriptionPlan.DoesNotExist:
        return Response({'error': 'Plan not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not plan.ls_variant_id:
        return Response({'error': 'Plan not configured in Lemon Squeezy yet.'}, status=status.HTTP_400_BAD_REQUEST)

    success_url = request.data.get('success_url', settings.FRONTEND_URL + '/payment/success')

    try:
        checkout = lemonsqueezy.create_checkout(plan, request.user, success_url)
    except requests.RequestException as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    checkout_url = checkout['data']['attributes']['url']
    checkout_id = checkout['data']['id']
    return Response({'checkout_url': checkout_url, 'checkout_id': checkout_id})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subscription_status(request):
    try:
        sub = UserSubscription.objects.get(user=request.user)
        if sub.end_date <= timezone.now() and sub.status == 'active':
            sub.status = 'expired'
            sub.save()
        return Response(UserSubscriptionSerializer(sub).data)
    except UserSubscription.DoesNotExist:
        return Response({
            'is_active': False,
            'plan': None,
            'status': 'none',
            'end_date': None,
            'days_remaining': 0,
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    """Frontend calls this after the Lemon Squeezy redirect to confirm the order went through."""
    order_id = request.query_params.get('order_id')
    if not order_id:
        return Response({'error': 'order_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        order = lemonsqueezy.get_order(order_id)
    except requests.RequestException as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    attributes = order['data']['attributes']
    if attributes.get('status') == 'paid':
        if not UserSubscription.objects.filter(user=request.user, ls_order_id=order_id).exists():
            _activate_subscription(order['data'])
        return Response({'success': True, 'message': 'Subscription activated.'})

    return Response({'success': False, 'message': 'Payment not completed.'})


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def lemonsqueezy_webhook(request):
    signature = request.META.get('HTTP_X_SIGNATURE', '')

    if not settings.LEMONSQUEEZY_WEBHOOK_SECRET:
        return Response({'error': 'Webhook secret not configured.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if not lemonsqueezy.verify_webhook_signature(request.body, signature):
        return Response({'error': 'Invalid signature.'}, status=status.HTTP_400_BAD_REQUEST)

    event = request.data
    event_name = request.META.get('HTTP_X_EVENT_NAME', '')

    if event_name == 'order_created' and event.get('data', {}).get('attributes', {}).get('status') == 'paid':
        _activate_subscription(event['data'])

    return Response({'status': 'ok'})


def _activate_subscription(order_data):
    from django.contrib.auth import get_user_model
    User = get_user_model()

    custom_data = order_data.get('attributes', {}).get('first_order_item', {})
    meta_custom = order_data.get('meta', {}).get('custom_data', {}) if 'meta' in order_data else {}

    try:
        user_id = meta_custom.get('user_id') or custom_data.get('user_id')
        plan_id = meta_custom.get('plan_id') or custom_data.get('plan_id')
    except AttributeError:
        return

    if not user_id or not plan_id:
        return

    try:
        user = User.objects.get(id=user_id)
        plan = SubscriptionPlan.objects.get(id=plan_id)
    except (User.DoesNotExist, SubscriptionPlan.DoesNotExist):
        return

    attributes = order_data.get('attributes', {})
    now = timezone.now()
    UserSubscription.objects.update_or_create(
        user=user,
        defaults={
            'plan': plan,
            'ls_customer_id': str(attributes.get('customer_id', '') or ''),
            'ls_order_id': str(order_data.get('id', '') or ''),
            'status': 'active',
            'start_date': now,
            'end_date': now + timedelta(days=plan.duration_days),
        },
    )
