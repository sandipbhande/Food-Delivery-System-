from django.contrib import admin

from core.models import (
    Address, Delivery, DeliveryAgent, MenuCategory, MenuItem,
    Order, OrderItem, Profile, Restaurant, Review,
)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["price"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["order_id", "customer", "restaurant", "status", "total_amount", "created_at"]
    list_filter = ["status", "payment_method", "is_paid"]
    inlines = [OrderItemInline]
    readonly_fields = ["subtotal", "total_amount"]


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 0


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "city", "cuisine_type", "average_rating", "is_active"]
    list_filter = ["city", "cuisine_type", "is_active"]
    search_fields = ["name", "city"]
    inlines = [MenuItemInline]


admin.site.register(Profile)
admin.site.register(Address)
admin.site.register(MenuCategory)
admin.site.register(MenuItem)
admin.site.register(DeliveryAgent)
admin.site.register(Delivery)
admin.site.register(Review)
