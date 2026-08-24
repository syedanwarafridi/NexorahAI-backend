from django.db import models
from django.conf import settings
from django.utils import timezone


class SubscriptionPlan(models.Model):
    DURATION_CHOICES = [('quarterly', '3 Months')]

    name = models.CharField(max_length=100)
    duration = models.CharField(max_length=20, choices=DURATION_CHOICES)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    # --- Stripe (replaced by Lemon Squeezy) ---
    # stripe_price_id = models.CharField(max_length=100, blank=True)
    # stripe_product_id = models.CharField(max_length=100, blank=True)
    # --- Lemon Squeezy ---
    ls_variant_id = models.CharField(max_length=100, blank=True)
    ls_product_id = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['price']

    def __str__(self):
        return f"{self.name} — ${self.price}"

    @property
    def duration_days(self):
        return 30 if self.duration == 'monthly' else 90


class UserSubscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscription'
    )
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    # --- Stripe (replaced by Lemon Squeezy) ---
    # stripe_customer_id = models.CharField(max_length=100, blank=True)
    # stripe_session_id = models.CharField(max_length=100, blank=True)
    # --- Lemon Squeezy ---
    ls_customer_id = models.CharField(max_length=100, blank=True)
    ls_order_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} — {self.plan.name if self.plan else 'No Plan'} — {self.status}"

    @property
    def is_active(self):
        return self.status == 'active' and self.end_date > timezone.now()

    @property
    def days_remaining(self):
        if not self.is_active:
            return 0
        return max((self.end_date - timezone.now()).days, 0)
