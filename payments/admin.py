from django.contrib import admin
from .models import SubscriptionPlan, UserSubscription


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    # list_display = ('name', 'duration', 'price', 'stripe_price_id', 'is_active')  # Stripe (replaced by Lemon Squeezy)
    list_display = ('name', 'duration', 'price', 'ls_variant_id', 'is_active')
    list_editable = ('is_active',)


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'is_active', 'start_date', 'end_date', 'days_remaining')
    list_filter = ('status', 'plan')
    search_fields = ('user__email',)
    # readonly_fields = ('created_at', 'updated_at', 'stripe_customer_id', 'stripe_session_id')  # Stripe (replaced by Lemon Squeezy)
    readonly_fields = ('created_at', 'updated_at', 'ls_customer_id', 'ls_order_id')
