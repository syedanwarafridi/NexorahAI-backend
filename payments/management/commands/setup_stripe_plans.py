# --- Stripe (replaced by Lemon Squeezy — see setup_lemonsqueezy_plans.py) ---
#
# """
# Creates Stripe products + prices and saves them to the database.
#
# Usage:
#     python manage.py setup_stripe_plans
#     python manage.py setup_stripe_plans --price-quarterly 69
# """
# import stripe
# from django.conf import settings
# from django.core.management.base import BaseCommand
# from payments.models import SubscriptionPlan
#
#
# class Command(BaseCommand):
#     help = 'Create Stripe product and price for the 3-month plan, then save to the database.'
#
#     def add_arguments(self, parser):
#         parser.add_argument('--price-quarterly', type=float, default=69.00, help='3-month plan price in USD')
#
#     def handle(self, *args, **options):
#         stripe.api_key = settings.STRIPE_SECRET_KEY
#
#         # Deactivate any existing monthly plan
#         deactivated = SubscriptionPlan.objects.filter(duration='monthly').update(is_active=False)
#         if deactivated:
#             self.stdout.write(self.style.WARNING(f'Deactivated {deactivated} monthly plan(s).'))
#
#         price_usd = options['price_quarterly']
#         price_cents = int(price_usd * 100)
#         description = 'Full access to all CPHQ course content, quizzes, mock exams, and AI tutor for 3 months.'
#
#         product = stripe.Product.create(
#             name='Nexorah AI — 3 Month Plan',
#             description=description,
#         )
#         self.stdout.write(f'Created Stripe product: {product.id}')
#
#         price = stripe.Price.create(
#             product=product.id,
#             unit_amount=price_cents,
#             currency='usd',
#         )
#         self.stdout.write(f'Created Stripe price: {price.id} (${price_usd})')
#
#         plan, created = SubscriptionPlan.objects.update_or_create(
#             duration='quarterly',
#             defaults={
#                 'name': '3 Month Plan',
#                 'price': price_usd,
#                 'description': description,
#                 'stripe_product_id': product.id,
#                 'stripe_price_id': price.id,
#                 'is_active': True,
#             },
#         )
#         action = 'Created' if created else 'Updated'
#         self.stdout.write(self.style.SUCCESS(
#             f'{action} plan in DB: {plan.name} — ${plan.price} — Price ID: {plan.stripe_price_id}'
#         ))
#         self.stdout.write(self.style.SUCCESS('\nDone! 3-month plan is ready.'))
