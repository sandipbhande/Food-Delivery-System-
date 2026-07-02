import uuid

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base with created/updated timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserRole(models.TextChoices):
    CUSTOMER = "customer", "Customer"
    RESTAURANT_OWNER = "restaurant_owner", "Restaurant Owner"
    DELIVERY_AGENT = "delivery_agent", "Delivery Agent"


class Profile(TimeStampedModel):
    """Extra info attached to Django's built-in User model."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.CUSTOMER)
    phone_number = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class Address(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=50, default="Home")  # Home, Work, etc.
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.label} - {self.street}, {self.city}"


class Restaurant(TimeStampedModel):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="restaurants")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    cuisine_type = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    logo = models.ImageField(upload_to="restaurant_logos/", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class MenuCategory(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=100)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "Menu categories"
        ordering = ["display_order", "name"]
        unique_together = ("restaurant", "name")

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"


class MenuItem(TimeStampedModel):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="menu_items")
    category = models.ForeignKey(MenuCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="items")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    image = models.ImageField(upload_to="menu_items/", null=True, blank=True)
    is_vegetarian = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} - {self.restaurant.name}"


class OrderStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    PREPARING = "preparing", "Preparing"
    OUT_FOR_DELIVERY = "out_for_delivery", "Out for Delivery"
    DELIVERED = "delivered", "Delivered"
    CANCELLED = "cancelled", "Cancelled"


class PaymentMethod(models.TextChoices):
    CASH_ON_DELIVERY = "cod", "Cash on Delivery"
    CARD = "card", "Card"
    UPI = "upi", "UPI"
    WALLET = "wallet", "Wallet"


class Order(TimeStampedModel):
    order_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="orders")
    delivery_address = models.ForeignKey(Address, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.CASH_ON_DELIVERY)
    is_paid = models.BooleanField(default=False)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    special_instructions = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.order_id} - {self.customer.username}"

    def recalculate_total(self, save=True):
        subtotal = sum(item.subtotal for item in self.items.all())
        self.subtotal = subtotal
        self.total_amount = subtotal + self.delivery_fee
        if save:
            self.save(update_fields=["subtotal", "total_amount"])


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=8, decimal_places=2)  # price snapshot at order time

    @property
    def subtotal(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.menu_item.name}"


class DeliveryAgent(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="delivery_agent")
    vehicle_number = models.CharField(max_length=20, blank=True)
    is_available = models.BooleanField(default=True)
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return f"Agent: {self.user.username}"


class Delivery(TimeStampedModel):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="delivery")
    agent = models.ForeignKey(DeliveryAgent, on_delete=models.SET_NULL, null=True, blank=True, related_name="deliveries")
    assigned_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Delivery for Order #{self.order.order_id}"


class Review(TimeStampedModel):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="review")
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="reviews")
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)

    def __str__(self):
        return f"{self.rating}★ - {self.restaurant.name}"
