"""
Lemon Squeezy API client helpers.

Docs: https://docs.lemonsqueezy.com/api
Auth: Bearer token (API key) on every request.
Checkouts: https://docs.lemonsqueezy.com/api/checkouts
Webhooks: https://docs.lemonsqueezy.com/help/webhooks
"""
import hashlib
import hmac

import requests
from django.conf import settings

API_BASE_URL = 'https://api.lemonsqueezy.com/v1'


def _headers():
    return {
        'Accept': 'application/vnd.api+json',
        'Content-Type': 'application/vnd.api+json',
        'Authorization': f'Bearer {settings.LEMONSQUEEZY_API_KEY}',
    }


def create_checkout(plan, user, success_url):
    """Create a Lemon Squeezy checkout for a one-time purchase of `plan`."""
    payload = {
        'data': {
            'type': 'checkouts',
            'attributes': {
                'checkout_data': {
                    'email': user.email,
                    'custom': {
                        'user_id': str(user.id),
                        'plan_id': str(plan.id),
                    },
                },
                'product_options': {
                    'redirect_url': success_url,
                },
            },
            'relationships': {
                'store': {
                    'data': {'type': 'stores', 'id': str(settings.LEMONSQUEEZY_STORE_ID)},
                },
                'variant': {
                    'data': {'type': 'variants', 'id': str(plan.ls_variant_id)},
                },
            },
        },
    }
    response = requests.post(f'{API_BASE_URL}/checkouts', json=payload, headers=_headers())
    response.raise_for_status()
    return response.json()


def get_order(order_id):
    response = requests.get(f'{API_BASE_URL}/orders/{order_id}', headers=_headers())
    response.raise_for_status()
    return response.json()


def create_product_and_variant(name, description, price_usd):
    """Bootstrap a product + variant in Lemon Squeezy for a subscription plan."""
    product_payload = {
        'data': {
            'type': 'products',
            'attributes': {'name': name, 'description': description},
            'relationships': {
                'store': {'data': {'type': 'stores', 'id': str(settings.LEMONSQUEEZY_STORE_ID)}},
            },
        },
    }
    product_resp = requests.post(f'{API_BASE_URL}/products', json=product_payload, headers=_headers())
    product_resp.raise_for_status()
    product = product_resp.json()['data']

    variant_payload = {
        'data': {
            'type': 'variants',
            'attributes': {
                'name': name,
                'price': int(price_usd * 100),
                'is_subscription': False,
            },
            'relationships': {
                'product': {'data': {'type': 'products', 'id': product['id']}},
            },
        },
    }
    variant_resp = requests.post(f'{API_BASE_URL}/variants', json=variant_payload, headers=_headers())
    variant_resp.raise_for_status()
    variant = variant_resp.json()['data']

    return product, variant


def verify_webhook_signature(payload_body, signature_header):
    if not settings.LEMONSQUEEZY_WEBHOOK_SECRET or not signature_header:
        return False
    digest = hmac.new(
        settings.LEMONSQUEEZY_WEBHOOK_SECRET.encode('utf-8'),
        payload_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(digest, signature_header)
