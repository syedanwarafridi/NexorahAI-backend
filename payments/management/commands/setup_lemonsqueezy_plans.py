"""
Creates a Lemon Squeezy product + variant and saves them to the database.

Requires LEMONSQUEEZY_API_KEY and LEMONSQUEEZY_STORE_ID to be set in .env.

Usage:
    python manage.py setup_lemonsqueezy_plans
    python manage.py setup_lemonsqueezy_plans --price-quarterly 69
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from payments import lemonsqueezy
from payments.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Create a Lemon Squeezy product and variant for the 3-month plan, then save to the database.'

    def add_arguments(self, parser):
        parser.add_argument('--price-quarterly', type=float, default=69.00, help='3-month plan price in USD')

    def handle(self, *args, **options):
        if not settings.LEMONSQUEEZY_API_KEY or not settings.LEMONSQUEEZY_STORE_ID:
            raise CommandError('LEMONSQUEEZY_API_KEY and LEMONSQUEEZY_STORE_ID must be set in .env first.')

        price_usd = options['price_quarterly']
        description = 'Full access to all CPHQ course content, quizzes, mock exams, and AI tutor for 3 months.'

        product, variant = lemonsqueezy.create_product_and_variant(
            name='Nexorah AI — 3 Month Plan',
            description=description,
            price_usd=price_usd,
        )
        self.stdout.write(f'Created Lemon Squeezy product: {product["id"]}')
        self.stdout.write(f'Created Lemon Squeezy variant: {variant["id"]} (${price_usd})')

        plan, created = SubscriptionPlan.objects.update_or_create(
            duration='quarterly',
            defaults={
                'name': '3 Month Plan',
                'price': price_usd,
                'description': description,
                'ls_product_id': product['id'],
                'ls_variant_id': variant['id'],
                'is_active': True,
            },
        )
        action = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(
            f'{action} plan in DB: {plan.name} — ${plan.price} — Variant ID: {plan.ls_variant_id}'
        ))
        self.stdout.write(self.style.SUCCESS('\nDone! 3-month plan is ready.'))
