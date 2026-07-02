from django.db.models import Avg
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from core.models import OrderItem, Review


@receiver([post_save, post_delete], sender=OrderItem)
def update_order_total(sender, instance, **kwargs):
    """Recalculate order totals whenever order items change."""
    instance.order.recalculate_total()


@receiver([post_save, post_delete], sender=Review)
def update_restaurant_rating(sender, instance, **kwargs):
    """Recalculate a restaurant's average rating whenever a review changes."""
    restaurant = instance.restaurant
    avg = restaurant.reviews.aggregate(avg=Avg("rating"))["avg"] or 0
    restaurant.average_rating = round(avg, 2)
    restaurant.save(update_fields=["average_rating"])
